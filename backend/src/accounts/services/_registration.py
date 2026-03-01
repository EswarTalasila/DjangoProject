"""Registration code management and redemption."""

import re

from django.db import transaction
from django.utils import timezone

from core.permissions import has_sudo_permission, primary_role
from courses.models import Course, Enrollment, EnrollmentStatus

from ..models import (
    OAuthAccount,
    OAuthProvider,
    RegistrationCode,
    RegistrationCodeType,
    Role,
    StudentProfile,
    SudoPermission,
    User,
)
from ._auth import link_or_create_oauth_account
from ._roles import create_user_from_payload
_NAME_RE = re.compile(r"^[A-Za-z]+$")


def _validate_name_field(value: str, field: str) -> None:
    """Raise ValueError if a name field contains non-letter characters."""
    if not _NAME_RE.match(value):
        raise ValueError(f"{field} must contain only letters.")


from ._utils import (
    REGISTRATION_CODE_STATUS_ACTIVE,
    REGISTRATION_CODE_STATUS_ARCHIVED,
    REGISTRATION_CODE_STATUS_EXHAUSTED,
    REGISTRATION_CODE_STATUS_EXPIRED,
    REGISTRATION_CODE_STATUS_REVOKED,
    REGISTRATION_CODE_TOKEN_BYTES,
    _generate_secret_token,
    _registration_code_hashes_for_lookup,
    generate_managed_username,
    identifier_in_use,
    normalize_username_identifier,
    registration_code_hash,
    registration_code_prefix,
)


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
    first_name = (payload.get("firstName") or "").strip()
    last_name = (payload.get("lastName") or "").strip()

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

    if not first_name or not last_name:
        raise ValueError("firstName and lastName are required when creating a new student account")
    _validate_name_field(first_name, "firstName")
    _validate_name_field(last_name, "lastName")
    provided_name = f"{first_name} {last_name}".strip()
    generated_username = generate_managed_username(first_name=first_name, last_name=last_name)
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
    email = normalize_username_identifier(payload.get("email", ""))
    first_name = (payload.get("firstName") or "").strip()
    last_name = (payload.get("lastName") or "").strip()
    password = payload.get("password")

    registration_code = _select_valid_code_for_update(code)
    if not registration_code:
        raise ValueError("Invalid or expired code")
    if registration_code.code_type == RegistrationCodeType.STUDENT:
        raise ValueError("Student code flows require student registration")

    if not first_name or not last_name:
        raise ValueError("firstName and lastName are required for non-student registration")
    _validate_name_field(first_name, "firstName")
    _validate_name_field(last_name, "lastName")
    if not email:
        raise ValueError("email is required for non-student registration")
    if identifier_in_use(email):
        raise ValueError("Email already taken")
    name = f"{first_name} {last_name}".strip()
    generated_username = generate_managed_username(
        first_name=first_name,
        last_name=last_name,
    )

    role_override = _role_from_registration_code_type(registration_code.code_type)
    user = create_user_from_payload(
        {
            "username": generated_username,
            "email": email,
            "name": name,
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
    first_name: str | None = None,
    last_name: str | None = None,
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
    if identifier_in_use(normalized_email):
        raise ValueError("Email already taken")

    resolved_first = (first_name or "").strip()
    resolved_last = (last_name or "").strip()
    if not resolved_first or not resolved_last:
        raise ValueError("firstName and lastName are required for OAuth registration")
    _validate_name_field(resolved_first, "firstName")
    _validate_name_field(resolved_last, "lastName")
    resolved_name = f"{resolved_first} {resolved_last}".strip()
    resolved_username = generate_managed_username(
        first_name=resolved_first,
        last_name=resolved_last,
    )
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
        return True

    request_role = primary_role(user)
    if request_role == Role.RESEARCHER:
        if code_type == RegistrationCodeType.RESEARCHER:
            return has_sudo_permission(user, SudoPermission.ISSUE_RESEARCHER_REG_CODE)
        if code_type == RegistrationCodeType.TEACHER:
            return True
        return code_type == RegistrationCodeType.STUDENT and has_sudo_permission(
            user, SudoPermission.ISSUE_STUDENT_REG_CODE
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
        if has_sudo_permission(user, SudoPermission.ISSUE_STUDENT_REG_CODE):
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
