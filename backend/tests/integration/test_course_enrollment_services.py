"""FR2-scoped unit tests for course enrollment service behavior."""

from __future__ import annotations

import pytest

from accounts.models import Role, TeacherProfile, User, UserRole
from courses.models import Course, Enrollment
from courses.services import create_student_in_course


@pytest.mark.django_db
@pytest.mark.integration
def test_create_student_in_course_requires_course_id(teacher_user):
    """Missing courseId is rejected early in student creation flow."""

    with pytest.raises(TypeError):
        create_student_in_course(teacher_user, {"name": "Student"})


@pytest.mark.django_db
@pytest.mark.integration
def test_create_student_in_course_rejects_client_username_override(teacher_user):
    """Client-supplied username is rejected; usernames are system-managed."""

    course = Course.objects.create(name="Course A", teacher_profile=teacher_user.teacher_profile)

    with pytest.raises(ValueError, match="system-managed"):
        create_student_in_course(
            teacher_user,
            course.id,
            {
                "name": "Dup Student",
                "username": "dup-student",
            },
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_create_student_in_course_raises_when_profile_missing(monkeypatch, teacher_user):
    """Profile-missing branch returns domain error when student profile absent."""

    from courses.models import Course

    course = Course.objects.create(name="Course B", teacher_profile=teacher_user.teacher_profile)

    phantom = User.objects.create_user(
        username="phantom-student",
        email="phantom-student@example.com",
        name="Phantom",
        password="StartPass123!",
    )
    UserRole.objects.create(user=phantom, role=Role.STUDENT)
    monkeypatch.setattr(
        "courses.services._mutations.create_user_from_payload", lambda *_a, **_k: phantom
    )

    with pytest.raises(ValueError, match="StudentProfile not created"):
        create_student_in_course(
            teacher_user,
            course.id,
            {
                "name": "Phantom",
            },
        )



@pytest.mark.django_db
@pytest.mark.integration
def test_create_student_in_course_creates_profile_and_enrollment(teacher_user):
    """Happy path creates new student account and active enrollment."""

    from courses.models import Course

    course = Course.objects.create(name="Course C", teacher_profile=teacher_user.teacher_profile)
    enrollment = create_student_in_course(
        teacher_user,
        course.id,
        {
            "name": "New Student",
            "consent": True,
        },
    )

    assert Enrollment.objects.filter(id=enrollment.id).exists()
    username = enrollment.student_profile.user.username
    assert len(username) == 8
    assert username[-1].isdigit()
    assert enrollment.student_profile.consent is True


# --- Branch-coverage additions ---


@pytest.mark.django_db
@pytest.mark.integration
def test_course_owner_null_teacher_profile():
    """Course with no teacher_profile returns None owner."""

    from types import SimpleNamespace

    from courses.services import _course_owner

    mock_course = SimpleNamespace(teacher_profile=None)
    assert _course_owner(mock_course) is None


@pytest.mark.django_db
@pytest.mark.integration
def test_can_view_course_admin_and_researcher(teacher_user):
    """Admin and researcher can view any course."""

    from courses.services import can_view_course

    course = Course.objects.create(name="View Course", teacher_profile=teacher_user.teacher_profile)

    admin = User.objects.create_user(
        username="admin-view-course",
        email="admin-view@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    from accounts.models import ResearcherProfile

    researcher = User.objects.create_user(
        username="researcher-view-course",
        email="researcher-view@example.com",
        name="Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
    ResearcherProfile.objects.create(user=researcher)

    assert can_view_course(admin, course) is True
    assert can_view_course(researcher, course) is True


@pytest.mark.django_db
@pytest.mark.integration
def test_can_view_course_other_teacher_denied(teacher_user):
    """Other teacher cannot view another teacher's course."""

    from courses.services import can_view_course

    course = Course.objects.create(
        name="Private Course", teacher_profile=teacher_user.teacher_profile
    )

    other_teacher = User.objects.create_user(
        username="other-teacher-view",
        email="other-teacher-view@example.com",
        name="Other Teacher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=other_teacher)

    assert can_view_course(other_teacher, course) is False


@pytest.mark.django_db
@pytest.mark.integration
def test_list_courses_for_user_admin_and_researcher(teacher_user):
    """Admin and researcher see all courses."""

    from courses.services import list_courses_for_user

    Course.objects.create(name="List Course", teacher_profile=teacher_user.teacher_profile)

    admin = User.objects.create_user(
        username="admin-list-course",
        email="admin-list@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    from accounts.models import ResearcherProfile

    researcher = User.objects.create_user(
        username="researcher-list-course",
        email="researcher-list@example.com",
        name="Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
    ResearcherProfile.objects.create(user=researcher)

    assert len(list_courses_for_user(admin)) >= 1
    assert len(list_courses_for_user(researcher)) >= 1


@pytest.mark.django_db
@pytest.mark.integration
def test_remove_student_from_course_missing_profile(teacher_user):
    """Removing student with no profile raises ValueError."""

    from courses.services import remove_student_from_course

    course = Course.objects.create(
        name="Remove Course", teacher_profile=teacher_user.teacher_profile
    )

    with pytest.raises(ValueError, match="Student not found in course"):
        remove_student_from_course(course, 999999)


@pytest.mark.django_db
@pytest.mark.integration
def test_create_student_in_course_avoids_non_student_identifier_collisions(teacher_user):
    """Student username generation avoids collisions with existing non-student accounts."""

    course = Course.objects.create(
        name="Reject Course", teacher_profile=teacher_user.teacher_profile
    )
    other_teacher = User.objects.create_user(
        username="existing-non-student",
        email="existing-non-student@example.com",
        name="Non Student",
        password="StartPass123!",
    )
    UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=other_teacher)

    enrollment = create_student_in_course(
        teacher_user,
        course.id,
        {
            "name": "Non Student",
        },
    )
    assert enrollment.student_profile.user.username != other_teacher.username


@pytest.mark.django_db
@pytest.mark.integration
def test_create_submissions_for_student_with_assignments(teacher_user):
    """Enrollment triggers submission creation for existing course assignments."""

    from django.utils import timezone as tz

    from assessments.models import Assessment, GradingMode, Question, QuestionKind
    from assignments.models import Assignment, AudienceType
    from submissions.models import Answer, Submission

    course = Course.objects.create(name="Sub Course", teacher_profile=teacher_user.teacher_profile)

    assessment = Assessment.objects.create(
        title="Test Assessment",
        grading_mode=GradingMode.AUTO,
        created_by_admin=teacher_user,
        category="General",
    )
    assignment = Assignment.objects.create(
        assessment=assessment,
        audience_type=AudienceType.COURSE,
        course=course,
        created_by=teacher_user,
        open_at=tz.now(),
    )
    Question.objects.create(
        assessment=assessment,
        question_type=QuestionKind.MULTIPLE_CHOICE,
        kind=QuestionKind.MULTIPLE_CHOICE,
        prompt="MC Q",
        max_points=5.0,
        auto_gradable=True,
        graded=False,
    )
    Question.objects.create(
        assessment=assessment,
        question_type=QuestionKind.SHORT_ANSWER,
        kind=QuestionKind.SHORT_ANSWER,
        prompt="SA Q",
        max_points=5.0,
        auto_gradable=True,
        graded=False,
    )
    Question.objects.create(
        assessment=assessment,
        question_type=QuestionKind.NUMBER_SCALE,
        kind=QuestionKind.NUMBER_SCALE,
        prompt="NS Q",
        max_points=5.0,
        auto_gradable=True,
        graded=False,
    )

    enrollment = create_student_in_course(
        teacher_user,
        course.id,
        {
            "name": "Sub Student",
            "consent": True,
        },
    )

    student_user = enrollment.student_profile.user
    submission = Submission.objects.filter(student=student_user, assignment=assignment).first()
    assert submission is not None

    answers = Answer.objects.filter(submission=submission).order_by("question_id")
    assert answers.count() == 3


@pytest.mark.django_db
@pytest.mark.integration
def test_answer_type_from_question_mapping():
    """Answer type mapper returns correct types for all question kinds."""

    from types import SimpleNamespace

    from assessments.models import QuestionKind
    from core.helpers import answer_type_from_question
    from submissions.models import AnswerType

    assert (
        answer_type_from_question(SimpleNamespace(kind=QuestionKind.MULTIPLE_CHOICE))
        == AnswerType.MULTIPLE_CHOICE
    )
    assert (
        answer_type_from_question(SimpleNamespace(kind=QuestionKind.SHORT_ANSWER))
        == AnswerType.SHORT_ANSWER
    )
    assert (
        answer_type_from_question(SimpleNamespace(kind=QuestionKind.NUMBER_SCALE))
        == AnswerType.NUMBER_SCALE
    )
    assert answer_type_from_question(SimpleNamespace(kind="UNKNOWN")) == AnswerType.SHORT_ANSWER


@pytest.mark.django_db
@pytest.mark.integration
def test_can_manage_course_owner_only(teacher_user):
    """Only course owner can manage (edit/delete) a course."""

    from courses.services import can_manage_course

    course = Course.objects.create(
        name="Manage Course", teacher_profile=teacher_user.teacher_profile
    )

    assert can_manage_course(teacher_user, course) is True

    other_teacher = User.objects.create_user(
        username="other-teacher-manage",
        email="other-teacher-manage@example.com",
        name="Other Teacher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=other_teacher)

    assert can_manage_course(other_teacher, course) is False
