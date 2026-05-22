"""Authentication views: login, logout, token refresh, Google OAuth, password management."""

import json
import logging
import sys
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError

from core.models import AuditAction, AuditOutcome
from core.throttles import AnonAuthThrottle, AnonBurstThrottle

logger = logging.getLogger(__name__)
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
AUTH_COOKIE_SAMESITE: Literal["Lax"] = "Lax"


def _v():
    """Return the accounts.views package module for mock-patchable lookups."""
    return sys.modules["accounts.views"]


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT == "production"


def _cookie_path() -> str:
    """Scope auth cookies to the active profile path to avoid cross-profile collisions."""
    return getattr(settings, "FORCE_SCRIPT_NAME", "") or "/"


def _set_auth_cookies(
    response: Response, *, access_token: str | None = None, refresh_token: str | None = None
) -> Response:
    """Attach HttpOnly auth cookies to a response."""
    if access_token is not None:
        access_lifetime = cast("Any", settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"])
        access_max_age = int(access_lifetime.total_seconds())
        response.set_cookie(
            ACCESS_COOKIE_NAME,
            access_token,
            max_age=access_max_age,
            httponly=True,
            secure=_cookie_secure(),
            samesite=AUTH_COOKIE_SAMESITE,
            path=_cookie_path(),
        )
    if refresh_token is not None:
        refresh_lifetime = cast("Any", settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
        refresh_max_age = int(refresh_lifetime.total_seconds())
        response.set_cookie(
            REFRESH_COOKIE_NAME,
            refresh_token,
            max_age=refresh_max_age,
            httponly=True,
            secure=_cookie_secure(),
            samesite=AUTH_COOKIE_SAMESITE,
            path=_cookie_path(),
        )
    return response


def _clear_auth_cookies(response: Response) -> Response:
    """Expire auth cookies from the client."""
    cookie_path = _cookie_path()
    response.delete_cookie(ACCESS_COOKIE_NAME, path=cookie_path, samesite=AUTH_COOKIE_SAMESITE)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=cookie_path, samesite=AUTH_COOKIE_SAMESITE)
    return response


def _extract_refresh_token(request) -> str | None:
    """Read refresh token from request body first, then cookie fallback."""
    body_token = request.data.get("refreshToken") if isinstance(request.data, dict) else None
    if isinstance(body_token, str) and body_token.strip():
        return body_token
    cookie_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
    return cookie_token if cookie_token else None


def _identifier_throttle_response(scope: str, identifier: str) -> Response:
    """Return standardized 429 response for identifier-based lockouts."""
    retry_after = max(1, _v().identifier_throttle_retry_after(scope, identifier))
    return Response(
        {"detail": "Too many failed attempts. Please try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )


def _google_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch Google user profile information using an OAuth access token."""
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        return cast("dict[str, Any]", json.loads(response.read().decode("utf-8")))


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Authenticate a user with role-constrained identifier + password."""
    v = _v()
    serializer = v.LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["identifier"]
    password = serializer.validated_data["password"]
    if not v.check_identifier_throttle("login", identifier):
        return _identifier_throttle_response("login", identifier)

    existing_user = v.find_user_by_identifier(identifier)
    if not existing_user:
        v.register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if not v.identifier_allowed_for_user(identifier, existing_user):
        v.register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )

    user = v.authenticate_user(identifier, password)
    if not user:
        v.register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )
    if user.is_staff:
        return Response(
            {"detail": "Admin accounts must use Django admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    v.clear_identifier_failures("login", identifier)
    refresh = v.RefreshToken.for_user(user)
    body = v.build_user_response(user)
    response = Response(body, status=status.HTTP_200_OK)
    return _set_auth_cookies(
        response,
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonBurstThrottle])
def demo_login(request):
    """Log in as a pre-seeded demo user for the requested role (STUDENT, TEACHER, RESEARCHER)."""
    v = _v()
    role = request.data.get("role", "").upper() if isinstance(request.data, dict) else ""
    if role not in ("STUDENT", "TEACHER", "RESEARCHER"):
        return Response(
            {"detail": "Invalid role. Must be STUDENT, TEACHER, or RESEARCHER."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = (
        v.User.objects.filter(
            is_active=True,
            is_staff=False,
            roles__role=role,
        )
        .order_by("id")
        .first()
    )
    if user is None:
        return Response(
            {"detail": "Demo accounts are not configured on this server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    refresh = v.RefreshToken.for_user(user)
    body = v.build_user_response(user)
    response = Response(body, status=status.HTTP_200_OK)
    return _set_auth_cookies(
        response,
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_profile(request):
    """Return authenticated user profile for frontend role gating."""
    return Response(
        {
            "id": str(request.user.id),
            "name": request.user.name,
            "username": request.user.username,
            "email": request.user.email,
            "role": _v().primary_role(request.user),
            "isStaff": bool(request.user.is_staff),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def refresh(request):
    """Exchange a refresh token for a new access token."""
    v = _v()
    refresh_token = _extract_refresh_token(request)
    if not refresh_token:
        serializer = v.RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refreshToken"]
    try:
        token = v.RefreshToken(cast("Any", refresh_token))
    except TokenError:
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
    response = Response({"message": "Session refreshed."}, status=status.HTTP_200_OK)
    return _set_auth_cookies(response, access_token=str(token.access_token))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """End the current session and clear auth cookies (idempotent)."""
    v = _v()
    refresh_token = _extract_refresh_token(request)
    if not refresh_token:
        serializer = v.RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refreshToken"]

    if not v.blacklist_refresh_token(refresh_token):
        response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
        return _clear_auth_cookies(response)
    response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
    return _clear_auth_cookies(response)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change password for the authenticated user and revoke all sessions."""
    v = _v()
    serializer = v.PasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    if payload["newPassword"] != payload["confirmPassword"]:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.check_password(payload["currentPassword"]):
        return Response(
            {"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST
        )

    errors = v.password_strength_errors(payload["newPassword"])
    if errors:
        return Response({"detail": errors[0]}, status=status.HTTP_400_BAD_REQUEST)
    if request.user.check_password(payload["newPassword"]):
        return Response(
            {"detail": "New password must be different from current password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    request.user.set_password(payload["newPassword"])
    request.user.save(update_fields=["password"])
    invalidated = v.invalidate_user_sessions(request.user)

    return Response(
        {"message": "Password changed successfully.", "sessionsInvalidated": invalidated},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def login_with_google(request):
    """Authenticate a user via Google OAuth and establish auth cookies."""
    v = _v()
    serializer = v.GoogleOAuthLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    access_token = serializer.validated_data["accessToken"]
    try:
        userinfo = v._google_userinfo(access_token)
    except (URLError, HTTPError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Google userinfo request failed: %s", exc)
        return Response(
            {"detail": "Access token verification failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except Exception:
        logger.exception("Unexpected error fetching Google userinfo")
        return v.server_error_response()

    subject = userinfo.get("sub")
    email = userinfo.get("email")
    if not subject or not email:
        return Response(
            {"detail": "Access token verification failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    oauth_identifier = f"oauth:{v.normalize_username_identifier(str(email))}"
    if not v.check_identifier_throttle("oauth-login", oauth_identifier):
        return _identifier_throttle_response("oauth-login", oauth_identifier)

    account = v.OAuthAccount.objects.filter(provider=v.OAuthProvider.GOOGLE, subject=subject).first()
    if account:
        if v.primary_role(account.user) == v.Role.STUDENT:
            v.register_identifier_failure("oauth-login", oauth_identifier)
            return Response(
                {"detail": "Google OAuth is not supported for student accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if account.user.is_staff:
            return Response(
                {"detail": "Admin accounts must use Django admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        account.email = email
        account.last_login_at = v.timezone.now()
        account.save(update_fields=["email", "last_login_at"])
        user = account.user
    else:
        found_user = v.User.objects.filter(email__iexact=email).first()
        if not found_user:
            found_user = v.User.objects.filter(username__iexact=email).first()
        if not found_user:
            v.register_identifier_failure("oauth-login", oauth_identifier)
            return Response(
                {"detail": "Invalid identifier or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if v.primary_role(found_user) == v.Role.STUDENT:
            v.register_identifier_failure("oauth-login", oauth_identifier)
            return Response(
                {"detail": "Google OAuth is not supported for student accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if found_user.is_staff:
            return Response(
                {"detail": "Admin accounts must use Django admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not found_user.email:
            found_user.email = email
            found_user.save(update_fields=["email"])
        v.link_or_create_oauth_account(found_user, subject, email)
        user = found_user

    v.clear_identifier_failures("oauth-login", oauth_identifier)
    refresh = v.RefreshToken.for_user(user)
    body = v.build_user_response(user)
    response = Response(body, status=status.HTTP_200_OK)
    return _set_auth_cookies(
        response,
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
    )


@api_view(["POST"])
@permission_classes([_v().IsTeacherOrAbove])
def issue_password_reset_code_view(request):
    """Issue a one-time reset code for a selected target user."""
    v = _v()
    serializer = v.PasswordResetCodeIssueSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target_user_id = serializer.validated_data["targetUserId"]
    target_user = v.User.objects.filter(id=target_user_id).first()
    ip = v.get_client_ip(request)

    audit_id = v.log_audit(
        actor=request.user,
        action=AuditAction.PASSWORD_RESET,
        target_user=target_user,
        old_value={"password": "changed"},
        new_value={"password": "changed"},
        ip_address=ip,
    )

    try:
        reset_request, reset_code = v.issue_password_reset_code(
            issuer=request.user,
            target_user_id=target_user_id,
        )
    except ValueError as exc:
        v.complete_audit(audit_id, AuditOutcome.FAILURE)
        detail = str(exc)
        status_code: int = status.HTTP_404_NOT_FOUND
        if "not found" not in detail.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        return Response({"detail": detail}, status=status_code)
    except PermissionError as exc:
        v.complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    v.complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(
        {
            "requestId": reset_request.id,
            "targetUserId": target_user_id,
            "targetRole": reset_request.requested_role,
            "resetCode": reset_code,
            "expiresAt": reset_request.expires_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonBurstThrottle])
def verify_reset_code(request):
    """Verify a reset code before allowing password update."""
    v = _v()
    serializer = v.PasswordResetCodeVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["identifier"]
    reset_code = serializer.validated_data["resetCode"]
    code = v.verify_password_reset_code(identifier, reset_code)
    if not code:
        return Response(
            {"valid": False, "detail": "Invalid or expired reset code."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "valid": True,
            "requestId": code.request_id,
            "expiresAt": code.expires_at.isoformat(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonBurstThrottle])
def complete_reset_code(request):
    """Complete a password reset using a valid code."""
    v = _v()
    serializer = v.PasswordResetCodeCompleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    if payload["newPassword"] != payload["confirmPassword"]:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        v.complete_password_reset(
            identifier=payload["identifier"],
            reset_code=payload["resetCode"],
            new_password=payload["newPassword"],
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
