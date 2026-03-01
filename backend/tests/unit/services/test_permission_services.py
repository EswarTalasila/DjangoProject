"""Unit tests for authorization/sudo service helpers."""

from __future__ import annotations

import pytest

from accounts.models import ResearcherProfile, Role, StudentProfile, TeacherProfile, User, UserRole
from accounts.services import (
    _can_grant_permissions,
    can_create_user,
    can_delete_user,
    can_edit_user,
    grant_sudo_to_researcher,
    revoke_sudo_grant,
    teacher_owns_student,
)
from courses.models import Course, Enrollment, EnrollmentStatus
from tests.factories import SudoGrantFactory


def _mk_user(*, username: str, role: str, staff: bool = False):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name=username,
        password="StartPass123!",
    )
    if staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        return user
    UserRole.objects.create(user=user, role=role)
    if role == Role.TEACHER:
        TeacherProfile.objects.create(user=user)
    if role == Role.RESEARCHER:
        ResearcherProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
@pytest.mark.unit
def test_can_create_user_role_matrix():
    """Role matrix for create-user permissions is enforced."""

    admin = _mk_user(username="admin-create", role=Role.RESEARCHER, staff=True)
    teacher = _mk_user(username="teacher-create", role=Role.TEACHER)
    researcher = _mk_user(username="researcher-create", role=Role.RESEARCHER)

    assert can_create_user(admin, Role.RESEARCHER) is True
    assert can_create_user(admin, Role.STUDENT) is False
    assert can_create_user(teacher, Role.STUDENT) is True
    assert can_create_user(teacher, Role.TEACHER) is False
    assert can_create_user(researcher, Role.TEACHER) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_teacher_owns_student_true_and_false(admin_user):
    """Teacher ownership depends on enrollment relationship."""

    teacher = _mk_user(username="teacher-own", role=Role.TEACHER)
    student = User.objects.create_user(
        username="student-own",
        email="student-own@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    student_profile = StudentProfile.objects.create(
        user=student, created_by=admin_user, consent=False
    )

    course = Course.objects.create(name="Own Course", teacher_profile=teacher.teacher_profile)

    assert teacher_owns_student(teacher, student) is False

    Enrollment.objects.create(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    )

    assert teacher_owns_student(teacher, student) is True


@pytest.mark.django_db
@pytest.mark.unit
def test_can_edit_and_delete_user_teacher_scope(admin_user):
    """Teacher can edit/delete only owned students."""

    teacher = _mk_user(username="teacher-edit", role=Role.TEACHER)
    student = User.objects.create_user(
        username="student-edit",
        email="student-edit@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    student_profile = StudentProfile.objects.create(
        user=student, created_by=admin_user, consent=False
    )

    course = Course.objects.create(name="Edit Course", teacher_profile=teacher.teacher_profile)
    Enrollment.objects.create(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    )

    assert can_edit_user(teacher, student, Role.STUDENT) is True
    assert can_delete_user(teacher, student) is True


@pytest.mark.django_db
@pytest.mark.unit
def test_can_grant_permissions_escalation_protection():
    """Researcher granter cannot delegate permissions they do not hold."""

    admin = _mk_user(username="admin-grant", role=Role.RESEARCHER, staff=True)
    granter = _mk_user(username="granter", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=granter,
        granted_by=admin,
        permissions=["CREATE_STUDENT"],
        can_grant_sudo=True,
    )

    allowed, message = _can_grant_permissions(granter, ["CREATE_STUDENT"], False)
    assert allowed is True

    denied, message = _can_grant_permissions(granter, ["DELETE_USER"], False)
    assert denied is False
    assert "don't hold" in message


@pytest.mark.django_db
@pytest.mark.unit
def test_grant_sudo_to_researcher_create_and_update_paths():
    """Grant call creates new record, then updates existing one."""

    admin = _mk_user(username="admin-sudo", role=Role.RESEARCHER, staff=True)
    grantee = _mk_user(username="grantee-sudo", role=Role.RESEARCHER)

    created = grant_sudo_to_researcher(admin, grantee, ["CREATE_STUDENT"], False)
    assert created.permissions == ["CREATE_STUDENT"]

    updated = grant_sudo_to_researcher(admin, grantee, ["EDIT_USER"], False)
    assert updated.id == created.id
    assert updated.permissions == ["EDIT_USER"]


@pytest.mark.django_db
@pytest.mark.unit
def test_revoke_sudo_grant_authorization_rules():
    """Admin can revoke any; non-creator non-admin is denied."""

    admin = _mk_user(username="admin-revoke", role=Role.RESEARCHER, staff=True)
    creator = _mk_user(username="creator-revoke", role=Role.RESEARCHER)
    other = _mk_user(username="other-revoke", role=Role.RESEARCHER)
    grantee = _mk_user(username="grantee-revoke", role=Role.RESEARCHER)

    grant = SudoGrantFactory(user=grantee, granted_by=creator, permissions=["CREATE_STUDENT"])

    with pytest.raises(PermissionError, match="only revoke grants you created"):
        revoke_sudo_grant(other, grant.id)

    revoke_sudo_grant(admin, grant.id)
    from accounts.models import SudoGrant

    assert not SudoGrant.objects.filter(id=grant.id).exists()


# --- Branch-coverage additions ---


@pytest.mark.django_db
@pytest.mark.unit
def test_can_create_user_researcher_with_create_teacher_sudo():
    """Researcher with CREATE_TEACHER sudo can create teachers."""

    admin = _mk_user(username="admin-ct-sudo", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-ct", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["CREATE_TEACHER"],
    )

    assert can_create_user(researcher, Role.TEACHER) is True
    assert can_create_user(researcher, Role.STUDENT) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_create_user_researcher_with_create_student_sudo():
    """Researcher with CREATE_STUDENT sudo can create students."""

    admin = _mk_user(username="admin-cs-sudo", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-cs", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["CREATE_STUDENT"],
    )

    assert can_create_user(researcher, Role.STUDENT) is True
    assert can_create_user(researcher, Role.TEACHER) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_teacher_owns_student_non_teacher_returns_false(admin_user):
    """Non-teacher user never owns a student."""

    researcher = _mk_user(username="researcher-own", role=Role.RESEARCHER)
    student = User.objects.create_user(
        username="student-own-r",
        email="student-own-r@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    assert teacher_owns_student(researcher, student) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_teacher_owns_student_non_student_returns_false():
    """Teacher checking ownership of non-student returns False."""

    teacher = _mk_user(username="teacher-own-ns", role=Role.TEACHER)
    researcher = _mk_user(username="researcher-target-ns", role=Role.RESEARCHER)

    assert teacher_owns_student(teacher, researcher) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_teacher_owns_student_missing_profile_returns_false(admin_user):
    """Student user without StudentProfile returns False."""

    teacher = _mk_user(username="teacher-own-mp", role=Role.TEACHER)
    student = User.objects.create_user(
        username="student-no-profile",
        email="student-no-profile@example.com",
        name="No Prof Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    # No StudentProfile created

    assert teacher_owns_student(teacher, student) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_edit_user_researcher_with_sudo(admin_user):
    """Researcher with EDIT_USER sudo can edit teachers and students."""

    admin = _mk_user(username="admin-edit-sudo", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-edit-sudo", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["EDIT_USER"],
    )

    teacher_target = _mk_user(username="teacher-edit-target", role=Role.TEACHER)
    assert can_edit_user(researcher, teacher_target, Role.TEACHER) is True

    student_target = User.objects.create_user(
        username="student-edit-target",
        email="student-edit-target@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student_target, role=Role.STUDENT)
    assert can_edit_user(researcher, student_target, Role.STUDENT) is True


@pytest.mark.django_db
@pytest.mark.unit
def test_can_edit_user_staff_target_always_false():
    """Staff/admin accounts cannot be edited through role flows."""

    admin = _mk_user(username="admin-edit-staff", role=Role.RESEARCHER, staff=True)
    target_admin = _mk_user(username="target-admin-edit", role=Role.RESEARCHER, staff=True)

    assert can_edit_user(admin, target_admin, Role.RESEARCHER) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_edit_user_invalid_role_returns_false():
    """Invalid requested role returns False."""

    admin = _mk_user(username="admin-edit-bad-role", role=Role.RESEARCHER, staff=True)
    teacher = _mk_user(username="teacher-edit-bad-role", role=Role.TEACHER)

    assert can_edit_user(admin, teacher, "NOT_A_ROLE") is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_edit_user_student_requester_returns_false(admin_user):
    """Student users cannot edit anyone."""

    student = User.objects.create_user(
        username="student-edit-req",
        email="student-edit-req@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    teacher = _mk_user(username="teacher-edit-unauth", role=Role.TEACHER)
    assert can_edit_user(student, teacher, Role.TEACHER) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_delete_user_researcher_with_sudo():
    """Researcher with DELETE_USER sudo can delete teachers and students."""

    admin = _mk_user(username="admin-del-sudo", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-del-sudo", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["DELETE_USER"],
    )

    teacher_target = _mk_user(username="teacher-del-target", role=Role.TEACHER)
    assert can_delete_user(researcher, teacher_target) is True


@pytest.mark.django_db
@pytest.mark.unit
def test_can_delete_user_admin_cannot_delete_student(admin_user):
    """Admin cannot delete student (only researchers and teachers)."""

    admin = _mk_user(username="admin-del-student", role=Role.RESEARCHER, staff=True)
    student = User.objects.create_user(
        username="student-del-target",
        email="student-del-target@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    assert can_delete_user(admin, student) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_delete_user_student_requester_returns_false(admin_user):
    """Student users cannot delete anyone."""

    student = User.objects.create_user(
        username="student-del-req",
        email="student-del-req@example.com",
        name="Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    teacher = _mk_user(username="teacher-del-unauth", role=Role.TEACHER)
    assert can_delete_user(student, teacher) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_can_grant_permissions_no_sudo_grant():
    """Researcher without any sudo grant cannot grant permissions."""

    researcher = _mk_user(username="researcher-no-grant", role=Role.RESEARCHER)

    allowed, message = _can_grant_permissions(researcher, ["CREATE_STUDENT"], False)
    assert allowed is False
    assert "does not have sudo" in message


@pytest.mark.django_db
@pytest.mark.unit
def test_can_grant_permissions_cannot_grant_sudo_flag():
    """Researcher cannot enable can_grant_sudo (admin only)."""

    admin = _mk_user(username="admin-cgs", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-cgs", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["CREATE_STUDENT"],
        can_grant_sudo=True,
    )

    allowed, message = _can_grant_permissions(researcher, ["CREATE_STUDENT"], True)
    assert allowed is False
    assert "Only admins" in message


@pytest.mark.django_db
@pytest.mark.unit
def test_can_grant_permissions_non_delegable_researcher_code_permission():
    """Researchers cannot delegate ISSUE_RESEARCHER_REG_CODE even if they hold it."""

    admin = _mk_user(username="admin-nd", role=Role.RESEARCHER, staff=True)
    researcher = _mk_user(username="researcher-nd", role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=["ISSUE_RESEARCHER_REG_CODE"],
        can_grant_sudo=True,
    )

    allowed, message = _can_grant_permissions(researcher, ["ISSUE_RESEARCHER_REG_CODE"], False)
    assert allowed is False
    assert "non-delegable" in message
