"""Registration views: account registration, invite codes, course enrollment."""

import json
import logging
import sys
from urllib.error import HTTPError, URLError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.throttles import AnonAuthThrottle
from .auth import _set_auth_cookies

logger = logging.getLogger(__name__)


def _v():
    return sys.modules["accounts.views"]


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonAuthThrottle])
def register_account(request):
    """Unified registration endpoint."""
    method = (request.data.get("method") or "").upper()
    payload = {k: v for k, v in request.data.items() if k != "method"}
    if method == "LOCAL":
        return _v()._register_local(request, payload)
    if method == "OAUTH":
        return _v()._register_oauth(request, payload)
    return Response({"detail": "method must be LOCAL or OAUTH"}, status=status.HTTP_400_BAD_REQUEST)


def _register_local(request, payload):
    """Register a new account using a local invite-code flow."""
    v = _v()
    serializer = v.StudentInviteRegisterSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data
    confirm_password = validated.get("confirmPassword")
    if validated["password"] != confirm_password:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    password_errors = v.password_strength_errors(validated["password"])
    if password_errors:
        return Response(
            {"detail": "Password does not meet policy requirements.", "errors": password_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record = v.validate_registration_code(validated["code"])
    if not record:
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    if record.code_type == v.RegistrationCodeType.STUDENT:
        try:
            user, enrollment = v.redeem_student_invite(validated)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        refresh = v.RefreshToken.for_user(user)
        body = v.build_user_response(user)
        body["message"] = "User registered"
        body["courseId"] = enrollment.course_id
        body["createdNewUser"] = True
        body["alreadyEnrolled"] = False
        response = Response(body, status=status.HTTP_201_CREATED)
        return _set_auth_cookies(
            response, access_token=str(refresh.access_token), refresh_token=str(refresh)
        )

    try:
        user = v.redeem_non_student_local_invite(validated)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    refresh = v.RefreshToken.for_user(user)
    body = v.build_user_response(user)
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
    v = _v()
    serializer = v.RegistrationOAuthSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data

    try:
        google_user = v._google_userinfo(validated["accessToken"])
    except (URLError, HTTPError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Google userinfo request failed: %s", exc)
        return Response(
            {"detail": "Invalid Google access token."}, status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception:
        logger.exception("Unexpected error fetching Google userinfo")
        return v.server_error_response()

    google_subject = str(google_user.get("sub", "")).strip()
    google_email = str(google_user.get("email", "")).strip()
    if not google_subject or not google_email:
        return Response(
            {"detail": "Google user profile is missing required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = v.redeem_non_student_oauth_invite(
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

    refresh = v.RefreshToken.for_user(user)
    body = v.build_user_response(user)
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
    v = _v()
    serializer = v.RegistrationCodeValidateInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code = serializer.validated_data["code"]
    record = v.validate_registration_code(code)
    if not record:
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    context = {}
    if record.course_id and record.course is not None:
        context["course_name"] = record.course.name
        teacher_profile = getattr(record.course, "teacher_profile", None)
        if teacher_profile and teacher_profile.user_id:
            context["teacher_name"] = teacher_profile.user.name

    return Response(
        {"valid": True, "code_type": record.code_type, "context": context},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_course_with_code(request):
    """Redeem a student invite code for the authenticated student account."""
    v = _v()
    if v.primary_role(request.user) != v.Role.STUDENT:
        return Response(
            {"detail": "Only student accounts can redeem student codes"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = v.StudentJoinCourseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        enrollment, already_enrolled = v.redeem_student_join_course(
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
    v = _v()
    plaintext_code = getattr(record, "plaintext_code", None)
    return {
        "id": record.id,
        "code": plaintext_code,
        "codePrefix": record.code_prefix,
        "codeType": record.code_type,
        "status": v.registration_code_status(record),
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
    v = _v()
    serializer = v.RegistrationCodeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        created = v.create_registration_codes(
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
        {"count": len(created), "codes": [_serialize_registration_code(r) for r in created]},
        status=status.HTTP_201_CREATED,
    )


def _list_codes(request):
    """List registration codes scoped to the authenticated user's role."""
    v = _v()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    code_type_filter = str(request.query_params.get("codeType", "")).strip().upper()

    queryset = v.registration_code_scope_queryset(request.user)
    if code_type_filter:
        queryset = queryset.filter(code_type=code_type_filter)

    records = list(queryset.order_by("-created_at"))
    if status_filter:
        records = [r for r in records if v.registration_code_status(r) == status_filter]
    return v.paginate(records, request, transform_fn=_serialize_registration_code)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def codes_collection(request):
    """List or create registration codes according to request method."""
    if request.method == "GET":
        return _v()._list_codes(request)
    return _v()._create_codes(request)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def code_detail(request, code_id: int):
    """Get or transition a single registration code within role scope."""
    v = _v()
    if request.method == "GET":
        record = v.registration_code_scope_queryset(request.user).filter(id=code_id).first()
        if not record:
            return Response({"detail": "Registration code not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_registration_code(record), status=status.HTTP_200_OK)

    if request.method == "DELETE":
        try:
            v.remove_registration_code(actor=request.user, registration_code_id=code_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = v.RegistrationCodeUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        updated = v.transition_registration_code_status(
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
