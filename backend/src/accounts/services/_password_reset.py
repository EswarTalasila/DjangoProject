"""Password reset workflow: issuer-generated codes, verification, and completion."""

from django.db import models, transaction
from django.utils import timezone

from core.permissions import has_sudo_permission, primary_role
from courses.models import Enrollment, EnrollmentStatus

from ..models import (
    PasswordResetCode,
    PasswordResetRequest,
    PasswordResetRequestStatus,
    Role,
    StudentProfile,
    SudoPermission,
    User,
)
from ._auth import find_user_by_identifier
from ._utils import (
    DEFAULT_RESET_CODE_WINDOW,
    _generate_secret_token,
    _hash_secret_token,
    normalize_username_identifier,
    password_strength_errors,
)


def _expire_open_reset_requests(*, target_user: User, reviewer: User) -> None:
    """Expire pending/approved reset requests for a target user."""
    now = timezone.now()
    PasswordResetRequest.objects.select_for_update().filter(
        user=target_user,
        status__in=[PasswordResetRequestStatus.PENDING, PasswordResetRequestStatus.APPROVED],
    ).update(
        status=PasswordResetRequestStatus.EXPIRED,
        reviewed_by=reviewer,
        reviewed_at=now,
    )


def _teacher_can_issue_for_student(*, teacher: User, student: User) -> bool:
    """Return True when a student is actively enrolled in any teacher-owned course."""
    student_profile = StudentProfile.objects.filter(user=student).first()
    if not student_profile:
        return False
    return Enrollment.objects.filter(
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
        course__teacher_profile__user=teacher,
    ).exists()


def _authorize_reset_issuance(*, issuer: User, target: User) -> None:
    """Raise PermissionError when issuer is not allowed to issue for the target user."""
    if issuer.pk == target.pk:
        raise PermissionError("Permission denied.")
    if target.is_staff:
        raise PermissionError("Reset codes cannot be issued for admin accounts.")

    target_role = primary_role(target)
    if target_role not in (Role.STUDENT, Role.TEACHER, Role.RESEARCHER):
        raise PermissionError("Target role is not eligible for reset issuance.")

    if issuer.is_staff:
        return

    issuer_role = primary_role(issuer)
    if issuer_role == Role.TEACHER:
        if target_role != Role.STUDENT:
            raise PermissionError("Teachers can only issue reset codes for students.")
        if not _teacher_can_issue_for_student(teacher=issuer, student=target):
            raise PermissionError("Student is not enrolled in your courses.")
        return

    if issuer_role == Role.RESEARCHER:
        if target_role == Role.TEACHER:
            return
        if target_role == Role.STUDENT and has_sudo_permission(
            issuer, SudoPermission.ISSUE_STUDENT_RESET_CODE
        ):
            return
        if target_role == Role.RESEARCHER and has_sudo_permission(
            issuer, SudoPermission.ISSUE_RESEARCHER_RESET_CODE
        ):
            return
        raise PermissionError("Not authorized to issue a reset code for this target role.")

    raise PermissionError("Not authorized to issue reset codes.")


@transaction.atomic
def issue_password_reset_code(
    *,
    issuer: User,
    target_user_id: int,
) -> tuple[PasswordResetRequest, str]:
    """Issue a one-time reset code for a target user according to issuer policy."""
    target = User.objects.select_for_update().filter(id=target_user_id).first()
    if not target:
        raise ValueError("Target user not found.")

    _authorize_reset_issuance(issuer=issuer, target=target)
    _expire_open_reset_requests(target_user=target, reviewer=issuer)

    now = timezone.now()
    target_role = primary_role(target)
    reset_request = PasswordResetRequest.objects.create(
        user=target,
        identifier=normalize_username_identifier(target.username),
        requested_role=target_role,
        request_token_hash=_hash_secret_token(_generate_secret_token("REQ")),
        status=PasswordResetRequestStatus.APPROVED,
        reason="Issuer-generated reset code.",
        expires_at=now + DEFAULT_RESET_CODE_WINDOW,
        reviewed_by=issuer,
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
