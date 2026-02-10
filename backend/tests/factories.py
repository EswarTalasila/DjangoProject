"""Factory helpers for backend test data."""

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from accounts.models import Role, StudentProfile, SudoGrant, SudoPermission, TeacherProfile, User, UserRole
from assessments.models import (
    Assessment,
    GradingMode,
    McqChoice,
    MultipleChoiceQuestion,
    Question,
    QuestionKind,
)
from assignments.models import Assignment, AudienceType
from courses.models import Course, Enrollment, EnrollmentStatus


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    password = factory.LazyFunction(lambda: make_password("testpass123"))
    is_active = True


class UserRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRole

    user = factory.SubFactory(UserFactory)
    role = Role.STUDENT


class TeacherProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeacherProfile

    user = factory.SubFactory(UserFactory)


class StudentProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile

    user = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)
    consent = False


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    title = factory.Sequence(lambda n: f"Assessment {n}")
    grading_mode = GradingMode.AUTO
    created_by_admin = factory.SubFactory(UserFactory)
    category = "General"


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: f"Course {n}")
    teacher_profile = factory.SubFactory(TeacherProfileFactory)


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    course = factory.SubFactory(CourseFactory)
    student_profile = factory.SubFactory(StudentProfileFactory)
    status = EnrollmentStatus.ACTIVE


class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assignment

    assessment = factory.SubFactory(AssessmentFactory)
    audience_type = AudienceType.COURSE
    course = factory.SubFactory(CourseFactory)
    created_by = factory.SubFactory(UserFactory)
    open_at = factory.LazyFunction(timezone.now)
    due_at = None


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    assessment = factory.SubFactory(AssessmentFactory)
    question_type = QuestionKind.MULTIPLE_CHOICE
    kind = QuestionKind.MULTIPLE_CHOICE
    prompt = factory.Sequence(lambda n: f"Question {n}")
    max_points = 5.0
    auto_gradable = True
    graded = False


class MultipleChoiceQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MultipleChoiceQuestion

    question = factory.SubFactory(QuestionFactory)
    select_all = False


class McqChoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = McqChoice

    question = factory.SubFactory(QuestionFactory)
    choice_text = factory.Sequence(lambda n: f"Choice {n}")
    points = 1


class SudoGrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SudoGrant

    user = factory.SubFactory(UserFactory)
    granted_by = factory.SubFactory(UserFactory)
    permissions = []
    can_grant_sudo = False

    class Params:
        full_user_management = factory.Trait(
            permissions=[
                SudoPermission.CREATE_TEACHER.value,
                SudoPermission.CREATE_STUDENT.value,
                SudoPermission.EDIT_USER.value,
                SudoPermission.DELETE_USER.value,
            ]
        )
        with_grant_ability = factory.Trait(can_grant_sudo=True)
