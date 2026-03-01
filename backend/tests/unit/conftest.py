"""Unit-test scoped fixtures for FR1/FR2 domains."""

import pytest

from accounts.models import (
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoPermission,
    TeacherProfile,
    UserRole,
)
from courses.models import Course, Enrollment, EnrollmentStatus
from tests.factories import SudoGrantFactory, UserFactory


@pytest.fixture
def teacher_with_course():
    """Teacher user with one owned course."""
    teacher = UserFactory(username="teacher_with_course")
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    teacher_profile = TeacherProfile.objects.create(user=teacher)
    course = Course.objects.create(name="Unit Course", teacher_profile=teacher_profile)
    return teacher, course


@pytest.fixture
def student_enrolled(teacher_with_course):
    """Student user actively enrolled in teacher_with_course fixture course."""
    teacher, course = teacher_with_course
    student = UserFactory(username="student_enrolled")
    UserRole.objects.create(user=student, role=Role.STUDENT)
    student_profile = StudentProfile.objects.create(user=student, created_by=teacher, consent=False)
    Enrollment.objects.create(
        course=course,
        student_profile=student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    return teacher, course, student


@pytest.fixture
def researcher_with_sudo():
    """Researcher with broad sudo permissions for authorization unit tests."""
    admin = UserFactory(username="sudo_admin")
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    researcher = UserFactory(username="sudo_researcher")
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
    ResearcherProfile.objects.create(user=researcher)

    grant = SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=[
            SudoPermission.CREATE_TEACHER.value,
            SudoPermission.CREATE_STUDENT.value,
            SudoPermission.EDIT_USER.value,
            SudoPermission.DELETE_USER.value,
            SudoPermission.ISSUE_STUDENT_RESET_CODE.value,
            SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value,
            SudoPermission.ISSUE_RESEARCHER_REG_CODE.value,
        ],
        can_grant_sudo=True,
    )
    return researcher, grant
