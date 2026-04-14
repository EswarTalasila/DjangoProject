"""Management command to seed a fuller demo dataset for local testing."""

from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.management.commands.provision_account import COURSE_NAME, CREDENTIALS
from accounts.models import StudentProfile, User
from assignment_templates.models import (
    AssignmentTemplate,
    AssignmentTemplateStatus,
    GradingMode,
    GradingStrategy,
    QuestionKind,
    ScoringPolicy,
    SubmissionMode,
)
from assignment_templates.services import (
    archive_assignment_template,
    create_assignment_template,
    create_assignment_template_draft,
    update_assignment_template,
)
from assignments.models import Assignment
from assignments.services._mutations import create_assignment
from config.env import env
from courses.models import Course, Enrollment, EnrollmentStatus
from courses.services import create_course
from courses.services._mutations import _create_submissions_for_student, create_student_in_course
from rubrics.models import Rubric
from rubrics.services import create_rubric
from submissions.models import (
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

SEED_SECONDARY_COURSE = "Seed Behavior Lab"

SEED_RUBRIC_TITLES = (
    "Seed Holistic Reflection Rubric",
    "Seed Participation Rubric",
)

SEED_ASSIGNMENT_TEMPLATE_TITLES = (
    "Seed Screening Survey",
    "Seed Writing Reflection",
    "Seed Grouped Behavior Review",
    "Seed Intake Packet Draft",
    "Seed Retired Check-In",
)

SEED_ASSIGNMENT_TITLES = (
    "Seed Screening Survey - Period 1",
    "Seed Writing Reflection - Period 1",
    "Seed Grouped Behavior Review - Lab",
)

EXTRA_STUDENTS = (
    {"name": "Jordan Lee", "consent": True},
    {"name": "Taylor Chen", "consent": True},
)


class Command(BaseCommand):
    """Seed a fuller deterministic demo dataset for local development/testing."""

    help = (
        "Provision deterministic accounts and seed demo rubrics, assignment templates, "
        "assignments, courses, and submissions."
    )

    def handle(self, *args, **options):
        if env.is_production:
            raise CommandError("seed_demo_data is blocked in production.")

        call_command("ensure_admin")
        call_command("provision_account", role="all", force_password=True)

        researcher = self._get_non_student_user("researcher")
        teacher = self._get_non_student_user("teacher")
        base_student = self._get_student_user()

        with transaction.atomic():
            self._clear_seed_domain_data()

            primary_course = self._ensure_course(teacher, COURSE_NAME)
            secondary_course = self._ensure_course(teacher, SEED_SECONDARY_COURSE)

            jordan = self._ensure_student_in_course(teacher, primary_course, EXTRA_STUDENTS[0])
            taylor = self._ensure_student_in_course(teacher, primary_course, EXTRA_STUDENTS[1])
            self._ensure_student_enrolled(primary_course, base_student)

            self._ensure_student_enrolled(secondary_course, base_student)
            self._ensure_student_enrolled(secondary_course, jordan)

            holistic_rubric = self._ensure_rubric(
                researcher,
                title="Seed Holistic Reflection Rubric",
                description="Assignment-template-wide manual grading rubric for writing-based demos.",
                criteria=[
                    {
                        "title": "Insight",
                        "description": "Quality and depth of the response.",
                        "weight": 1.0,
                        "levels": [
                            {"label": "Beginning", "points": 1, "description": "Limited detail."},
                            {"label": "Developing", "points": 2, "description": "Some relevant detail."},
                            {"label": "Strong", "points": 3, "description": "Clear, specific reasoning."},
                        ],
                    },
                    {
                        "title": "Communication",
                        "description": "Organization and clarity of the response.",
                        "weight": 1.0,
                        "levels": [
                            {"label": "Needs Support", "points": 1, "description": "Hard to follow."},
                            {"label": "Adequate", "points": 2, "description": "Mostly clear."},
                            {"label": "Polished", "points": 3, "description": "Clear and well-structured."},
                        ],
                    },
                ],
            )
            participation_rubric = self._ensure_rubric(
                researcher,
                title="Seed Participation Rubric",
                description="Question-group rubric for qualitative classroom participation notes.",
                criteria=[
                    {
                        "title": "Participation",
                        "description": "Observed level of engagement.",
                        "weight": 1.0,
                        "levels": [
                            {"label": "Low", "points": 1, "description": "Rarely engaged."},
                            {"label": "Moderate", "points": 2, "description": "Intermittently engaged."},
                            {"label": "High", "points": 3, "description": "Consistently engaged."},
                        ],
                    }
                ],
            )

            screening_assignment_template = create_assignment_template(
                researcher,
                {
                    "title": "Seed Screening Survey",
                    "category": "Screening",
                    "gradingMode": GradingMode.AUTO,
                    "scoringPolicy": ScoringPolicy.STANDARD,
                    "questions": [
                        {
                            "type": QuestionKind.MULTIPLE_CHOICE,
                            "prompt": "How often has the student been ready to learn this week?",
                            "maxPoints": 2,
                            "data": {
                                "choices": [
                                    {"prompt": "Rarely", "score": 0},
                                    {"prompt": "Sometimes", "score": 1},
                                    {"prompt": "Usually", "score": 2},
                                ],
                                "selectAll": False,
                            },
                        },
                        {
                            "type": QuestionKind.NUMBER_SCALE,
                            "prompt": "Rate the student’s energy level today.",
                            "maxPoints": 5,
                            "data": {"min": 1, "max": 5, "target": 4},
                        },
                        {
                            "type": QuestionKind.MULTIPLE_CHOICE,
                            "prompt": "Which classroom supports helped most?",
                            "maxPoints": 2,
                            "data": {
                                "choices": [
                                    {"prompt": "Visual schedule", "score": 1},
                                    {"prompt": "Check-in prompt", "score": 1},
                                    {"prompt": "Break card", "score": 1},
                                ],
                                "selectAll": True,
                            },
                        },
                    ],
                },
            )

            writing_assignment_template = create_assignment_template(
                researcher,
                {
                    "title": "Seed Writing Reflection",
                    "category": "Reflection",
                    "gradingMode": GradingMode.MANUAL,
                    "scoringPolicy": ScoringPolicy.STANDARD,
                    "rubricId": holistic_rubric.id,
                    "questions": [
                        {
                            "type": QuestionKind.SHORT_ANSWER,
                            "prompt": "Describe a strategy that helped the student stay focused.",
                            "maxPoints": 6,
                            "gradingStrategy": GradingStrategy.MANUAL,
                            "data": {"caseSensitive": False, "trim": True},
                        },
                        {
                            "type": QuestionKind.SHORT_ANSWER,
                            "prompt": "What follow-up support would you recommend next?",
                            "maxPoints": 6,
                            "gradingStrategy": GradingStrategy.MANUAL,
                            "data": {"caseSensitive": False, "trim": True},
                        },
                    ],
                },
            )

            grouped_assignment_template = create_assignment_template(
                researcher,
                {
                    "title": "Seed Grouped Behavior Review",
                    "category": "Observation",
                    "gradingMode": GradingMode.HYBRID,
                    "scoringPolicy": ScoringPolicy.STANDARD,
                    "questionGroups": [
                        {
                            "clientKey": "observation",
                            "name": "Observation Notes",
                            "rubricId": participation_rubric.id,
                        }
                    ],
                    "questions": [
                        {
                            "type": QuestionKind.SHORT_ANSWER,
                            "prompt": "Describe the student’s participation during independent work.",
                            "maxPoints": 4,
                            "groupClientKey": "observation",
                            "gradingStrategy": GradingStrategy.MANUAL,
                            "data": {"caseSensitive": False, "trim": True},
                        },
                        {
                            "type": QuestionKind.NUMBER_SCALE,
                            "prompt": "Rate on-task behavior from 1 to 5.",
                            "maxPoints": 5,
                            "gradingStrategy": GradingStrategy.AUTO,
                            "data": {"min": 1, "max": 5, "target": 4},
                        },
                    ],
                },
            )

            draft_assignment_template = create_assignment_template_draft(researcher)
            update_assignment_template(
                draft_assignment_template,
                {
                    "title": "Seed Intake Packet Draft",
                    "category": "Intake",
                    "gradingMode": GradingMode.MANUAL,
                    "scoringPolicy": ScoringPolicy.STANDARD,
                    "submissionMode": SubmissionMode.UPLOAD_ONLY,
                    "questions": [
                        {
                            "type": QuestionKind.MOOD_METER,
                            "prompt": "Select the mood shown in the student check-in.",
                            "maxPoints": 1,
                            "gradingStrategy": GradingStrategy.MANUAL,
                            "data": {},
                        },
                        {
                            "type": QuestionKind.SHORT_ANSWER,
                            "prompt": "Add any intake notes for later review.",
                            "maxPoints": 2,
                            "gradingStrategy": GradingStrategy.MANUAL,
                            "data": {"caseSensitive": False, "trim": True},
                        },
                    ],
                },
            )

            archived_assignment_template = create_assignment_template(
                researcher,
                {
                    "title": "Seed Retired Check-In",
                    "category": "Archive Demo",
                    "gradingMode": GradingMode.AUTO,
                    "scoringPolicy": ScoringPolicy.COMPLETION,
                    "questions": [
                        {
                            "type": QuestionKind.MULTIPLE_CHOICE,
                            "prompt": "Did the student complete the warm-up routine?",
                            "maxPoints": 1,
                            "data": {
                                "choices": [
                                    {"prompt": "No", "score": 0},
                                    {"prompt": "Yes", "score": 1},
                                ],
                                "selectAll": False,
                            },
                        }
                    ],
                },
            )
            archive_assignment_template(researcher, archived_assignment_template)

            screening_assignment = create_assignment(
                teacher,
                {
                    "title": "Seed Screening Survey - Period 1",
                    "assignmentTemplateId": screening_assignment_template.id,
                    "audienceType": "COURSE",
                    "courseId": primary_course.id,
                    "openAt": timezone.now() - timedelta(days=3),
                    "dueAt": timezone.now() + timedelta(days=4),
                },
            )
            writing_assignment = create_assignment(
                teacher,
                {
                    "title": "Seed Writing Reflection - Period 1",
                    "assignmentTemplateId": writing_assignment_template.id,
                    "audienceType": "COURSE",
                    "courseId": primary_course.id,
                    "openAt": timezone.now() - timedelta(days=1),
                    "dueAt": timezone.now() + timedelta(days=5),
                },
            )
            grouped_assignment = create_assignment(
                teacher,
                {
                    "title": "Seed Grouped Behavior Review - Lab",
                    "assignmentTemplateId": grouped_assignment_template.id,
                    "audienceType": "COURSE",
                    "courseId": secondary_course.id,
                    "openAt": timezone.now() - timedelta(days=2),
                    "dueAt": timezone.now() + timedelta(days=7),
                },
            )

            self._mark_submission_state(
                assignment=screening_assignment,
                student=base_student,
                status=SubmissionStatus.GRADED,
                short_answer_text="The student responded well to a structured visual schedule.",
            )
            self._mark_submission_state(
                assignment=screening_assignment,
                student=jordan,
                status=SubmissionStatus.SUBMITTED,
                short_answer_text="Break cards and movement prompts helped.",
            )
            self._mark_submission_state(
                assignment=screening_assignment,
                student=taylor,
                status=SubmissionStatus.IN_PROGRESS,
                short_answer_text="Teacher has partial notes in progress.",
            )
            self._mark_submission_state(
                assignment=grouped_assignment,
                student=base_student,
                status=SubmissionStatus.SUBMITTED,
                short_answer_text="Observed steady engagement after teacher redirection.",
            )

        self.stdout.write(self.style.SUCCESS("Demo seed completed"))
        self.stdout.write(
            "\n".join(
                [
                    "Seeded:",
                    f"  researcher: {researcher.username}",
                    f"  teacher:    {teacher.username}",
                    f"  student:    {base_student.username}",
                    f"  courses:    {Course.objects.filter(name__in=[COURSE_NAME, SEED_SECONDARY_COURSE]).count()}",
                    f"  rubrics:    {Rubric.objects.filter(title__in=SEED_RUBRIC_TITLES).count()}",
                    (
                        "  assignment_templates:"
                        f"{AssignmentTemplate.objects.filter(title__in=SEED_ASSIGNMENT_TEMPLATE_TITLES).count()}"
                    ),
                    f"  assignments:{Assignment.objects.filter(title__in=SEED_ASSIGNMENT_TITLES).count()}",
                    (
                        "  statuses:   draft="
                        f"{AssignmentTemplate.objects.filter(title='Seed Intake Packet Draft', status=AssignmentTemplateStatus.DRAFT).count()} "
                        f"active={AssignmentTemplate.objects.filter(title__in=SEED_ASSIGNMENT_TEMPLATE_TITLES, status=AssignmentTemplateStatus.ACTIVE).count()} "
                        f"archived={AssignmentTemplate.objects.filter(title='Seed Retired Check-In', status=AssignmentTemplateStatus.ARCHIVED).count()}"
                    ),
                ]
            )
        )

    def _get_non_student_user(self, role: str) -> User:
        creds = CREDENTIALS[role]
        user = User.objects.filter(email__iexact=creds["email"]).first()
        if not user:
            raise CommandError(f"Expected seeded {role} user not found.")
        return user

    def _get_student_user(self) -> User:
        creds = CREDENTIALS["student"]
        name = f"{creds['first_name']} {creds['last_name']}"
        user = User.objects.filter(name=name).first()
        if not user:
            raise CommandError("Expected seeded student user not found.")
        return user

    def _ensure_course(self, teacher: User, course_name: str) -> Course:
        course = Course.objects.filter(
            name=course_name,
            teacher_profile__user=teacher,
        ).first()
        if course:
            return course
        return create_course(teacher, course_name)

    def _ensure_student_in_course(self, teacher: User, course: Course, payload: dict) -> User:
        existing = User.objects.filter(name=payload["name"]).first()
        if existing:
            self._ensure_student_enrolled(course, existing)
            return existing

        enrollment = create_student_in_course(
            teacher,
            course.id,
            {
                "name": payload["name"],
                "password": "change-me",
                "consent": payload.get("consent", True),
            },
        )
        return enrollment.student_profile.user

    def _ensure_student_enrolled(self, course: Course, student_user: User) -> None:
        student_profile = StudentProfile.objects.filter(user=student_user).first()
        if not student_profile:
            raise CommandError(f"Student profile missing for user {student_user.username}")

        enrollment, created = Enrollment.objects.get_or_create(
            course=course,
            student_profile=student_profile,
            defaults={"status": EnrollmentStatus.ACTIVE},
        )
        if enrollment.status != EnrollmentStatus.ACTIVE:
            enrollment.status = EnrollmentStatus.ACTIVE
            enrollment.save(update_fields=["status"])
        if created:
            _create_submissions_for_student(student_user, course)

    def _ensure_rubric(
        self,
        researcher: User,
        *,
        title: str,
        description: str,
        criteria: list[dict],
    ) -> Rubric:
        return create_rubric(
            researcher,
            {"title": title, "description": description, "criteria": criteria},
        )

    def _clear_seed_domain_data(self) -> None:
        Assignment.objects.filter(title__in=SEED_ASSIGNMENT_TITLES).delete()
        AssignmentTemplate.objects.filter(title__in=SEED_ASSIGNMENT_TEMPLATE_TITLES).delete()
        Rubric.objects.filter(title__in=SEED_RUBRIC_TITLES).delete()
        Course.objects.filter(name=SEED_SECONDARY_COURSE).delete()

    def _mark_submission_state(
        self,
        *,
        assignment: Assignment,
        student: User,
        status: str,
        short_answer_text: str,
    ) -> None:
        submission = Submission.objects.filter(
            assignment=assignment,
            student=student,
        ).first()
        if not submission:
            raise CommandError(
                f"Expected submission for assignment '{assignment.title}' and student '{student.username}'"
            )

        normalized_status = status
        if (
            assignment.assignment_template.grading_mode == GradingMode.AUTO
            and status == SubmissionStatus.SUBMITTED
        ):
            normalized_status = SubmissionStatus.GRADED

        total_score = 0.0
        answered_any = False
        for index, answer in enumerate(submission.answers.select_related("question").all()):
            question = answer.question
            answer.skipped = False

            if normalized_status == SubmissionStatus.IN_PROGRESS and index > 0:
                answer.save(update_fields=["skipped"])
                continue

            if question.kind == QuestionKind.MULTIPLE_CHOICE:
                mc_answer, _ = MultipleChoiceAnswer.objects.get_or_create(answer=answer)
                MultipleChoiceSelected.objects.filter(answer=mc_answer).delete()
                choices = list(question.mcq_choices.all())
                if choices:
                    best_index = max(range(len(choices)), key=lambda idx: choices[idx].points)
                    MultipleChoiceSelected.objects.create(
                        answer=mc_answer,
                        choice_index=best_index,
                    )
                    if normalized_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED):
                        answer.score = float(choices[best_index].points)
                        total_score += answer.score
                    else:
                        answer.score = None
                answered_any = True
            elif question.kind == QuestionKind.SHORT_ANSWER:
                short_answer, _ = ShortAnswerAnswer.objects.get_or_create(
                    answer=answer,
                    defaults={"text": ""},
                )
                short_answer.text = short_answer_text
                short_answer.save(update_fields=["text"])
                if normalized_status == SubmissionStatus.GRADED:
                    answer.score = min(question.max_points, max(question.max_points - 1, 1))
                    total_score += float(answer.score or 0)
                else:
                    answer.score = None
                answered_any = True
            elif question.kind == QuestionKind.NUMBER_SCALE:
                number_answer, _ = NumberScaleAnswer.objects.get_or_create(
                    answer=answer,
                    defaults={"val": None},
                )
                scale = question.number_scale
                value = scale.target if scale.target is not None else scale.max
                number_answer.val = value
                number_answer.save(update_fields=["val"])
                if normalized_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED):
                    answer.score = float(question.max_points)
                    total_score += answer.score
                else:
                    answer.score = None
                answered_any = True

            answer.save(update_fields=["score", "skipped"])

        submission.status = normalized_status
        submission.submitted_at = (
            timezone.now() - timedelta(hours=4)
            if normalized_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED)
            else None
        )
        submission.score = (
            total_score
            if normalized_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED)
            else None
        )
        if not answered_any:
            submission.status = SubmissionStatus.NOT_STARTED
            submission.submitted_at = None
            submission.score = None
        submission.save(update_fields=["status", "submitted_at", "score"])
