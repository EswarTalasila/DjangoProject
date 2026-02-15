"""
Account service helpers.

This module provides business logic for user account management including:
- Role normalization and assignment
- Profile creation for teachers and students
- Authentication and authorization checks
- User creation from payloads
- OAuth account linking
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import has_sudo_permission, primary_role
from courses.models import Course, Enrollment, EnrollmentStatus

from .models import (
    OAuthAccount,
    OAuthProvider,
    PasswordResetCode,
    PasswordResetRequest,
    PasswordResetRequestStatus,
    RegistrationCode,
    RegistrationCodeType,
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
DEFAULT_RESET_REQUEST_WINDOW = timedelta(minutes=30)
DEFAULT_RESET_CODE_WINDOW = timedelta(minutes=30)
MAX_RESET_CODE_WINDOW = timedelta(hours=24)
REGISTRATION_CODE_TOKEN_BYTES = 12

REGISTRATION_CODE_STATUS_ACTIVE = "ACTIVE"
REGISTRATION_CODE_STATUS_EXHAUSTED = "EXHAUSTED"
REGISTRATION_CODE_STATUS_EXPIRED = "EXPIRED"
REGISTRATION_CODE_STATUS_REVOKED = "REVOKED"
REGISTRATION_CODE_STATUS_ARCHIVED = "ARCHIVED"
REGISTRATION_CODE_HMAC_SALT = "registration-code"
REGISTRATION_CODE_PREFIX_LENGTH = 8


def normalize_username_identifier(username: str) -> str:
    """Normalize login identifiers to lowercase for consistent uniqueness checks."""
    return str(username).strip().lower()


def normalize_registration_code_input(code: str) -> str:
    """Normalize invite code input for deterministic hashing and comparisons."""
    return str(code).strip().upper()


def registration_code_hash(code: str, *, secret: str | None = None) -> str:
    """Return deterministic salted HMAC digest for a registration code."""
    normalized = normalize_registration_code_input(code)
    if not normalized:
        return ""
    return salted_hmac(
        REGISTRATION_CODE_HMAC_SALT,
        normalized,
        secret=secret or settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def registration_code_prefix(code: str) -> str:
    """Return non-sensitive preview prefix for list/detail views."""
    normalized = normalize_registration_code_input(code)
    return normalized[:REGISTRATION_CODE_PREFIX_LENGTH]


def _registration_code_hashes_for_lookup(code: str) -> list[str]:
    """
    Build deterministic code hashes for current and fallback Django secrets.

    This allows seamless SECRET_KEY rotation using SECRET_KEY_FALLBACKS.
    Expected runtime bound is small: 1 hash normally, 2 during rotation.
    """
    normalized = normalize_registration_code_input(code)
    if not normalized:
        return []

    secrets_in_order: list[str] = []
    for secret in [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]:
        if not secret or secret in secrets_in_order:
            continue
        secrets_in_order.append(secret)

    return [
        salted_hmac(
            REGISTRATION_CODE_HMAC_SALT,
            normalized,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()
        for secret in secrets_in_order
    ]


def _hash_secret_token(value: str) -> str:
    """Hash a secret token before persisting it."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generate_secret_token(prefix: str, nbytes: int = 12) -> str:
    """Generate a prefixed token string for request/reset flows."""
    return f"{prefix}-{secrets.token_hex(nbytes).upper()}"


def identifier_allowed_for_user(identifier: str, user: User) -> bool:
    """
    Validate whether an identifier is allowed for a specific user.

    Students must use username; non-students can use username or email.
    """
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return False

    normalized_username = normalize_username_identifier(user.username)
    role = primary_role(user)

    if role == Role.STUDENT:
        return normalized == normalized_username

    if normalized == normalized_username:
        return True

    if user.email:
        return normalized == normalize_username_identifier(user.email)
    return False


def check_identifier_throttle(scope: str, identifier: str) -> bool:
    """Return True if requests for an identifier are still allowed."""
    key = f"auth-throttle:{scope}:{normalize_username_identifier(identifier)}"
    attempts = int(cache.get(key, 0))
    return attempts < LOGIN_RATE_LIMIT_ATTEMPTS


def register_identifier_failure(scope: str, identifier: str) -> None:
    """Increment failed-attempt counter for an identifier."""
    key = f"auth-throttle:{scope}:{normalize_username_identifier(identifier)}"
    attempts = int(cache.get(key, 0)) + 1
    cache.set(key, attempts, LOGIN_RATE_LIMIT_WINDOW_SECONDS)


def clear_identifier_failures(scope: str, identifier: str) -> None:
    """Clear failed-attempt counter for an identifier after successful auth."""
    key = f"auth-throttle:{scope}:{normalize_username_identifier(identifier)}"
    cache.delete(key)


def password_strength_errors(password: str) -> list[str]:
    """Return all password policy violations for AUTH-CN-01."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not any(ch.isupper() for ch in password):
        errors.append("Password must include at least one uppercase letter.")
    if not any(ch.islower() for ch in password):
        errors.append("Password must include at least one lowercase letter.")
    if not any(ch.isdigit() for ch in password):
        errors.append("Password must include at least one number.")
    if not any(not ch.isalnum() for ch in password):
        errors.append("Password must include at least one special character.")
    return errors


def _compact_alnum(value: str) -> str:
    """Keep only lowercase alphanumeric characters."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _unique_username_from_base(base: str) -> str:
    """Generate a unique username candidate by appending numeric suffixes."""
    max_len: int = User._meta.get_field("username").max_length or 150
    normalized_base = normalize_username_identifier(base)[:max_len] or "user"
    candidate = normalized_base
    suffix = 0
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        suffix_text = str(suffix)
        available = max_len - len(suffix_text)
        trimmed_base = normalized_base[:available] if available > 0 else ""
        candidate = f"{trimmed_base}{suffix_text}"
    return candidate


def _base_student_username_from_name(name: str) -> str:
    """
    Create a deterministic base username from a display name.

    Example:
        "Jane Smith" -> "jsmith"
    """
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "student"
    if len(parts) == 1:
        return _compact_alnum(parts[0]) or "student"
    first_initial = _compact_alnum(parts[0])[:1]
    last = _compact_alnum(parts[-1])
    base = f"{first_initial}{last}".strip()
    return base or "student"


def generate_student_username(name: str) -> str:
    """
    Generate a unique student username using name-derived base + numeric suffix.

    First available candidate wins:
    - base
    - base2
    - base3
    - ...
    """
    max_len: int = User._meta.get_field("username").max_length or 150
    base = _base_student_username_from_name(name)[:max_len]
    if not base:
        base = "student"

    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        suffix_text = str(suffix)
        available = max_len - len(suffix_text)
        trimmed_base = base[:available] if available > 0 else ""
        candidate = f"{trimmed_base}{suffix_text}"
    return candidate


def _get_role_value(role: str | None) -> Role:
    """
    Normalize a role string to a valid Role enum value.

    Handles legacy ROLE_ prefixes from the Spring Boot API and defaults to STUDENT
    if no role is provided.

    Args:
        role: Raw role string, possibly with ROLE_ prefix (e.g., "ROLE_TEACHER")

    Returns:
        Normalized Role enum value (RESEARCHER, TEACHER, or STUDENT)

    Raises:
        ValueError: If the role string is not a valid Role choice
    """
    if not role:
        return Role.STUDENT
    if isinstance(role, str) and role.startswith("ROLE_"):
        role = role.replace("ROLE_", "", 1)

    try:
        return Role(role)
    except ValueError as err:
        valid_roles = [r.value for r in Role]
        raise ValueError(f"Invalid role '{role}'. Must be one of: {valid_roles}") from err


def set_single_role(user: User, role: str) -> None:
    """
    Set a single role for a user, replacing any existing roles.

    This ensures each user has exactly one role at a time, which simplifies
    permission checks throughout the application.

    Args:
        user: The user to update
        role: The role to assign (will be normalized)
    """
    normalized = _get_role_value(role)
    UserRole.objects.filter(user=user).delete()
    UserRole.objects.create(user=user, role=normalized)


def ensure_profiles_for_role(user: User, role: str, creator: User | None = None) -> None:
    """
    Create the appropriate profile for a user's role if it does not exist.

    Each role requires a corresponding profile:
    - RESEARCHER: ResearcherProfile
    - TEACHER: TeacherProfile
    - STUDENT: StudentProfile (with consent tracking and creator reference)

    Args:
        user: The user who needs a profile
        role: The user's role (determines which profile to create)
        creator: For students, the user who created this student account
    """
    normalized = _get_role_value(role)
    if normalized == Role.RESEARCHER and not ResearcherProfile.objects.filter(user=user).exists():
        ResearcherProfile.objects.create(user=user)
    if normalized == Role.TEACHER and not TeacherProfile.objects.filter(user=user).exists():
        TeacherProfile.objects.create(user=user)
    if normalized == Role.STUDENT and not StudentProfile.objects.filter(user=user).exists():
        StudentProfile.objects.create(user=user, created_by=creator or user, consent=False)


def build_user_response(user: User, access_token: str, refresh_token: str | None = None) -> dict:
    """
    Build the login response payload for a user.

    This creates the response structure expected by the frontend after
    successful authentication, including the JWT token and user metadata.

    Args:
        user: The authenticated user
        access_token: The JWT access token to include

    Returns:
        Dict with username/name/accessToken/tokenType/role/id fields
    """
    role = primary_role(user)
    payload: dict[str, str] = {
        "email": user.email or user.username,
        "username": user.username,
        "name": user.name,
        "accessToken": access_token,
        "tokenType": "Bearer",
        "role": role,
        "id": str(user.id),
    }
    if refresh_token:
        payload["refreshToken"] = refresh_token
    return payload


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.

    Args:
        username: The user's login identifier
        password: The user's password

    Returns:
        The authenticated User object, or None if authentication fails
    """
    normalized = normalize_username_identifier(username)
    if not normalized:
        return None

    user = find_user_by_identifier(normalized)
    if not user:
        return None

    return authenticate(username=user.username, password=password)


def find_user_by_identifier(identifier: str) -> User | None:
    """Resolve a user using the normalized identifier field."""
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return None
    user = User.objects.filter(username__iexact=normalized).first()
    if user:
        return user
    return User.objects.filter(email__iexact=normalized).first()


def invalidate_user_sessions(user: User) -> int:
    """
    Invalidate all outstanding refresh tokens for a user.

    Returns the number of tokens newly blacklisted.
    """
    blacklisted = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            blacklisted += 1
    return blacklisted


def blacklist_refresh_token(refresh_token: str) -> bool:
    """Blacklist a single refresh token for logout."""
    try:
        token = RefreshToken(refresh_token)  # type: ignore[arg-type]
        token.blacklist()
    except TokenError:
        return False
    return True


def can_create_user(request_user: User, requested_role: str) -> bool:
    """
    Check if request_user is allowed to create a user with the requested role.

    Permission hierarchy:
    - Admins (is_staff) can create researchers and teachers
    - Researchers with sudo can create teachers (CREATE_TEACHER) or students (CREATE_STUDENT)
    - Teachers can create students
    - Students cannot create any users

    Args:
        request_user: The user making the create request
        requested_role: The role for the new user

    Returns:
        True if the creation is allowed, False otherwise
    """
    role = _get_role_value(requested_role)
    request_role = primary_role(request_user)

    # Admin can create researchers and teachers
    if request_user.is_staff:
        return role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can create teachers/students
    if request_role == Role.RESEARCHER:
        if role == Role.TEACHER and has_sudo_permission(
            request_user, SudoPermission.CREATE_TEACHER
        ):
            return True
        if role == Role.STUDENT and has_sudo_permission(
            request_user, SudoPermission.CREATE_STUDENT
        ):
            return True

    # Teacher can create students
    if request_role == Role.TEACHER:
        return role == Role.STUDENT

    return False


def teacher_owns_student(teacher_user: User, student_user: User) -> bool:
    """
    Check if a teacher has ownership over a student via course enrollment.

    A teacher "owns" a student if that student is enrolled in any course
    taught by the teacher. This establishes the permission relationship
    for teachers to manage their students.

    Args:
        teacher_user: The potential teacher
        student_user: The potential student

    Returns:
        True if the student is enrolled in one of the teacher's courses
    """
    if primary_role(teacher_user) != Role.TEACHER:
        return False
    if primary_role(student_user) != Role.STUDENT:
        return False
    try:
        student_profile = student_user.student_profile
    except StudentProfile.DoesNotExist:
        return False
    return Enrollment.objects.filter(
        student_profile=student_profile, course__teacher_profile__user=teacher_user
    ).exists()


def can_edit_user(request_user: User, target_user: User, requested_role: str) -> bool:
    """
    Check if request_user can edit target_user with the requested role.

    Permission rules:
    - Admins (is_staff) can edit researchers and teachers
    - Researchers with EDIT_USER sudo can edit teachers and students
    - Teachers can edit students they own (enrolled in their courses)
    - Students cannot edit any users

    Args:
        request_user: The user making the edit request
        target_user: The user being edited
        requested_role: The role to assign to target_user

    Returns:
        True if the edit is allowed, False otherwise
    """
    # Admin/staff accounts are not editable through role-assignment flows.
    if target_user.is_staff:
        return False

    try:
        target_role = _get_role_value(requested_role)
    except ValueError:
        return False
    request_role = primary_role(request_user)

    # Admin can edit researchers and teachers
    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can edit teachers and students
    if (
        request_role == Role.RESEARCHER
        and target_role
        in (
            Role.TEACHER,
            Role.STUDENT,
        )
        and has_sudo_permission(request_user, SudoPermission.EDIT_USER)
    ):
        return True

    # Teacher can edit students they own
    if request_role == Role.TEACHER:
        return target_role == Role.STUDENT and teacher_owns_student(request_user, target_user)

    return False


def can_delete_user(request_user: User, target_user: User) -> bool:
    """
    Check if request_user can delete target_user.

    Permission rules:
    - Admins (is_staff) can delete researchers and teachers
    - Researchers with DELETE_USER sudo can delete teachers and students
    - Teachers can delete students they own
    - Students cannot delete any users

    Args:
        request_user: The user making the delete request
        target_user: The user to be deleted

    Returns:
        True if the deletion is allowed, False otherwise
    """
    request_role = primary_role(request_user)
    target_role = primary_role(target_user)

    # Admin can delete researchers and teachers
    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can delete teachers and students
    if (
        request_role == Role.RESEARCHER
        and target_role
        in (
            Role.TEACHER,
            Role.STUDENT,
        )
        and has_sudo_permission(request_user, SudoPermission.DELETE_USER)
    ):
        return True

    # Teacher can delete students they own
    if request_role == Role.TEACHER:
        return target_role == Role.STUDENT and teacher_owns_student(request_user, target_user)

    return False


def _mark_request_expired_if_needed(request: PasswordResetRequest) -> None:
    """Transition a pending reset request to EXPIRED when its request window elapsed."""
    if (
        request.status == PasswordResetRequestStatus.PENDING
        and request.expires_at <= timezone.now()
    ):
        request.status = PasswordResetRequestStatus.EXPIRED
        request.reviewed_at = timezone.now()
        request.save(update_fields=["status", "reviewed_at"])


def _can_approve_reset_request(approver: User, request: PasswordResetRequest) -> bool:
    """
    Check AUTH-UC-07 approval chain rules.

    - ADMIN can approve any request
    - RESEARCHER can approve TEACHER requests
    """
    if approver.is_staff:
        return True

    approver_role = primary_role(approver)
    return approver_role == Role.RESEARCHER and request.requested_role == Role.TEACHER


@transaction.atomic
def create_password_reset_request(identifier: str) -> tuple[PasswordResetRequest, str]:
    """
    Create a pending password reset request and return the one-time request token.

    The request token is only returned at creation time.
    """
    user = find_user_by_identifier(identifier)
    if not user:
        raise ValueError("Unable to create reset request.")

    requester_role = primary_role(user)
    if requester_role not in (Role.RESEARCHER, Role.TEACHER):
        # Keep generic wording to avoid leaking account role from this public endpoint.
        raise ValueError("Unable to create reset request.")
    if not identifier_allowed_for_user(identifier, user):
        raise PermissionError("Invalid identifier format for this account role.")

    pending_requests = PasswordResetRequest.objects.select_for_update().filter(
        user=user,
        status=PasswordResetRequestStatus.PENDING,
    )
    for pending in pending_requests:
        _mark_request_expired_if_needed(pending)
    if pending_requests.filter(status=PasswordResetRequestStatus.PENDING).exists():
        raise ValueError("A pending reset request already exists.")

    token = _generate_secret_token("REQ")
    request = PasswordResetRequest.objects.create(
        user=user,
        identifier=normalize_username_identifier(identifier),
        requested_role=requester_role,
        request_token_hash=_hash_secret_token(token),
        status=PasswordResetRequestStatus.PENDING,
        expires_at=timezone.now() + DEFAULT_RESET_REQUEST_WINDOW,
    )
    return request, token


def get_password_reset_request_status(
    identifier: str, request_token: str
) -> PasswordResetRequest | None:
    """Look up reset request status by identifier + request token."""
    user = find_user_by_identifier(identifier)
    if not user:
        return None
    if primary_role(user) == Role.STUDENT:
        return None
    request = (
        PasswordResetRequest.objects.filter(
            user=user,
            identifier=normalize_username_identifier(identifier),
            request_token_hash=_hash_secret_token(request_token),
        )
        .order_by("-id")
        .first()
    )
    if not request:
        return None
    _mark_request_expired_if_needed(request)
    return request


def _resolve_code_expiry(requested_expires_at):
    """Resolve code expiry for non-student approval-based reset codes."""
    now = timezone.now()

    if requested_expires_at is None:
        return now + DEFAULT_RESET_CODE_WINDOW

    max_allowed = now + MAX_RESET_CODE_WINDOW
    if requested_expires_at <= now:
        raise ValueError("expires_at must be in the future.")
    if requested_expires_at > max_allowed:
        raise ValueError("expires_at exceeds maximum allowed window.")
    return requested_expires_at


@transaction.atomic
def transition_password_reset_request(
    approver: User,
    request_id: int,
    new_status: str,
    reason: str | None = None,
    expires_at=None,
) -> tuple[PasswordResetRequest, str | None]:
    """Approve or deny a pending password reset request."""
    request = PasswordResetRequest.objects.select_for_update().filter(id=request_id).first()
    if not request:
        raise ValueError("Reset request not found.")

    _mark_request_expired_if_needed(request)
    if request.status != PasswordResetRequestStatus.PENDING:
        raise ValueError("Only pending requests can be transitioned.")
    if new_status not in (PasswordResetRequestStatus.APPROVED, PasswordResetRequestStatus.DENIED):
        raise ValueError("Invalid status transition.")
    if not _can_approve_reset_request(approver, request):
        raise PermissionError("Not authorized to approve this reset request.")

    request.reviewed_by = approver
    request.reviewed_at = timezone.now()
    request.reason = reason or None

    if new_status == PasswordResetRequestStatus.DENIED:
        request.status = PasswordResetRequestStatus.DENIED
        request.save(update_fields=["status", "reviewed_by", "reviewed_at", "reason"])
        PasswordResetCode.objects.filter(request=request).delete()
        return request, None

    token = _generate_secret_token("RESET")
    request.status = PasswordResetRequestStatus.APPROVED
    request.save(update_fields=["status", "reviewed_by", "reviewed_at", "reason"])

    PasswordResetCode.objects.update_or_create(
        request=request,
        defaults={
            "code_hash": _hash_secret_token(token),
            "expires_at": _resolve_code_expiry(expires_at),
            "used_at": None,
        },
    )
    return request, token


@transaction.atomic
def issue_student_reset_code_for_teacher(
    *,
    teacher: User,
    course_id: int,
    student_user_id: int,
) -> tuple[PasswordResetRequest, str]:
    """
    Issue a reset code directly for a student enrolled in the teacher's course.

    This bypasses the non-student request queue. A fresh APPROVED request record
    is created to anchor the one-time reset code.
    """
    teacher_profile = TeacherProfile.objects.filter(user=teacher).first()
    if not teacher_profile:
        raise PermissionError("Teacher profile not found.")

    course = Course.objects.select_related("teacher_profile").filter(id=course_id).first()
    if not course:
        raise ValueError("Course not found.")
    if course.teacher_profile_id != teacher_profile.id:
        raise PermissionError("Teachers can only generate reset codes for their own courses.")

    student = User.objects.filter(id=student_user_id).first()
    if not student or primary_role(student) != Role.STUDENT:
        raise ValueError("Student not found.")

    student_profile = StudentProfile.objects.filter(user=student).first()
    if not student_profile:
        raise ValueError("Student profile not found.")
    enrolled = Enrollment.objects.filter(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    ).exists()
    if not enrolled:
        raise PermissionError("Student is not enrolled in this course.")

    now = timezone.now()

    # Replace any older in-flight student reset requests with a fresh teacher-issued code.
    open_requests = PasswordResetRequest.objects.select_for_update().filter(
        user=student,
        requested_role=Role.STUDENT,
        status__in=[PasswordResetRequestStatus.PENDING, PasswordResetRequestStatus.APPROVED],
    )
    open_requests.update(
        status=PasswordResetRequestStatus.EXPIRED,
        reviewed_by=teacher,
        reviewed_at=now,
    )

    request_token = _generate_secret_token("REQ")
    reset_request = PasswordResetRequest.objects.create(
        user=student,
        identifier=normalize_username_identifier(student.username),
        requested_role=Role.STUDENT,
        request_token_hash=_hash_secret_token(request_token),
        status=PasswordResetRequestStatus.APPROVED,
        reason="Teacher-initiated student reset.",
        expires_at=now + DEFAULT_RESET_CODE_WINDOW,
        reviewed_by=teacher,
        reviewed_at=now,
    )

    reset_code = _generate_secret_token("RESET")
    PasswordResetCode.objects.create(
        request=reset_request,
        code_hash=_hash_secret_token(reset_code),
        expires_at=reset_request.expires_at,
    )
    return reset_request, reset_code


def verify_password_reset_code(identifier: str, reset_code: str) -> PasswordResetCode | None:
    """Validate whether a reset code is active for the given identifier."""
    user = find_user_by_identifier(identifier)
    if not user:
        return None

    code = (
        PasswordResetCode.objects.select_related("request")
        .filter(
            request__user=user,
            request__identifier=normalize_username_identifier(identifier),
            request__status=PasswordResetRequestStatus.APPROVED,
            code_hash=_hash_secret_token(reset_code),
            used_at__isnull=True,
        )
        .first()
    )
    if not code:
        return None
    if code.expires_at <= timezone.now():
        code.request.status = PasswordResetRequestStatus.EXPIRED
        code.request.reviewed_at = timezone.now()
        code.request.save(update_fields=["status", "reviewed_at"])
        return None
    return code


@transaction.atomic
def complete_password_reset(identifier: str, reset_code: str, new_password: str) -> User:
    """
    Complete password reset using an approved one-time code.

    This operation is atomic per AUTH-CN-08.
    """
    user = find_user_by_identifier(identifier)
    if not user:
        raise PermissionError("Invalid reset code.")

    code = (
        PasswordResetCode.objects.select_for_update()
        .select_related("request", "request__user")
        .filter(
            request__user=user,
            request__identifier=normalize_username_identifier(identifier),
            request__status=PasswordResetRequestStatus.APPROVED,
            code_hash=_hash_secret_token(reset_code),
            used_at__isnull=True,
        )
        .first()
    )
    if not code:
        raise PermissionError("Invalid reset code.")
    if code.expires_at <= timezone.now():
        code.request.status = PasswordResetRequestStatus.EXPIRED
        code.request.reviewed_at = timezone.now()
        code.request.save(update_fields=["status", "reviewed_at"])
        raise PermissionError("Reset code has expired.")

    password_errors = password_strength_errors(new_password)
    if password_errors:
        raise ValueError(password_errors[0])
    if user.check_password(new_password):
        raise ValueError("New password must be different from current password.")

    user.set_password(new_password)
    user.save(update_fields=["password"])
    code.used_at = timezone.now()
    code.save(update_fields=["used_at"])
    return user


@transaction.atomic
def cleanup_temporary_reset_codes(*, now=None) -> dict[str, int]:
    """
    Purge temporary reset codes that are expired or already used.

    This supports AUTH-CN-09 by ensuring one-time reset artifacts are not kept
    long-term. Expired approved requests are marked EXPIRED before code deletion
    so status lookups remain coherent.
    """
    check_time = now or timezone.now()
    expired_request_ids = list(
        PasswordResetCode.objects.filter(
            used_at__isnull=True,
            expires_at__lte=check_time,
            request__status=PasswordResetRequestStatus.APPROVED,
        ).values_list("request_id", flat=True)
    )
    if expired_request_ids:
        PasswordResetRequest.objects.filter(id__in=expired_request_ids).update(
            status=PasswordResetRequestStatus.EXPIRED,
            reviewed_at=check_time,
        )

    deleted_codes, _ = PasswordResetCode.objects.filter(
        models.Q(used_at__isnull=False) | models.Q(expires_at__lte=check_time)
    ).delete()
    return {
        "codesDeleted": deleted_codes,
        "requestsExpired": len(expired_request_ids),
    }


@transaction.atomic
def create_user_from_payload(
    payload: dict, role_override: str | None = None, creator: User | None = None
) -> User:
    """
    Create a new user from a request payload.

    This is the main entry point for user creation, handling:
    - User record creation with password hashing
    - Role assignment (with optional override for security)
    - Profile creation based on role

    The role_override parameter is used to force a specific role regardless
    of what the payload contains, which is important for public registration
    where we always force STUDENT role.

    Args:
        payload: Dict containing username, name, password, and optionally role
        role_override: If provided, this role is used instead of payload role
        creator: For students, the user creating this account

    Returns:
        The newly created User object
    """
    username = normalize_username_identifier(payload.get("username", ""))
    raw_email = payload.get("email")
    email = normalize_username_identifier(raw_email) if raw_email else None
    name = payload.get("name")
    password = payload.get("password")
    role = _get_role_value(role_override or payload.get("role") or Role.STUDENT)

    if role != Role.STUDENT and not email:
        raise ValueError("email is required for non-student users")

    user = User.objects.create_user(
        username=username,
        email=email,
        name=name,
        password=password,
        is_active=True,
    )
    set_single_role(user, role)
    ensure_profiles_for_role(user, role, creator=creator)
    return user


def _select_valid_code_for_update(code: str) -> RegistrationCode | None:
    """Lock and validate an invite code for redemption in the current transaction."""
    candidate_hashes = _registration_code_hashes_for_lookup(code)
    if not candidate_hashes:
        return None
    record = None
    for candidate_hash in candidate_hashes:
        record = (
            RegistrationCode.objects.select_for_update().filter(code_hash=candidate_hash).first()
        )
        if record:
            break
    if not record:
        return None
    now = timezone.now()
    if record.archived_at is not None:
        return None
    if not record.is_active:
        return None
    if record.expires_at <= now:
        return None
    if record.times_used >= record.max_uses:
        return None
    return record


def validate_registration_code(code: str) -> RegistrationCode | None:
    """Validate a code without consuming it."""
    candidate_hashes = _registration_code_hashes_for_lookup(code)
    if not candidate_hashes:
        return None
    record = None
    for candidate_hash in candidate_hashes:
        record = RegistrationCode.objects.filter(code_hash=candidate_hash).first()
        if record:
            break
    if not record:
        return None
    now = timezone.now()
    if record.archived_at is not None:
        return None
    if not record.is_active:
        return None
    if record.expires_at <= now:
        return None
    if record.times_used >= record.max_uses:
        return None
    return record


def _ensure_student_enrollment(user: User, course: Course) -> tuple[Enrollment, bool]:
    """
    Attach a student account to a course, allowing multi-course membership.

    Returns:
        (enrollment, already_enrolled)
    """
    student_profile = StudentProfile.objects.filter(user=user).first()
    if not student_profile:
        raise ValueError("Student profile not found")
    existing = Enrollment.objects.filter(course=course, student_profile=student_profile).first()
    if existing:
        return existing, True

    enrollment = Enrollment.objects.create(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    return enrollment, False


@transaction.atomic
def redeem_student_invite(payload: dict) -> tuple[User, Enrollment]:
    """
    Redeem a student invite code to create a new student account.

    Returns:
        (user, enrollment)
    """
    code: str = payload.get("code") or ""
    password = payload.get("password")
    provided_name = payload.get("name")

    registration_code = _select_valid_code_for_update(code)
    if not registration_code:
        raise ValueError("Invalid or expired code")
    if registration_code.code_type != RegistrationCodeType.STUDENT:
        raise ValueError("Invalid code type for student registration")
    if not registration_code.course_id:
        raise ValueError("Code is missing course association")

    course = registration_code.course
    if course is None:
        raise ValueError("Code is missing course association")

    if not provided_name:
        raise ValueError("name is required when creating a new student account")
    generated_username = generate_student_username(provided_name)
    user = create_user_from_payload(
        {
            "username": generated_username,
            "name": provided_name,
            "password": password,
        },
        role_override=Role.STUDENT,
        creator=None,
    )

    enrollment, already_enrolled = _ensure_student_enrollment(user, course)
    if already_enrolled:
        raise ValueError("Student already enrolled in this course")
    registration_code.times_used += 1
    if registration_code.times_used >= registration_code.max_uses:
        registration_code.is_active = False
    registration_code.save(update_fields=["times_used", "is_active"])
    return user, enrollment


@transaction.atomic
def redeem_student_join_course(user: User, code: str) -> tuple[Enrollment, bool]:
    """
    Redeem a student invite code for an authenticated student account.

    Returns:
        (enrollment, already_enrolled)
    """
    if primary_role(user) != Role.STUDENT:
        raise PermissionError("Only student accounts can redeem student codes")

    registration_code = _select_valid_code_for_update(code)
    if not registration_code:
        raise ValueError("Invalid or expired code")
    if registration_code.code_type != RegistrationCodeType.STUDENT:
        raise ValueError("Invalid code type for student registration")
    if not registration_code.course_id:
        raise ValueError("Code is missing course association")

    course = registration_code.course
    if course is None:
        raise ValueError("Code is missing course association")

    enrollment, already_enrolled = _ensure_student_enrollment(user, course)
    if not already_enrolled:
        registration_code.times_used += 1
        if registration_code.times_used >= registration_code.max_uses:
            registration_code.is_active = False
        registration_code.save(update_fields=["times_used", "is_active"])
    return enrollment, already_enrolled


@transaction.atomic
def redeem_non_student_local_invite(payload: dict) -> User:
    """Redeem a non-student invite code and create account with local credentials."""
    code: str = payload.get("code") or ""
    username = normalize_username_identifier(payload.get("username", ""))
    email = normalize_username_identifier(payload.get("email", ""))
    name = (payload.get("name") or "").strip()
    password = payload.get("password")

    registration_code = _select_valid_code_for_update(code)
    if not registration_code:
        raise ValueError("Invalid or expired code")
    if registration_code.code_type == RegistrationCodeType.STUDENT:
        raise ValueError("Student code flows require student registration")

    if not username:
        raise ValueError("username is required for non-student registration")
    if not email:
        raise ValueError("email is required for non-student registration")
    if _identifier_in_use(username):
        raise ValueError("Username already taken")
    if _identifier_in_use(email):
        raise ValueError("Email already taken")

    role_override = _role_from_registration_code_type(registration_code.code_type)
    user = create_user_from_payload(
        {
            "username": username,
            "email": email,
            "name": name or username,
            "password": password,
        },
        role_override=role_override,
        creator=None,
    )

    registration_code.times_used += 1
    if registration_code.times_used >= registration_code.max_uses:
        registration_code.is_active = False
    registration_code.save(update_fields=["times_used", "is_active"])
    return user


def _identifier_in_use(identifier: str, exclude_user_id: int | None = None) -> bool:
    """Check whether identifier is already used as username or email."""
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return False
    queryset = User.objects.filter(
        models.Q(username__iexact=normalized) | models.Q(email__iexact=normalized)
    )
    if exclude_user_id is not None:
        queryset = queryset.exclude(id=exclude_user_id)
    return queryset.exists()


def _role_from_registration_code_type(code_type: str) -> Role:
    """Map registration code type to the user role being provisioned."""
    if code_type == RegistrationCodeType.STUDENT:
        return Role.STUDENT
    if code_type == RegistrationCodeType.TEACHER:
        return Role.TEACHER
    if code_type == RegistrationCodeType.RESEARCHER:
        return Role.RESEARCHER
    raise ValueError("Unsupported registration code type")


@transaction.atomic
def redeem_non_student_oauth_invite(
    *,
    code: str,
    oauth_subject: str,
    oauth_email: str,
    username: str | None = None,
    name: str | None = None,
    email_verified: bool | None = None,
    picture_url: str | None = None,
) -> User:
    """
    Redeem a non-student invite code and create account via Google OAuth identity.
    """
    registration_code = _select_valid_code_for_update(code)
    if not registration_code:
        raise ValueError("Invalid or expired code")
    if registration_code.code_type == RegistrationCodeType.STUDENT:
        raise ValueError("Student code flows do not support OAuth registration")

    normalized_email = normalize_username_identifier(oauth_email)
    if not normalized_email:
        raise ValueError("OAuth provider did not return a valid email")

    if OAuthAccount.objects.filter(provider=OAuthProvider.GOOGLE, subject=oauth_subject).exists():
        raise ValueError("OAuth account already linked")
    if _identifier_in_use(normalized_email):
        raise ValueError("Email already taken")

    requested_username = normalize_username_identifier(username) if username else ""
    if requested_username:
        if _identifier_in_use(requested_username):
            raise ValueError("Username already taken")
        resolved_username = requested_username
    else:
        base = _compact_alnum(normalized_email.split("@", 1)[0]) or "user"
        resolved_username = _unique_username_from_base(base)

    resolved_name = (name or "").strip() or resolved_username
    role_override = _role_from_registration_code_type(registration_code.code_type)
    user = create_user_from_payload(
        {
            "username": resolved_username,
            "email": normalized_email,
            "name": resolved_name,
            "password": None,
        },
        role_override=role_override,
        creator=None,
    )
    oauth_account = link_or_create_oauth_account(
        user=user,
        subject=oauth_subject,
        email=normalized_email,
    )
    oauth_account.email_verified = email_verified
    oauth_account.picture_url = picture_url
    oauth_account.last_login_at = timezone.now()
    oauth_account.save(update_fields=["email_verified", "picture_url", "last_login_at"])

    registration_code.times_used += 1
    if registration_code.times_used >= registration_code.max_uses:
        registration_code.is_active = False
    registration_code.save(update_fields=["times_used", "is_active"])
    return user


def registration_code_status(registration_code: RegistrationCode, *, now=None) -> str:
    """Derive lifecycle status for a registration code."""
    check_time = now or timezone.now()
    if registration_code.archived_at is not None:
        return REGISTRATION_CODE_STATUS_ARCHIVED
    if registration_code.expires_at <= check_time:
        return REGISTRATION_CODE_STATUS_EXPIRED
    if registration_code.times_used >= registration_code.max_uses:
        return REGISTRATION_CODE_STATUS_EXHAUSTED
    if not registration_code.is_active:
        return REGISTRATION_CODE_STATUS_REVOKED
    return REGISTRATION_CODE_STATUS_ACTIVE


def _can_generate_code_type(user: User, code_type: str) -> bool:
    """Check role-based code generation permissions."""
    if user.is_staff:
        return code_type == RegistrationCodeType.RESEARCHER

    request_role = primary_role(user)
    if request_role == Role.RESEARCHER:
        if code_type == RegistrationCodeType.TEACHER:
            return True
        return code_type == RegistrationCodeType.STUDENT and has_sudo_permission(
            user, SudoPermission.CREATE_STUDENT
        )
    if request_role == Role.TEACHER:
        return code_type == RegistrationCodeType.STUDENT
    return False


@transaction.atomic
def create_registration_codes(
    *,
    creator: User,
    code_type: str,
    count: int,
    uses_per_code: int,
    expires_at,
    course_id: int | None = None,
    metadata: dict | None = None,
) -> list[RegistrationCode]:
    """Generate registration codes according to role and constraint rules."""
    if not _can_generate_code_type(creator, code_type):
        raise PermissionError("Not authorized to generate this code type.")
    now = timezone.now()
    if expires_at <= now:
        raise ValueError("expiresAt must be in the future.")
    if count < 1:
        raise ValueError("count must be >= 1.")
    if uses_per_code < 1:
        raise ValueError("usesPerCode must be >= 1.")

    course = None
    if code_type == RegistrationCodeType.STUDENT:
        if not course_id:
            raise ValueError("courseId is required for student codes.")
        course = Course.objects.filter(id=course_id).first()
        if not course:
            raise ValueError("Course not found.")
        if primary_role(creator) == Role.TEACHER and course.teacher_profile.user_id != creator.id:
            raise PermissionError("Teachers can only generate codes for their own courses.")
    elif course_id is not None:
        raise ValueError("courseId is only valid for student code generation.")
    if metadata:
        if code_type != RegistrationCodeType.TEACHER:
            raise ValueError("metadata is only valid for teacher code generation.")
        if count != 1:
            raise ValueError("metadata can only be set when count is 1.")

    created: list[RegistrationCode] = []
    for _ in range(count):
        candidate = _generate_secret_token("REG", nbytes=REGISTRATION_CODE_TOKEN_BYTES)
        candidate_hashes = _registration_code_hashes_for_lookup(candidate)
        while RegistrationCode.objects.filter(code_hash__in=candidate_hashes).exists():
            candidate = _generate_secret_token("REG", nbytes=REGISTRATION_CODE_TOKEN_BYTES)
            candidate_hashes = _registration_code_hashes_for_lookup(candidate)
        persisted_hash = registration_code_hash(candidate)
        created.append(
            RegistrationCode.objects.create(
                code_hash=persisted_hash,
                code_prefix=registration_code_prefix(candidate),
                code_type=code_type,
                created_by=creator,
                course=course,
                max_uses=uses_per_code,
                times_used=0,
                expires_at=expires_at,
                is_active=True,
                metadata=metadata or None,
            )
        )
        created[-1].plaintext_code = candidate  # type: ignore[attr-defined]
    return created


def registration_code_scope_queryset(user: User, *, include_related: bool = True):
    """Return scoped queryset for code list/detail operations."""
    base = RegistrationCode.objects.all()
    if include_related:
        base = base.select_related("course", "created_by")
    if user.is_staff:
        return base
    request_role = primary_role(user)
    if request_role == Role.RESEARCHER:
        allowed_types = [RegistrationCodeType.TEACHER]
        if has_sudo_permission(user, SudoPermission.CREATE_STUDENT):
            allowed_types.append(RegistrationCodeType.STUDENT)
        return base.filter(created_by=user, code_type__in=allowed_types)
    if request_role == Role.TEACHER:
        return base.filter(created_by=user, code_type=RegistrationCodeType.STUDENT)
    return base.none()


@transaction.atomic
def transition_registration_code_status(
    *,
    actor: User,
    registration_code_id: int,
    next_status: str,
) -> RegistrationCode:
    """Transition a registration code to REVOKED or ARCHIVED when allowed."""
    registration_code: RegistrationCode | None = (
        registration_code_scope_queryset(actor, include_related=False)
        .select_for_update()
        .filter(id=registration_code_id)
        .first()
    )
    if not registration_code:
        raise ValueError("Registration code not found.")

    current_status = registration_code_status(registration_code)
    if next_status == REGISTRATION_CODE_STATUS_REVOKED:
        if current_status != REGISTRATION_CODE_STATUS_ACTIVE:
            raise ValueError("Only ACTIVE codes can be revoked.")
        registration_code.is_active = False
        registration_code.save(update_fields=["is_active"])
        return registration_code

    if next_status == REGISTRATION_CODE_STATUS_ARCHIVED:
        if current_status not in (
            REGISTRATION_CODE_STATUS_EXHAUSTED,
            REGISTRATION_CODE_STATUS_EXPIRED,
            REGISTRATION_CODE_STATUS_REVOKED,
        ):
            raise ValueError("Only EXHAUSTED, EXPIRED, or REVOKED codes can be archived.")
        registration_code.archived_at = timezone.now()
        registration_code.save(update_fields=["archived_at"])
        return registration_code

    raise ValueError("Unsupported status transition.")


def link_or_create_oauth_account(user: User, subject: str, email: str) -> OAuthAccount:
    """
    Link a Google OAuth account to a user, or update an existing link.

    This is called during Google OAuth login to associate the Google account
    with the local user account. If the link already exists, it updates the
    email in case it has changed.

    Args:
        user: The local user to link
        subject: The Google account subject ID (unique identifier)
        email: The email from the Google account

    Returns:
        The OAuthAccount linking the user to their Google account
    """
    account, _ = OAuthAccount.objects.update_or_create(
        provider=OAuthProvider.GOOGLE,
        subject=subject,
        defaults={"user": user, "email": email},
    )
    return account


def _can_grant_permissions(
    granter: User, permissions: list[str], can_grant_sudo: bool
) -> tuple[bool, str]:
    """
    Check if granter can grant the specified permissions.

    Permission rules:
    - Admins (is_staff) can grant any permissions and set can_grant_sudo=True
    - Sudoed researchers with can_grant_sudo=True can grant, but:
      - Cannot set can_grant_sudo=True (admin only)
      - Can only grant permissions they hold (subset check)

    Args:
        granter: The user attempting to grant permissions
        permissions: List of SudoPermission values to grant
        can_grant_sudo: Whether to allow the grantee to grant sudo to others

    Returns:
        Tuple of (allowed, error_message). If allowed is True, error_message is empty.
    """
    if granter.is_staff:
        return True, ""

    try:
        granter_grant = granter.sudo_grant
    except SudoGrant.DoesNotExist:
        return False, "Granter does not have sudo permissions"

    if not granter_grant.can_grant_sudo:
        return False, "Granter cannot grant sudo (can_grant_sudo=False)"

    if can_grant_sudo:
        return False, "Only admins can set can_grant_sudo=True"

    # Subset check: granter must hold all permissions being granted
    missing = [p for p in permissions if p not in granter_grant.permissions]
    if missing:
        return False, f"Cannot grant permissions you don't hold: {missing}"

    return True, ""


@transaction.atomic
def grant_sudo_to_researcher(
    granter: User, grantee: User, permissions: list[str], can_grant_sudo: bool = False
) -> SudoGrant:
    """
    Grant sudo permissions to a researcher.

    This function creates or updates a SudoGrant for the grantee, allowing them
    to perform elevated actions. Enforces escalation prevention rules.

    Args:
        granter: The admin or sudoed researcher granting permissions
        grantee: The researcher receiving sudo permissions (must have RESEARCHER role)
        permissions: List of SudoPermission values to grant
        can_grant_sudo: Whether grantee can grant sudo to other researchers (admin only)

    Returns:
        The created or updated SudoGrant

    Raises:
        ValueError: If grantee is not a researcher
        PermissionError: If granter is not authorized or attempting escalation
    """
    # Verify grantee has RESEARCHER role
    grantee_role = primary_role(grantee)
    if grantee_role != Role.RESEARCHER:
        raise ValueError(f"Grantee must have RESEARCHER role, has {grantee_role}")

    # Verify granter is authorized
    allowed, error = _can_grant_permissions(granter, permissions, can_grant_sudo)
    if not allowed:
        raise PermissionError(error)

    # Create or update the SudoGrant
    try:
        grant = grantee.sudo_grant
        # Update existing grant
        grant.permissions = permissions
        grant.can_grant_sudo = can_grant_sudo
        grant.granted_by = granter
    except SudoGrant.DoesNotExist:
        # Create new grant
        grant = SudoGrant(
            user=grantee,
            granted_by=granter,
            permissions=permissions,
            can_grant_sudo=can_grant_sudo,
        )

    # Validate permissions against enum before saving
    grant.full_clean()
    grant.save()
    return grant


@transaction.atomic
def revoke_sudo_grant(revoker: User, grant_id: int) -> None:
    """
    Revoke a sudo grant.

    Args:
        revoker: The admin or sudoed researcher revoking the grant
        grant_id: ID of the SudoGrant to revoke

    Raises:
        ValueError: If grant not found
        PermissionError: If revoker is not authorized to revoke this grant
    """
    try:
        grant = SudoGrant.objects.get(id=grant_id)
    except SudoGrant.DoesNotExist as err:
        raise ValueError(f"SudoGrant with id {grant_id} not found") from err

    # Verify revoker is authorized
    if revoker.is_staff:
        # Admin can revoke any grant
        grant.delete()
        return

    # Sudoed researcher can revoke grants they created
    if grant.granted_by_id == revoker.id:
        grant.delete()
        return

    raise PermissionError("You can only revoke grants you created")
