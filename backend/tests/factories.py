"""Factory helpers for backend test data."""

from datetime import timedelta
from typing import ClassVar

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from accounts.models import (
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
from assignment_templates.models import (
    AssignmentTemplate,
    GradingMode,
    McqChoice,
    MultipleChoiceQuestion,
    Question,
    QuestionKind,
    ScoringPolicy,
)
from assignments.models import (
    Assignment,
    AssignmentQuestion,
    AssignmentStatus,
    AudienceType,
)
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, AnswerType, Submission, SubmissionStatus


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}@example.com")
    email = factory.LazyAttribute(lambda obj: obj.username)
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


class ResearcherProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResearcherProfile

    user = factory.SubFactory(UserFactory)


class StudentProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile

    user = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)
    consent = False


class AssignmentTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssignmentTemplate

    title = factory.Sequence(lambda n: f"AssignmentTemplate {n}")
    grading_mode = GradingMode.AUTO
    scoring_policy = ScoringPolicy.STANDARD
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

    assignment_template = factory.SubFactory(AssignmentTemplateFactory)
    audience_type = AudienceType.COURSE
    course = factory.SubFactory(CourseFactory)
    created_by = factory.SubFactory(UserFactory)
    open_at = factory.LazyFunction(timezone.now)
    due_at = None
    status = AssignmentStatus.ACTIVE

    @factory.post_generation
    def snapshot_content(self, create, extracted, **kwargs):
        """Mirror template content into assignment-owned rows by default for integration tests."""
        if not create or extracted is False:
            return
        if self.questions.exists():
            return

        from assignments.services._content import snapshot_assignment_content

        snapshot_assignment_content(
            self,
            self.assignment_template,
            creator_user_id=self.created_by_id,
        )


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    assignment_template = factory.SubFactory(AssignmentTemplateFactory)
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
    permissions: ClassVar[list[str]] = []
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


class RegistrationCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistrationCode

    code_hash = factory.Sequence(lambda n: f"{n:064x}"[-64:])
    code_prefix = factory.Sequence(lambda n: f"REG{n:05d}")
    code_type = RegistrationCodeType.STUDENT
    created_by = factory.SubFactory(UserFactory)
    course = factory.LazyAttribute(
        lambda obj: CourseFactory() if obj.code_type == RegistrationCodeType.STUDENT else None
    )
    max_uses = 1
    times_used = 0
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    is_active = True
    metadata = None
    archived_at = None

    class Params:
        expired = factory.Trait(expires_at=factory.LazyFunction(lambda: timezone.now()))
        exhausted = factory.Trait(times_used=factory.SelfAttribute("max_uses"))
        revoked = factory.Trait(is_active=False)


class PasswordResetRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetRequest

    user = factory.SubFactory(UserFactory)
    identifier = factory.LazyAttribute(lambda obj: obj.user.username)
    requested_role = Role.TEACHER
    request_token_hash = factory.Sequence(lambda n: f"reqhash{n:012d}")
    status = PasswordResetRequestStatus.PENDING
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=30))
    reason = None
    reviewed_by = None
    reviewed_at = None


class PasswordResetCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetCode

    request = factory.SubFactory(PasswordResetRequestFactory)
    code_hash = factory.Sequence(lambda n: f"resethash{n:012d}")
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=30))
    used_at = None


class OAuthAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OAuthAccount

    user = factory.SubFactory(UserFactory)
    provider = OAuthProvider.GOOGLE
    subject = factory.Sequence(lambda n: f"google-sub-{n}")
    email = factory.Sequence(lambda n: f"oauth{n}@example.com")
    email_verified = True
    picture_url = None


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory)
    status = SubmissionStatus.NOT_STARTED
    score = None
    submitted_at = None


class AnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Answer

    submission = factory.SubFactory(SubmissionFactory)
    answer_type = AnswerType.SHORT_ANSWER
    score = None
    skipped = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Route test answers through assignment-owned questions even when callers pass template rows."""
        submission = kwargs.get("submission") or SubmissionFactory()
        kwargs["submission"] = submission
        question = kwargs.get("question")
        kwargs["question"] = _resolve_assignment_question(submission.assignment, question)
        return super()._create(model_class, *args, **kwargs)


def _resolve_assignment_question(assignment: Assignment, question=None) -> AssignmentQuestion:
    """Return an assignment-owned question compatible with the submission schema."""
    if isinstance(question, AssignmentQuestion):
        return question

    if question is None:
        assignment_question = assignment.questions.order_by("order_index", "id").first()
        if assignment_question is not None:
            return assignment_question
        source_question = QuestionFactory(assignment_template=assignment.assignment_template)
    else:
        source_question = question

    assignment_question = AssignmentQuestion.objects.filter(
        assignment=assignment,
        source_template_question=source_question,
    ).first()
    if assignment_question is not None:
        return assignment_question

    return AssignmentQuestion.objects.create(
        assignment=assignment,
        source_template_question=source_question,
        created_by=assignment.created_by,
        kind=source_question.kind,
        prompt=source_question.prompt,
        max_points=source_question.max_points,
        auto_gradable=source_question.auto_gradable,
        graded=source_question.graded,
        image=getattr(source_question, "image", None),
        image_asset=getattr(source_question, "image_asset", None),
        grading_strategy=getattr(source_question, "grading_strategy", "AUTO"),
        data=getattr(source_question, "data", {}) or {},
        order_index=getattr(source_question, "order_index", 0),
        origin="TEMPLATE",
        locked_from_source=True,
    )
