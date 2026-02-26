"""Unit tests for issuer-driven password reset service helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import (
    PasswordResetCode,
    PasswordResetRequestStatus,
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from accounts.services import (
    cleanup_temporary_reset_codes,
    complete_password_reset,
    issue_password_reset_code,
    verify_password_reset_code,
)
from courses.models import Course, Enrollment, EnrollmentStatus


def _make_admin(username: str = "admin-reset") -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Admin User",
        password="StartPass123!",
        is_staff=True,
    )


def _make_teacher(username: str = "teacher-reset") -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Teacher User",
        password="StartPass123!",
    )
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)
    return user


def _make_researcher(username: str = "researcher-reset") -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Researcher User",
        password="StartPass123!",
    )
    UserRole.objects.create(user=user, role=Role.RESEARCHER)
    ResearcherProfile.objects.create(user=user)
    return user


def _make_student(*, username: str = "student-reset", created_by: User) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Student User",
        password="StartPass123!",
    )
    UserRole.objects.create(user=user, role=Role.STUDENT)
    StudentProfile.objects.create(user=user, created_by=created_by, consent=False)
    return user


def _enroll_student_with_teacher(*, teacher: User, student: User) -> Course:
    course = Course.objects.create(
        name="Reset Scope Course", teacher_profile=teacher.teacher_profile
    )
    Enrollment.objects.create(
        course=course,
        student_profile=student.student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    return course


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_target_not_found():
    """Issuance rejects unknown target user IDs."""
    admin = _make_admin("admin-target-missing")

    with pytest.raises(ValueError, match="Target user not found"):
        issue_password_reset_code(issuer=admin, target_user_id=999999)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_blocks_admin_targets():
    """Issuance rejects admin targets, even when issuer is admin."""
    issuer = _make_admin("admin-issuer")
    target_admin = _make_admin("admin-target")

    with pytest.raises(PermissionError, match="cannot be issued for admin accounts"):
        issue_password_reset_code(issuer=issuer, target_user_id=target_admin.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_teacher_scope_enforced():
    """Teacher can issue only for enrolled students in their owned courses."""
    admin = _make_admin("admin-teacher-scope")
    teacher = _make_teacher("teacher-scope")
    student = _make_student(username="student-scope", created_by=admin)

    with pytest.raises(PermissionError, match="not enrolled in your courses"):
        issue_password_reset_code(issuer=teacher, target_user_id=student.id)

    _enroll_student_with_teacher(teacher=teacher, student=student)
    reset_request, reset_code = issue_password_reset_code(
        issuer=teacher,
        target_user_id=student.id,
    )

    assert reset_request.user_id == student.id
    assert reset_request.requested_role == Role.STUDENT
    assert reset_code.startswith("RESET-")

    with pytest.raises(PermissionError, match="Permission denied"):
        issue_password_reset_code(issuer=teacher, target_user_id=teacher.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_blocks_self_issuance_for_all_roles():
    """Self-issuance is denied for admin, researcher, and teacher issuers."""
    admin = _make_admin("admin-self-target")
    researcher = _make_researcher("researcher-self-target")
    teacher = _make_teacher("teacher-self-target")

    for issuer in (admin, researcher, teacher):
        with pytest.raises(PermissionError, match="Permission denied"):
            issue_password_reset_code(issuer=issuer, target_user_id=issuer.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_researcher_default_permissions():
    """Researcher default issuance is teacher-only without sudo extensions."""
    admin = _make_admin("admin-researcher-default")
    researcher = _make_researcher("researcher-default")
    teacher = _make_teacher("teacher-default-target")
    student = _make_student(username="student-default-target", created_by=admin)
    researcher_target = _make_researcher("researcher-default-target")

    issued, reset_code = issue_password_reset_code(issuer=researcher, target_user_id=teacher.id)
    assert issued.user_id == teacher.id
    assert issued.requested_role == Role.TEACHER
    assert reset_code.startswith("RESET-")

    with pytest.raises(PermissionError, match="Not authorized"):
        issue_password_reset_code(issuer=researcher, target_user_id=student.id)

    with pytest.raises(PermissionError, match="Not authorized"):
        issue_password_reset_code(issuer=researcher, target_user_id=researcher_target.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_researcher_sudo_extensions():
    """Researcher sudo flags enable student/researcher issuance targets."""
    admin = _make_admin("admin-researcher-sudo")
    researcher = _make_researcher("researcher-sudo")
    student = _make_student(username="student-sudo-target", created_by=admin)
    researcher_target = _make_researcher("researcher-sudo-target")

    SudoGrant.objects.create(
        user=researcher,
        granted_by=admin,
        can_grant_sudo=False,
        permissions=[
            SudoPermission.ISSUE_STUDENT_RESET_CODE.value,
            SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value,
        ],
    )

    issued_student, _ = issue_password_reset_code(issuer=researcher, target_user_id=student.id)
    assert issued_student.requested_role == Role.STUDENT

    issued_researcher, _ = issue_password_reset_code(
        issuer=researcher,
        target_user_id=researcher_target.id,
    )
    assert issued_researcher.requested_role == Role.RESEARCHER


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_admin_ignores_teacher_scope():
    """Admin can issue for eligible non-admin roles without enrollment constraints."""
    admin = _make_admin("admin-global-reset")
    teacher = _make_teacher("teacher-global-target")
    student = _make_student(username="student-global-target", created_by=admin)

    issued_teacher, _ = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)
    assert issued_teacher.requested_role == Role.TEACHER

    issued_student, _ = issue_password_reset_code(issuer=admin, target_user_id=student.id)
    assert issued_student.requested_role == Role.STUDENT


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_password_reset_code_reissue_invalidates_prior_code():
    """A new issuance expires the prior approved request/code for the same target."""
    admin = _make_admin("admin-reissue")
    teacher = _make_teacher("teacher-reissue")

    first_request, first_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)
    second_request, second_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    assert first_request.id != second_request.id
    assert first_code != second_code
    assert verify_password_reset_code(teacher.username, first_code) is None
    assert verify_password_reset_code(teacher.username, second_code) is not None

    first_request.refresh_from_db()
    assert first_request.status == PasswordResetRequestStatus.EXPIRED


@pytest.mark.django_db
@pytest.mark.unit
def test_verify_password_reset_code_handles_unknown_invalid_and_expired():
    """Verify returns None for unknown identifier, bad code, and expired codes."""
    admin = _make_admin("admin-verify")
    teacher = _make_teacher("teacher-verify")
    request_obj, reset_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    assert verify_password_reset_code("missing-user", reset_code) is None
    assert verify_password_reset_code(teacher.username, "RESET-INVALID") is None

    code_obj = PasswordResetCode.objects.get(request=request_obj)
    code_obj.expires_at = timezone.now() - timedelta(minutes=1)
    code_obj.save(update_fields=["expires_at"])

    assert verify_password_reset_code(teacher.username, reset_code) is None
    request_obj.refresh_from_db()
    assert request_obj.status == PasswordResetRequestStatus.EXPIRED


@pytest.mark.django_db
@pytest.mark.unit
def test_complete_password_reset_rejects_invalid_or_expired_code():
    """Complete rejects bad codes and expired codes."""
    admin = _make_admin("admin-complete-invalid")
    teacher = _make_teacher("teacher-complete-invalid")
    request_obj, reset_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    with pytest.raises(PermissionError, match="Invalid reset code"):
        complete_password_reset(teacher.username, "RESET-BAD", "BetterPass123!")

    code_obj = PasswordResetCode.objects.get(request=request_obj)
    code_obj.expires_at = timezone.now() - timedelta(minutes=1)
    code_obj.save(update_fields=["expires_at"])

    with pytest.raises(PermissionError, match="has expired"):
        complete_password_reset(teacher.username, reset_code, "BetterPass123!")


@pytest.mark.django_db
@pytest.mark.unit
def test_complete_password_reset_rejects_weak_or_reused_password():
    """Complete enforces password strength and rejects reusing current password."""
    admin = _make_admin("admin-complete-policy")
    teacher = _make_teacher("teacher-complete-policy")
    request_obj, reset_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    with pytest.raises(ValueError, match="uppercase"):
        complete_password_reset(teacher.username, reset_code, "weakpass1!")

    code_obj = PasswordResetCode.objects.get(request=request_obj)
    assert code_obj.used_at is None

    with pytest.raises(ValueError, match="different from current password"):
        complete_password_reset(teacher.username, reset_code, "StartPass123!")
    code_obj.refresh_from_db()
    assert code_obj.used_at is None


@pytest.mark.django_db
@pytest.mark.unit
def test_complete_password_reset_marks_code_used_and_prevents_reuse():
    """Successful completion consumes the code and blocks second use."""
    admin = _make_admin("admin-complete-happy")
    teacher = _make_teacher("teacher-complete-happy")
    request_obj, reset_code = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    updated_user = complete_password_reset(teacher.username, reset_code, "BetterPass123!")
    assert updated_user.id == teacher.id
    assert updated_user.check_password("BetterPass123!")

    code_obj = PasswordResetCode.objects.get(request=request_obj)
    assert code_obj.used_at is not None

    with pytest.raises(PermissionError, match="Invalid reset code"):
        complete_password_reset(teacher.username, reset_code, "AnotherPass123!")


@pytest.mark.django_db
@pytest.mark.unit
def test_cleanup_temporary_reset_codes_expires_requests_and_deletes_codes():
    """Cleanup expires approved requests for expired codes and deletes artifacts."""
    admin = _make_admin("admin-cleanup")
    teacher = _make_teacher("teacher-cleanup")
    request_obj, _ = issue_password_reset_code(issuer=admin, target_user_id=teacher.id)

    code_obj = PasswordResetCode.objects.get(request=request_obj)
    code_obj.expires_at = timezone.now() - timedelta(minutes=1)
    code_obj.save(update_fields=["expires_at"])

    result = cleanup_temporary_reset_codes()
    assert result["codesDeleted"] >= 1
    assert result["requestsExpired"] >= 1

    request_obj.refresh_from_db()
    assert request_obj.status == PasswordResetRequestStatus.EXPIRED
    assert not PasswordResetCode.objects.filter(request=request_obj).exists()
