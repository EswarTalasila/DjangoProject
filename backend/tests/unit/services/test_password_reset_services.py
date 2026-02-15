"""Unit tests for password reset service helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import (
    PasswordResetCode,
    PasswordResetRequestStatus,
    Role,
    StudentProfile,
    TeacherProfile,
    User,
    UserRole,
)
from accounts.services import (
    _can_approve_reset_request,
    _resolve_code_expiry,
    complete_password_reset,
    create_password_reset_request,
    issue_student_reset_code_for_teacher,
    transition_password_reset_request,
)
from courses.models import Course, Enrollment, EnrollmentStatus


def _make_teacher(username: str = "teacher-reset") -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Teacher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)
    return user


def _make_researcher(username: str = "researcher-reset") -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name="Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=user, role=Role.RESEARCHER)
    from accounts.models import ResearcherProfile

    ResearcherProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
@pytest.mark.unit
def test_resolve_code_expiry_defaults_and_bounds():
    """Expiry resolver applies default and enforces time bounds."""

    default_exp = _resolve_code_expiry(None)
    assert default_exp > timezone.now()

    with pytest.raises(ValueError, match="must be in the future"):
        _resolve_code_expiry(timezone.now() - timedelta(minutes=1))


@pytest.mark.django_db
@pytest.mark.unit
def test_create_password_reset_request_rejects_unknown_and_student(admin_user):
    """Unknown identifiers and student role requests are rejected."""

    with pytest.raises(ValueError, match="Unable to create reset request"):
        create_password_reset_request("missing@example.com")

    student = User.objects.create_user(
        username="student-reset",
        email="student-reset@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    with pytest.raises(ValueError, match="Unable to create reset request"):
        create_password_reset_request("student-reset")


@pytest.mark.django_db
@pytest.mark.unit
def test_create_password_reset_request_blocks_duplicate_pending():
    """Only one pending reset request may exist per user at a time."""

    teacher = _make_teacher("teacher-dup")
    create_password_reset_request(teacher.email)

    with pytest.raises(ValueError, match="pending reset request"):
        create_password_reset_request(teacher.email)


@pytest.mark.django_db
@pytest.mark.unit
def test_can_approve_reset_request_role_chain():
    """Admin can approve all, researcher only teacher requests."""

    admin = User.objects.create_user(
        username="admin-reset",
        email="admin-reset@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    researcher = _make_researcher("researcher-approve")
    teacher = _make_teacher("teacher-approve")

    request_teacher, _ = create_password_reset_request(teacher.email)

    assert _can_approve_reset_request(admin, request_teacher) is True
    assert _can_approve_reset_request(researcher, request_teacher) is True
    assert _can_approve_reset_request(teacher, request_teacher) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_transition_password_reset_request_not_found_and_unauthorized():
    """Transition rejects missing requests and unauthorized approvers."""

    teacher = _make_teacher("teacher-transition")
    request_obj, _ = create_password_reset_request(teacher.email)

    with pytest.raises(ValueError, match="not found"):
        transition_password_reset_request(teacher, 999999, PasswordResetRequestStatus.DENIED)

    with pytest.raises(PermissionError, match="Not authorized"):
        transition_password_reset_request(
            teacher, request_obj.id, PasswordResetRequestStatus.DENIED
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_for_teacher_scope_and_success(admin_user):
    """Teacher can issue student reset only for enrolled student in own course."""

    teacher = _make_teacher("teacher-issue")
    course = Course.objects.create(name="Reset Course", teacher_profile=teacher.teacher_profile)

    student = User.objects.create_user(
        username="student-issue",
        email="student-issue@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    student_profile = StudentProfile.objects.create(
        user=student, created_by=admin_user, consent=False
    )

    with pytest.raises(PermissionError, match="not enrolled"):
        issue_student_reset_code_for_teacher(
            teacher=teacher,
            course_id=course.id,
            student_user_id=student.id,
        )

    Enrollment.objects.create(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    )

    reset_request, reset_code = issue_student_reset_code_for_teacher(
        teacher=teacher,
        course_id=course.id,
        student_user_id=student.id,
    )

    assert reset_request.user_id == student.id
    assert reset_code.startswith("RESET-")
    assert PasswordResetCode.objects.filter(request=reset_request).exists()


@pytest.mark.django_db
@pytest.mark.unit
def test_complete_password_reset_invalid_and_weak_password_paths():
    """Invalid code rejected and weak password does not consume reset code."""

    admin = User.objects.create_user(
        username="admin-reset-flow",
        email="admin-reset-flow@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    teacher = _make_teacher("teacher-reset-flow")
    request_obj, _token = create_password_reset_request(teacher.email)
    transitioned, reset_code = transition_password_reset_request(
        admin,
        request_obj.id,
        PasswordResetRequestStatus.APPROVED,
    )

    with pytest.raises(PermissionError, match="Invalid reset code"):
        complete_password_reset(teacher.email, "bad-code", "BetterPass123!")

    with pytest.raises(ValueError, match="uppercase"):
        complete_password_reset(teacher.email, reset_code, "weakpass1!")

    code_obj = PasswordResetCode.objects.get(request=transitioned)
    assert code_obj.used_at is None

    updated = complete_password_reset(teacher.email, reset_code, "BetterPass123!")
    assert updated.id == teacher.id


@pytest.mark.django_db
@pytest.mark.unit
def test_transition_password_reset_request_denied_clears_existing_code():
    """Deny transition removes any existing reset code records for request."""

    admin = User.objects.create_user(
        username="admin-deny",
        email="admin-deny@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    teacher = _make_teacher("teacher-deny")
    approved_request, _ = create_password_reset_request(teacher.email)
    transitioned, reset_code = transition_password_reset_request(
        admin,
        approved_request.id,
        PasswordResetRequestStatus.APPROVED,
    )
    assert reset_code is not None
    assert PasswordResetCode.objects.filter(request=transitioned).exists()

    denied_request, _ = create_password_reset_request(teacher.email)
    denied, token = transition_password_reset_request(
        admin,
        denied_request.id,
        PasswordResetRequestStatus.DENIED,
    )
    assert token is None
    assert denied.status == PasswordResetRequestStatus.DENIED
    assert not PasswordResetCode.objects.filter(request=denied_request).exists()


# --- Branch-coverage additions ---


@pytest.mark.django_db
@pytest.mark.unit
def test_resolve_code_expiry_exceeds_max_window():
    """Expiry beyond 24h maximum window is rejected."""

    from datetime import timedelta as td

    far_future = timezone.now() + td(hours=25)
    with pytest.raises(ValueError, match="exceeds maximum allowed window"):
        _resolve_code_expiry(far_future)


@pytest.mark.django_db
@pytest.mark.unit
def test_transition_non_pending_request_rejected():
    """Transitioning a non-pending (already approved) request is rejected."""

    admin = User.objects.create_user(
        username="admin-non-pending",
        email="admin-non-pending@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    teacher = _make_teacher("teacher-non-pending")
    request_obj, _ = create_password_reset_request(teacher.email)

    # Approve it first
    transition_password_reset_request(admin, request_obj.id, PasswordResetRequestStatus.APPROVED)

    with pytest.raises(ValueError, match="Only pending requests"):
        transition_password_reset_request(admin, request_obj.id, PasswordResetRequestStatus.DENIED)


@pytest.mark.django_db
@pytest.mark.unit
def test_transition_invalid_status_rejected():
    """Invalid status value (like EXPIRED) is rejected for transitions."""

    admin = User.objects.create_user(
        username="admin-invalid-status",
        email="admin-invalid-status@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    teacher = _make_teacher("teacher-invalid-status")
    request_obj, _ = create_password_reset_request(teacher.email)

    with pytest.raises(ValueError, match="Invalid status transition"):
        transition_password_reset_request(admin, request_obj.id, PasswordResetRequestStatus.EXPIRED)


@pytest.mark.django_db
@pytest.mark.unit
def test_verify_password_reset_code_unknown_user():
    """Unknown identifier returns None from verify."""

    from accounts.services import verify_password_reset_code

    assert verify_password_reset_code("nobody@example.com", "RESET-XYZ") is None


@pytest.mark.django_db
@pytest.mark.unit
def test_complete_password_reset_unknown_user():
    """Unknown user raises PermissionError on complete."""

    with pytest.raises(PermissionError, match="Invalid reset code"):
        complete_password_reset("nobody@example.com", "RESET-XYZ", "NewPass123!")


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_non_teacher():
    """Non-teacher user is rejected when issuing student reset code."""

    researcher = _make_researcher("researcher-issue-fail")

    with pytest.raises(PermissionError, match="Teacher profile not found"):
        issue_student_reset_code_for_teacher(teacher=researcher, course_id=1, student_user_id=1)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_missing_course():
    """Non-existent course is rejected."""

    teacher = _make_teacher("teacher-no-course")

    with pytest.raises(ValueError, match="Course not found"):
        issue_student_reset_code_for_teacher(teacher=teacher, course_id=999999, student_user_id=1)


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_wrong_course_owner():
    """Teacher cannot issue reset for another teacher's course."""

    teacher1 = _make_teacher("teacher-own-course")
    teacher2 = _make_teacher("teacher-other-course")

    course = Course.objects.create(name="Other Course", teacher_profile=teacher2.teacher_profile)

    with pytest.raises(PermissionError, match="their own courses"):
        issue_student_reset_code_for_teacher(
            teacher=teacher1, course_id=course.id, student_user_id=1
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_non_student_target(admin_user):
    """Non-student target user is rejected."""

    teacher = _make_teacher("teacher-non-student-target")
    course = Course.objects.create(name="NS Target", teacher_profile=teacher.teacher_profile)
    non_student = _make_teacher("not-a-student")

    with pytest.raises(ValueError, match="Student not found"):
        issue_student_reset_code_for_teacher(
            teacher=teacher, course_id=course.id, student_user_id=non_student.id
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_issue_student_reset_code_missing_student_profile(admin_user):
    """Student without profile is rejected."""

    teacher = _make_teacher("teacher-no-profile")
    course = Course.objects.create(name="No Prof", teacher_profile=teacher.teacher_profile)

    # Create user with student role but no StudentProfile
    student = User.objects.create_user(
        username="no-profile-student",
        email="no-profile@example.com",
        name="No Profile",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)

    with pytest.raises(ValueError, match="Student profile not found"):
        issue_student_reset_code_for_teacher(
            teacher=teacher, course_id=course.id, student_user_id=student.id
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_cleanup_temporary_reset_codes_expires_approved_requests():
    """Cleanup marks expired approved requests as EXPIRED and deletes codes."""

    from accounts.services import cleanup_temporary_reset_codes

    admin = User.objects.create_user(
        username="admin-cleanup",
        email="admin-cleanup@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    teacher = _make_teacher("teacher-cleanup")
    request_obj, _ = create_password_reset_request(teacher.email)
    _, _reset_code = transition_password_reset_request(
        admin, request_obj.id, PasswordResetRequestStatus.APPROVED
    )

    # Force expire the code
    code_obj = PasswordResetCode.objects.get(request=request_obj)
    code_obj.expires_at = timezone.now() - timedelta(minutes=1)
    code_obj.save(update_fields=["expires_at"])

    result = cleanup_temporary_reset_codes()
    assert result["codesDeleted"] >= 1
    assert result["requestsExpired"] >= 1

    request_obj.refresh_from_db()
    assert request_obj.status == PasswordResetRequestStatus.EXPIRED


@pytest.mark.django_db
@pytest.mark.unit
def test_get_password_reset_request_status_various_paths():
    """Status lookup handles unknown user, student user, and valid lookup."""

    from accounts.services import get_password_reset_request_status

    # Unknown user
    assert get_password_reset_request_status("nobody@example.com", "REQ-TOKEN") is None

    # Student user
    admin = User.objects.create_user(
        username="admin-status",
        email="admin-status@example.com",
        name="Admin",
        password="StartPass123!",
        is_staff=True,
    )
    student = User.objects.create_user(
        username="student-status",
        email="student-status@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin, consent=False)
    assert get_password_reset_request_status("student-status", "REQ-TOKEN") is None

    # Valid teacher lookup with wrong token
    teacher = _make_teacher("teacher-status")
    assert get_password_reset_request_status(teacher.email, "wrong-token") is None
