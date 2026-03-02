"""
Authentication and user management API endpoints.

This module provides REST API views for:
- User registration and login (username/password and Google OAuth)
- User CRUD operations (create, read, update, delete)
- Password management (set initial password, reset password)
- Bulk user creation for administrators

All endpoints return JSON responses. Authentication uses JWT via SimpleJWT
with HttpOnly cookie transport. Role-based access control is enforced via
permission classes.

Endpoints:
    POST /api/v1/auth/sessions          - Username/password authentication
    POST /api/v1/auth/sessions/oauth    - Google OAuth authentication
    POST /api/v1/auth/token-exchanges   - Refresh access token
    POST /api/v1/auth/session-revocations - Logout (refresh token blacklist)
    PATCH /api/v1/auth/password         - Self-service password change
    POST /api/v1/auth/password-reset-codes - Issuer-driven reset code generation
    POST /api/v1/auth/reset-code-validations - Verify reset code
    POST /api/v1/auth/password-resets   - Complete password reset
    POST /api/v1/registration/accounts  - Unified registration (method: LOCAL|OAUTH)
    POST /api/v1/registration/code-validations - Public invite code validation (FR-02)
    POST /api/v1/enrollments            - Authenticated student course join (FR-02)
    GET/POST /api/v1/codes              - List/create registration codes (FR-02)
    GET/PATCH /api/v1/codes/{id}        - Code detail + lifecycle transitions (FR-02)
    POST /api/v1/users                  - Create user (teacher/admin, sudoed researcher)
    PATCH /api/v1/users/{id}            - Update user (teacher/admin, sudoed researcher)
    DELETE /api/v1/users/{id}           - Delete user (teacher/admin, sudoed researcher)
    GET /api/v1/users/staff             - List staff (researcher/admin)
    GET /api/v1/users/students          - List students (researcher/admin)
    GET /api/v1/sudo-grants             - List sudo grants (own grants for researcher, all for admin)
    POST /api/v1/sudo-grants            - Grant sudo permissions
    DELETE /api/v1/sudo-grants/{id}     - Revoke sudo grant
"""

import json
import logging
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from django.db.models import Exists, OuterRef, Prefetch, Q

from core.errors import error_response
from core.pagination import paginate
from core.permissions import (
    IsResearcherOrAdmin,
    IsTeacherOrAbove,
    primary_role,
)
from core.throttles import AnonAuthThrottle, AnonBurstThrottle

from courses.models import Enrollment, EnrollmentStatus

from .models import (
    OAuthAccount,
    OAuthProvider,
    RegistrationCodeType,
    Role,
    SudoGrant,
    SudoPermission,
)
from .serializers import (
    GoogleOAuthLoginSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetCodeCompleteSerializer,
    PasswordResetCodeIssueSerializer,
    PasswordResetCodeVerifySerializer,
    RefreshTokenSerializer,
    RegistrationCodeCreateSerializer,
    RegistrationCodeUpdateSerializer,
    RegistrationCodeValidateInputSerializer,
    RegistrationOAuthSerializer,
    StudentInviteRegisterSerializer,
    StudentJoinCourseSerializer,
    StudentListSerializer,
    UserInputSerializer,
    UserOutputSerializer,
)
from .services import (
    authenticate_user,
    blacklist_refresh_token,
    build_user_response,
    can_create_user,
    can_delete_user,
    can_edit_user,
    check_identifier_throttle,
    clear_identifier_failures,
    complete_password_reset,
    create_registration_codes,
    create_user_from_payload,
    ensure_profiles_for_role,
    find_user_by_identifier,
    generate_managed_username,
    grant_sudo_to_researcher,
    identifier_allowed_for_user,
    identifier_in_use,
    identifier_throttle_retry_after,
    invalidate_user_sessions,
    issue_password_reset_code,
    link_or_create_oauth_account,
    normalize_username_identifier,
    password_strength_errors,
    redeem_non_student_local_invite,
    redeem_non_student_oauth_invite,
    redeem_student_invite,
    redeem_student_join_course,
    register_identifier_failure,
    registration_code_scope_queryset,
    registration_code_status,
    revoke_sudo_grant,
    set_single_role,
    transition_registration_code_status,
    validate_registration_code,
    verify_password_reset_code,
)

User = get_user_model()
logger = logging.getLogger(__name__)
USERNAME_IMMUTABLE_DETAIL = "username is system-managed and must not be provided"
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
AUTH_COOKIE_SAMESITE: Literal["Lax"] = "Lax"


def _cookie_secure() -> bool:
    return bool(getattr(settings, "ENVIRONMENT", "") == "production")


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
            path="/",
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
            path="/",
        )
    return response


def _clear_auth_cookies(response: Response) -> Response:
    """Expire auth cookies from the client."""
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", samesite=AUTH_COOKIE_SAMESITE)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", samesite=AUTH_COOKIE_SAMESITE)
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
    retry_after = max(1, identifier_throttle_retry_after(scope, identifier))
    return Response(
        {"detail": "Too many failed attempts. Please try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )


def _google_userinfo(access_token: str) -> dict[str, Any]:
    """
    Fetch Google user profile information using an OAuth access token.

    Makes an HTTP request to Google's userinfo endpoint to retrieve the
    authenticated user's profile data including their unique subject ID and email.

    Args:
        access_token: A valid Google OAuth2 access token obtained from the
            frontend after the user completes Google Sign-In.

    Returns:
        Dict containing Google user profile fields:
            - sub: Unique Google user identifier
            - email: User's email address
            - email_verified: Whether email is verified
            - name: User's display name
            - picture: URL to profile picture

    Raises:
        URLError: If the request to Google fails (network error, timeout)
        JSONDecodeError: If the response is not valid JSON
        HTTPError: If Google returns an error (invalid token, expired, etc.)
    """
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        return cast("dict[str, Any]", json.loads(response.read().decode("utf-8")))


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def register_account(request):
    """
    Unified registration endpoint.

    Dispatches to LOCAL or OAUTH registration based on the ``method`` field.

    Request Body:
        { "method": "LOCAL", ...local fields... }
        { "method": "OAUTH", ...oauth fields... }

    Returns:
        400 if method is missing or invalid.
    """
    method = (request.data.get("method") or "").upper()
    payload = {k: v for k, v in request.data.items() if k != "method"}
    if method == "LOCAL":
        return _register_local(request, payload)
    if method == "OAUTH":
        return _register_oauth(request, payload)
    return Response({"detail": "method must be LOCAL or OAUTH"}, status=status.HTTP_400_BAD_REQUEST)


def _register_local(request, payload):
    """Register a new account using a local invite-code flow."""
    serializer = StudentInviteRegisterSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data
    confirm_password = validated.get("confirmPassword")
    if validated["password"] != confirm_password:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    password_errors = password_strength_errors(validated["password"])
    if password_errors:
        return Response(
            {
                "detail": "Password does not meet policy requirements.",
                "errors": password_errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    record = validate_registration_code(validated["code"])
    if not record:
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    if record.code_type == RegistrationCodeType.STUDENT:
        try:
            user, enrollment = redeem_student_invite(validated)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        body = build_user_response(user)
        body["message"] = "User registered"
        body["courseId"] = enrollment.course_id
        body["createdNewUser"] = True
        body["alreadyEnrolled"] = False
        response = Response(body, status=status.HTTP_201_CREATED)
        return _set_auth_cookies(
            response, access_token=str(refresh.access_token), refresh_token=str(refresh)
        )

    try:
        user = redeem_non_student_local_invite(validated)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)
    body = build_user_response(user)
    body["message"] = "User registered"
    body["createdNewUser"] = True
    body["alreadyEnrolled"] = False
    body["courseId"] = None
    response = Response(body, status=status.HTTP_201_CREATED)
    return _set_auth_cookies(
        response, access_token=str(refresh.access_token), refresh_token=str(refresh)
    )


def _register_oauth(request, payload):
    """Register a non-student account with invite code + Google OAuth."""
    serializer = RegistrationOAuthSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data

    try:
        google_user = _google_userinfo(validated["accessToken"])
    except (URLError, HTTPError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Google userinfo request failed: %s", exc)
        return Response(
            {"detail": "Invalid Google access token."}, status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as exc:
        logger.warning("Unexpected error fetching Google userinfo: %s", type(exc).__name__)
        return Response(
            {"detail": "Invalid Google access token."}, status=status.HTTP_401_UNAUTHORIZED
        )

    google_subject = str(google_user.get("sub", "")).strip()
    google_email = str(google_user.get("email", "")).strip()
    if not google_subject or not google_email:
        return Response(
            {"detail": "Google user profile is missing required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = redeem_non_student_oauth_invite(
            code=validated["code"],
            oauth_subject=google_subject,
            oauth_email=google_email,
            first_name=validated.get("firstName"),
            last_name=validated.get("lastName"),
            email_verified=google_user.get("email_verified"),
            picture_url=google_user.get("picture"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    body = build_user_response(user)
    body["message"] = "User registered"
    body["courseId"] = None
    body["createdNewUser"] = True
    body["alreadyEnrolled"] = False
    response = Response(body, status=status.HTTP_201_CREATED)
    return _set_auth_cookies(
        response, access_token=str(refresh.access_token), refresh_token=str(refresh)
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def validate_registration_code_view(request):
    """Validate a registration code and return non-sensitive context."""
    serializer = RegistrationCodeValidateInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code = serializer.validated_data["code"]
    record = validate_registration_code(code)
    if not record:
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    context = {}
    if record.course_id and record.course is not None:
        context["course_name"] = record.course.name
        teacher_profile = getattr(record.course, "teacher_profile", None)
        if teacher_profile and teacher_profile.user_id:
            context["teacher_name"] = teacher_profile.user.name

    return Response(
        {
            "valid": True,
            "code_type": record.code_type,
            "context": context,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_course_with_code(request):
    """Redeem a student invite code for the authenticated student account."""
    if primary_role(request.user) != Role.STUDENT:
        return Response(
            {"detail": "Only student accounts can redeem student codes"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = StudentJoinCourseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        enrollment, already_enrolled = redeem_student_join_course(
            user=request.user,
            code=serializer.validated_data["code"],
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    return Response(
        {
            "message": "Already enrolled" if already_enrolled else "Invite redeemed",
            "username": request.user.username,
            "name": request.user.name,
            "courseId": enrollment.course_id,
            "createdNewUser": False,
            "alreadyEnrolled": already_enrolled,
        },
        status=status.HTTP_201_CREATED,
    )


def _serialize_registration_code(record):
    """Return API payload for registration code list/detail responses."""
    plaintext_code = getattr(record, "plaintext_code", None)
    return {
        "id": record.id,
        "code": plaintext_code,
        "codePrefix": record.code_prefix,
        "codeType": record.code_type,
        "status": registration_code_status(record),
        "maxUses": record.max_uses,
        "timesUsed": record.times_used,
        "usesRemaining": max(record.max_uses - record.times_used, 0),
        "expiresAt": record.expires_at.isoformat(),
        "isActive": record.is_active,
        "courseId": record.course_id,
        "courseName": record.course.name if record.course_id else None,
        "metadata": record.metadata,
        "createdByUserId": record.created_by_id,
        "createdAt": record.created_at.isoformat(),
        "archivedAt": record.archived_at.isoformat() if record.archived_at else None,
    }


def _create_codes(request):
    """Generate registration codes for the next role tier."""
    serializer = RegistrationCodeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        created = create_registration_codes(
            creator=request.user,
            code_type=payload["codeType"],
            count=payload["count"],
            uses_per_code=payload["usesPerCode"],
            expires_at=payload["expiresAt"],
            course_id=payload.get("courseId"),
            metadata=payload.get("metadata"),
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "count": len(created),
            "codes": [_serialize_registration_code(record) for record in created],
        },
        status=status.HTTP_201_CREATED,
    )


def _list_codes(request):
    """List registration codes scoped to the authenticated user's role."""
    include_archived = str(request.query_params.get("includeArchived", "")).lower() in (
        "1",
        "true",
        "yes",
    )
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    code_type_filter = str(request.query_params.get("codeType", "")).strip().upper()

    queryset = registration_code_scope_queryset(request.user)
    if code_type_filter:
        queryset = queryset.filter(code_type=code_type_filter)
    if not include_archived:
        queryset = queryset.filter(archived_at__isnull=True)

    records = list(queryset.order_by("-created_at"))
    if status_filter:
        records = [r for r in records if registration_code_status(r) == status_filter]
    return paginate(records, request, transform_fn=_serialize_registration_code)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def codes_collection(request):
    """List or create registration codes according to request method."""
    if request.method == "GET":
        return _list_codes(request)
    return _create_codes(request)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def code_detail(request, code_id: int):
    """Get or transition a single registration code within role scope."""
    if request.method == "GET":
        record = registration_code_scope_queryset(request.user).filter(id=code_id).first()
        if not record:
            return Response(
                {"detail": "Registration code not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(_serialize_registration_code(record), status=status.HTTP_200_OK)

    serializer = RegistrationCodeUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        updated = transition_registration_code_status(
            actor=request.user,
            registration_code_id=code_id,
            next_status=payload["status"],
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Registration code not found.":
            return Response({"detail": message}, status=status.HTTP_404_NOT_FOUND)
        if message.startswith("Only "):
            return Response({"detail": message}, status=status.HTTP_409_CONFLICT)
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

    return Response(_serialize_registration_code(updated), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Authenticate a user with role-constrained identifier + password."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["identifier"]
    password = serializer.validated_data["password"]
    if not check_identifier_throttle("login", identifier):
        return _identifier_throttle_response("login", identifier)

    existing_user = find_user_by_identifier(identifier)
    if not existing_user:
        register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if not identifier_allowed_for_user(identifier, existing_user):
        register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )

    user = authenticate_user(identifier, password)
    if not user:
        register_identifier_failure("login", identifier)
        return Response(
            {"detail": "Invalid identifier or password."}, status=status.HTTP_401_UNAUTHORIZED
        )
    if user.is_staff:
        return Response(
            {"detail": "Admin accounts must use Django admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    clear_identifier_failures("login", identifier)
    refresh = RefreshToken.for_user(user)
    body = build_user_response(user)
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
            "role": primary_role(request.user),
            "isStaff": bool(request.user.is_staff),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def refresh(request):
    """Exchange a refresh token for a new access token."""
    refresh_token = _extract_refresh_token(request)
    if not refresh_token:
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refreshToken"]
    try:
        token = RefreshToken(cast("Any", refresh_token))
    except TokenError:
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
    response = Response({"message": "Session refreshed."}, status=status.HTTP_200_OK)
    return _set_auth_cookies(response, access_token=str(token.access_token))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """Invalidate a refresh token and end the current session."""
    refresh_token = _extract_refresh_token(request)
    if not refresh_token:
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refreshToken"]

    if not blacklist_refresh_token(refresh_token):
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
    response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
    return _clear_auth_cookies(response)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change password for the authenticated user and revoke all sessions."""
    serializer = PasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    if payload["newPassword"] != payload["confirmPassword"]:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.check_password(payload["currentPassword"]):
        return Response(
            {"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST
        )

    errors = password_strength_errors(payload["newPassword"])
    if errors:
        return Response({"detail": errors[0]}, status=status.HTTP_400_BAD_REQUEST)
    if request.user.check_password(payload["newPassword"]):
        return Response(
            {"detail": "New password must be different from current password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    request.user.set_password(payload["newPassword"])
    request.user.save(update_fields=["password"])
    invalidated = invalidate_user_sessions(request.user)

    return Response(
        {"message": "Password changed successfully.", "sessionsInvalidated": invalidated},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_with_google(request):
    """
    Authenticate a user via Google OAuth and establish auth cookies.

    The frontend completes Google Sign-In and sends the access token here.
    This endpoint verifies the token with Google, then either:
    1. Links to an existing OAuth account and logs in, or
    2. Links to an existing user account by email (first Google login), or
    3. Returns an error if no matching account exists.

    Note: Users must be pre-created in the system before using Google login.
    This endpoint does NOT create new accounts - use register or create_user.

    Request Body:
        {
            "accessToken": "ya29.a0..."  # Google OAuth access token from frontend
        }

    Returns:
        200: {
            "role": "STUDENT|TEACHER|RESEARCHER",
            "id": "123",
            "username": "user123",
            "name": "Display Name",
            "email": "user@example.com"
        }
        (also sets HttpOnly access_token + refresh_token cookies)
        400: "accessToken is required" if missing
        401: "Access token verification failed" if Google rejects token
        401: "Access token verification failed" if Google response is invalid
        401: "Invalid identifier or password" when no eligible account is linked
    """
    serializer = GoogleOAuthLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    access_token = serializer.validated_data["accessToken"]
    try:
        userinfo = _google_userinfo(access_token)
    except (URLError, HTTPError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Google userinfo request failed: %s", exc)
        return Response(
            {"detail": "Access token verification failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except Exception as exc:
        logger.warning("Unexpected error fetching Google userinfo: %s", type(exc).__name__)
        return Response(
            {"detail": "Access token verification failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    subject = userinfo.get("sub")
    email = userinfo.get("email")
    if not subject or not email:
        return Response(
            {"detail": "Access token verification failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    oauth_identifier = f"oauth:{normalize_username_identifier(str(email))}"
    if not check_identifier_throttle("oauth-login", oauth_identifier):
        return _identifier_throttle_response("oauth-login", oauth_identifier)

    account = OAuthAccount.objects.filter(provider=OAuthProvider.GOOGLE, subject=subject).first()
    if account:
        if primary_role(account.user) == Role.STUDENT:
            register_identifier_failure("oauth-login", oauth_identifier)
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
        account.last_login_at = timezone.now()
        account.save(update_fields=["email", "last_login_at"])
        user = account.user
    else:
        found_user = User.objects.filter(email__iexact=email).first()
        if not found_user:
            found_user = User.objects.filter(username__iexact=email).first()
        if not found_user:
            register_identifier_failure("oauth-login", oauth_identifier)
            return Response(
                {"detail": "Invalid identifier or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if primary_role(found_user) == Role.STUDENT:
            register_identifier_failure("oauth-login", oauth_identifier)
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
        link_or_create_oauth_account(found_user, subject, email)
        user = found_user

    clear_identifier_failures("oauth-login", oauth_identifier)
    refresh = RefreshToken.for_user(user)
    body = build_user_response(user)
    response = Response(body, status=status.HTTP_200_OK)
    return _set_auth_cookies(
        response,
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
    )


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def issue_password_reset_code_view(request):
    """Issue a one-time reset code for a selected target user."""
    serializer = PasswordResetCodeIssueSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target_user_id = serializer.validated_data["targetUserId"]

    try:
        reset_request, reset_code = issue_password_reset_code(
            issuer=request.user,
            target_user_id=target_user_id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code: int = status.HTTP_404_NOT_FOUND
        if "not found" not in detail.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        return Response({"detail": detail}, status=status_code)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

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
    serializer = PasswordResetCodeVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["identifier"]
    reset_code = serializer.validated_data["resetCode"]
    code = verify_password_reset_code(identifier, reset_code)
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
    serializer = PasswordResetCodeCompleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    if payload["newPassword"] != payload["confirmPassword"]:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        complete_password_reset(
            identifier=payload["identifier"],
            reset_code=payload["resetCode"],
            new_password=payload["newPassword"],
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def create_user(request):
    """
    Create a new user account with specified role (privileged operation).

    Teachers can create students only. Admins can create users of any role.

    Request Body:
        {
            "name": "User Name",             # Required
            "role": "STUDENT|TEACHER|RESEARCHER", # Optional, defaults to STUDENT
            "password": "optional"           # Optional initial password
            "email": "optional@example.com"  # Required for non-students
        }

    Returns:
        201: Created user object {id, name, username, email, role}
        400: "name is required" if missing
        403: "Forbidden" if requester lacks permission for requested role

    Permission Rules:
        - TEACHER: Can create STUDENT only
        - Researcher with CREATE_TEACHER/CREATE_STUDENT sudo permission
        - Admin (is_staff): Can create RESEARCHER or TEACHER
    """
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if "username" in request.data:
        return Response(
            {"detail": USERNAME_IMMUTABLE_DETAIL},
            status=status.HTTP_400_BAD_REQUEST,
        )
    payload = serializer.validated_data
    if not payload.get("name"):
        return Response({"detail": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
    requested_role = payload.get("role") or Role.STUDENT
    if not can_create_user(request.user, requested_role):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if requested_role != Role.STUDENT and not payload.get("email"):
        return Response(
            {"detail": "email is required for non-student users"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if payload.get("email") and identifier_in_use(payload.get("email")):
        return Response({"detail": "Email already taken"}, status=status.HTTP_409_CONFLICT)
    create_payload = dict(payload)
    create_payload["username"] = generate_managed_username(name=payload["name"])
    try:
        user = create_user_from_payload(
            create_payload,
            role_override=requested_role,
            creator=request.user,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(UserOutputSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def manage_user(request, user_id: int):
    """
    Update or delete an existing user account.

    PATCH: Update user profile, role, or password.
    DELETE: Permanently delete a user account.

    Args:
        user_id: Database ID of the user (path parameter)
    """
    if request.method == "DELETE":
        return _delete_user(request, user_id)
    return _edit_user(request, user_id)


def _edit_user(request, user_id: int):
    """Update an existing user's profile, role, or password."""
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    requested_role = payload.get("role") or primary_role(user)
    if not can_edit_user(request.user, user, requested_role):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    next_email = user.email

    if payload.get("name"):
        user.name = payload["name"]

    if "username" in payload:
        return Response(
            {"detail": "Usernames are system-managed and immutable."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "email" in payload:
        incoming_email = payload.get("email")
        normalized_email = normalize_username_identifier(incoming_email) if incoming_email else None
        if normalized_email and identifier_in_use(normalized_email, exclude_user_id=user_id):
            return Response({"detail": "Email already taken"}, status=status.HTTP_409_CONFLICT)
        next_email = normalized_email
        user.email = normalized_email

    if requested_role != Role.STUDENT and not next_email:
        return Response(
            {"detail": "email is required for non-student users"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if payload.get("password"):
        user.set_password(payload["password"])
    user.save()
    if payload.get("role"):
        set_single_role(user, payload["role"])
        ensure_profiles_for_role(user, payload["role"], creator=request.user)
    user.refresh_from_db()
    return Response(UserOutputSerializer(user).data, status=status.HTTP_200_OK)


def _delete_user(request, user_id: int):
    """Permanently delete a user account by ID."""
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    if not can_delete_user(request.user, user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsResearcherOrAdmin])
def list_staff(request):
    """
    List staff directory users (researchers and teachers).

    Used by researcher/admin dashboard views to display non-admin staff
    accounts for management workflows.

    Returns:
        200: [
            {
                "id": 123,
                "name": "Teacher Name",
                "username": "teacher@example.com",
                "role": "TEACHER"
            },
            ...
        ]
    """
    users = (
        User.objects.filter(roles__role__in=[Role.TEACHER, Role.RESEARCHER])
        .prefetch_related("roles")
        .distinct()
        .order_by("id")
    )
    return paginate(users, request, transform_fn=lambda u: UserOutputSerializer(u).data)


@api_view(["GET"])
@permission_classes([IsResearcherOrAdmin])
def list_students(request):
    """
    List student users with their active course enrollments.

    Supports search filtering via ``q`` (name/username icontains) and
    course filtering via ``courseId`` (numeric course ID).

    Returns:
        200: Paginated list of students with active enrollments.
        400: If courseId is present but non-numeric.
    """
    # Validate courseId early — must be a positive integer if provided
    course_id_param = request.query_params.get("courseId")
    if course_id_param is not None:
        try:
            course_id = int(course_id_param)
            if course_id < 1:
                raise ValueError
        except (ValueError, TypeError):
            return error_response("courseId must be a positive integer", status_code=400)
    else:
        course_id = None

    # Active enrollments subquery — only include students who have at least one
    active_enrollment_exists = Enrollment.objects.filter(
        student_profile__user=OuterRef("pk"),
        status=EnrollmentStatus.ACTIVE,
    )

    # Base queryset: STUDENT-role users with at least one ACTIVE enrollment
    users = (
        User.objects.filter(roles__role=Role.STUDENT)
        .filter(Exists(active_enrollment_exists))
        .prefetch_related(
            Prefetch(
                "student_profile__enrollments",
                queryset=Enrollment.objects.filter(
                    status=EnrollmentStatus.ACTIVE,
                ).select_related("course"),
                to_attr="active_enrollments",
            ),
        )
        .distinct()
        .order_by("id")
    )

    # Search filter: name or username icontains
    search = request.query_params.get("q", "").strip()
    if search:
        users = users.filter(Q(name__icontains=search) | Q(username__icontains=search))

    # Course filter
    if course_id is not None:
        users = users.filter(
            student_profile__enrollments__course_id=course_id,
            student_profile__enrollments__status=EnrollmentStatus.ACTIVE,
        )

    def transform(user):
        enrollments = getattr(user.student_profile, "active_enrollments", [])
        return StudentListSerializer(
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "courses": [
                    {"id": e.course.id, "name": e.course.name} for e in enrollments
                ],
            }
        ).data

    return paginate(users, request, transform_fn=transform)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_sudo_grant(request):
    """
    Return current-user sudo grant permissions for frontend capability gating.

    Admin users are treated as full capability.
    Non-admin users return explicit SudoGrant state when present.
    """
    if request.user.is_staff:
        return Response(
            {
                "hasSudo": True,
                "canGrantSudo": True,
                "permissions": [p.value for p in SudoPermission],
                "isStaff": True,
            },
            status=status.HTTP_200_OK,
        )

    grant = SudoGrant.objects.filter(user=request.user).first()
    if not grant:
        return Response(
            {
                "hasSudo": False,
                "canGrantSudo": False,
                "permissions": [],
                "isStaff": False,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "hasSudo": True,
            "canGrantSudo": bool(grant.can_grant_sudo),
            "permissions": grant.permissions,
            "isStaff": False,
        },
        status=status.HTTP_200_OK,
    )


def _list_sudo_grants(request):
    """Return sudo grants visible to the current user."""
    if request.user.is_staff:
        grants = SudoGrant.objects.select_related("user", "granted_by").all()
    else:
        grants = SudoGrant.objects.select_related("user", "granted_by").filter(
            granted_by=request.user
        )

    results = [
        {
            "id": g.id,
            "user": {
                "id": g.user.id,
                "username": g.user.username,
                "name": g.user.name or g.user.username,
            },
            "permissions": g.permissions,
            "canGrantSudo": g.can_grant_sudo,
            "grantedAt": g.granted_at.isoformat(),
        }
        for g in grants
    ]
    return Response(results, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsResearcherOrAdmin])
def sudo_grants_collection(request):
    """Dispatch GET (list) and POST (grant) for sudo grants."""
    if request.method == "GET":
        return _list_sudo_grants(request)
    return _grant_sudo(request)


def _grant_sudo(request):
    """
    Grant sudo permissions to a researcher.

    Admins can grant any permissions and set can_grant_sudo=True.
    Sudoed researchers with can_grant_sudo=True can grant a subset of their
    own permissions, but cannot set can_grant_sudo=True (admin only).

    Request Body:
        {
            "user_id": 123,                    # Researcher to grant sudo to
            "permissions": ["CREATE_TEACHER"], # List of SudoPermission values
            "can_grant_sudo": false            # Optional, default false
        }

    Returns:
        200: {"message": "Sudo granted", "grant_id": N}
        400: Validation errors (missing user_id, invalid permissions)
        403: Permission denied (escalation attempt or unauthorized)
        404: User not found or not a researcher

    Permission Rules:
        - Admin (is_staff): Can grant any permissions, set can_grant_sudo=True
        - Researcher with can_grant_sudo: Can grant subset of own permissions
    """
    user_id = request.data.get("user_id")
    permissions = request.data.get("permissions", [])
    can_grant_sudo_flag = request.data.get("can_grant_sudo", False)

    if not user_id:
        return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    grantee = User.objects.filter(id=user_id).first()
    if not grantee:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        grant = grant_sudo_to_researcher(
            granter=request.user,
            grantee=grantee,
            permissions=permissions,
            can_grant_sudo=can_grant_sudo_flag,
        )
        return Response(
            {"message": "Sudo granted", "grant_id": grant.id}, status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


@api_view(["DELETE"])
@permission_classes([IsResearcherOrAdmin])
def revoke_sudo(request, grant_id: int):
    """
    Revoke a sudo grant.

    Admins can revoke any grant. Sudoed researchers can revoke grants
    they created (where they are the granted_by user).

    Args:
        grant_id: ID of the SudoGrant to revoke (path parameter)

    Returns:
        200: {"message": "Sudo revoked"}
        403: Permission denied (not authorized to revoke this grant)
        404: Grant not found

    Permission Rules:
        - Admin (is_staff): Can revoke any grant
        - Researcher: Can revoke grants they created
    """
    try:
        revoke_sudo_grant(revoker=request.user, grant_id=grant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except PermissionError as e:
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
