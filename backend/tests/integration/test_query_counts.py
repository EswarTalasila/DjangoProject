"""Query-count regression tests for N+1 fixes.

These tests verify that DTO serialization paths maintain a constant query count
regardless of how many child objects exist (answers, questions, criteria, etc.).
Uses Django's CaptureQueriesContext to measure actual DB round-trips.
"""

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from accounts.models import Role, StudentProfile, TeacherProfile, UserRole
from assessments.models import (
    Assessment,
    GradingMode,
    McqChoice,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    QuestionKind,
    ShortAnswerQuestion,
    ScoringPolicy,
)
from assignments.models import Assignment, AudienceType
from courses.models import Course, Enrollment, EnrollmentStatus
from rubrics.models import Rubric, RubricCriterion, RubricLevel
from submissions.models import (
    Answer,
    AnswerType,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)
from tests.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# ── Helpers ──────────────────────────────────────────────────────────────


def _create_teacher_and_course():
    teacher = UserFactory()
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    tp = TeacherProfile.objects.create(user=teacher)
    course = Course.objects.create(name="Query Test Course", teacher_profile=tp)
    return teacher, course


def _create_assessment_with_questions(admin, n_mcq=2, n_sa=1, n_ns=1):
    """Create an assessment with a mix of question types."""
    assessment = Assessment.objects.create(
        title="Query Test Assessment",
        grading_mode=GradingMode.AUTO,
        scoring_policy=ScoringPolicy.STANDARD,
        created_by_admin=admin,
    )
    questions = []
    for i in range(n_mcq):
        q = Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.MULTIPLE_CHOICE,
            kind=QuestionKind.MULTIPLE_CHOICE,
            prompt=f"MCQ {i}",
            max_points=5.0,
            auto_gradable=True,
            graded=False,
        )
        MultipleChoiceQuestion.objects.create(question=q, select_all=False)
        for j in range(3):
            McqChoice.objects.create(question=q, choice_text=f"Choice {j}", points=j)
        questions.append(q)
    for i in range(n_sa):
        q = Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt=f"SA {i}",
            max_points=10.0,
            auto_gradable=False,
            graded=False,
        )
        ShortAnswerQuestion.objects.create(question=q, case_sensitive=False, trim=True)
        questions.append(q)
    for i in range(n_ns):
        q = Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.NUMBER_SCALE,
            kind=QuestionKind.NUMBER_SCALE,
            prompt=f"NS {i}",
            max_points=5.0,
            auto_gradable=True,
            graded=False,
        )
        NumberScaleQuestion.objects.create(question=q, min=1, max=10, target=5)
        questions.append(q)
    return assessment, questions


def _create_submission_with_answers(assignment, student, questions):
    """Create a submission with one answer per question, including sub-types."""
    sub = Submission.objects.create(
        assignment=assignment,
        student=student,
        status=SubmissionStatus.SUBMITTED,
    )
    for q in questions:
        if q.kind == QuestionKind.MULTIPLE_CHOICE:
            ans = Answer.objects.create(
                submission=sub,
                question=q,
                answer_type=AnswerType.MULTIPLE_CHOICE,
            )
            mc = MultipleChoiceAnswer.objects.create(answer=ans)
            MultipleChoiceSelected.objects.create(answer=mc, choice_index=0)
            MultipleChoiceSelected.objects.create(answer=mc, choice_index=1)
        elif q.kind == QuestionKind.SHORT_ANSWER:
            ans = Answer.objects.create(
                submission=sub,
                question=q,
                answer_type=AnswerType.SHORT_ANSWER,
            )
            ShortAnswerAnswer.objects.create(answer=ans, text="answer text")
        elif q.kind == QuestionKind.NUMBER_SCALE:
            ans = Answer.objects.create(
                submission=sub,
                question=q,
                answer_type=AnswerType.NUMBER_SCALE,
            )
            NumberScaleAnswer.objects.create(answer=ans, val=5)
    return sub


def _create_rubric_with_criteria(admin, n_criteria=3, n_levels=4):
    """Create a rubric with N criteria, each having M levels."""
    rubric = Rubric.objects.create(title="Query Test Rubric", created_by=admin)
    for i in range(n_criteria):
        crit = RubricCriterion.objects.create(
            rubric=rubric, title=f"Criterion {i}", order_index=i, weight=1.0,
        )
        for j in range(n_levels):
            RubricLevel.objects.create(
                criterion=crit, label=f"Level {j}", points=float(j),
                order_index=j,
            )
    return rubric


# ── Submission DTO query-count test ──────────────────────────────────────


class TestSubmissionDtoQueryCount:
    """Verify submission DTO generation query count is constant."""

    def test_submission_dto_constant_queries(self, admin_user):
        """submission_to_dto query count does not scale with answer count."""
        from submissions.services import get_submission_for_dto, submission_to_dto

        teacher, course = _create_teacher_and_course()
        assessment, questions = _create_assessment_with_questions(
            admin_user, n_mcq=3, n_sa=2, n_ns=2,
        )
        assignment = Assignment.objects.create(
            assessment=assessment, audience_type=AudienceType.COURSE,
            course=course, created_by=teacher, open_at="2025-01-01T00:00:00Z",
        )
        student = UserFactory()
        UserRole.objects.create(user=student, role=Role.STUDENT)
        StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

        sub = _create_submission_with_answers(assignment, student, questions)

        # Warm up Django's internal caches
        get_submission_for_dto(sub.id)

        with CaptureQueriesContext(connection) as ctx:
            s = get_submission_for_dto(sub.id)
            submission_to_dto(s)

        # One query to fetch submission + 4 prefetch queries
        # (answers, mc_answers+selected, short_answers, number_scale_answers).
        # The exact count may vary slightly, but should NOT scale with N.
        assert len(ctx.captured_queries) <= 8, (
            f"Expected <= 8 queries for submission DTO, got {len(ctx.captured_queries)}:\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )


# ── Assessment DTO query-count test ──────────────────────────────────────


class TestAssessmentDtoQueryCount:
    """Verify assessment DTO generation query count is constant."""

    def test_assessment_dto_constant_queries(self, admin_user):
        """assessment_to_dto query count does not scale with question count."""
        from assessments.services import _assessment_with_related, assessment_to_dto

        assessment, _ = _create_assessment_with_questions(
            admin_user, n_mcq=5, n_sa=3, n_ns=2,
        )

        # Warm up
        _assessment_with_related(assessment.id)

        with CaptureQueriesContext(connection) as ctx:
            a = _assessment_with_related(assessment.id)
            assessment_to_dto(a)

        # 1 assessment query + 5 prefetch queries (groups, questions,
        # mcq_choices, multiple_choice, short_answer, number_scale).
        assert len(ctx.captured_queries) <= 8, (
            f"Expected <= 8 queries for assessment DTO, got {len(ctx.captured_queries)}:\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )


# ── Rubric DTO query-count test ──────────────────────────────────────────


class TestRubricDtoQueryCount:
    """Verify rubric DTO generation query count is constant."""

    def test_rubric_dto_constant_queries(self, admin_user):
        """rubric_to_dto query count does not scale with criteria/level count."""
        from rubrics.services import _rubric_with_related, rubric_to_dto

        rubric = _create_rubric_with_criteria(admin_user, n_criteria=5, n_levels=4)

        # Warm up
        _rubric_with_related(rubric.id)

        with CaptureQueriesContext(connection) as ctx:
            r = _rubric_with_related(rubric.id)
            rubric_to_dto(r)

        # 1 rubric query + 2 prefetch queries (criteria, levels).
        assert len(ctx.captured_queries) <= 4, (
            f"Expected <= 4 queries for rubric DTO, got {len(ctx.captured_queries)}:\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )


# ── Course DTO query-count test ──────────────────────────────────────────


class TestCourseDtoQueryCount:
    """Verify course DTO generation does not N+1 on enrollments."""

    def test_course_dto_constant_queries(self, admin_user):
        """course_to_dto query count does not scale with enrollment count."""
        from courses.services._queries import course_to_dto

        teacher, course = _create_teacher_and_course()

        for i in range(5):
            student = UserFactory(username=f"qc_student_{i}@example.com")
            UserRole.objects.create(user=student, role=Role.STUDENT)
            sp = StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)
            Enrollment.objects.create(
                course=course, student_profile=sp, status=EnrollmentStatus.ACTIVE,
            )

        # Warm up
        course_to_dto(course)

        with CaptureQueriesContext(connection) as ctx:
            course_to_dto(course)

        # 1 enrollment query (with select_related) + 1 assignment query.
        assert len(ctx.captured_queries) <= 4, (
            f"Expected <= 4 queries for course DTO, got {len(ctx.captured_queries)}:\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )


# ── Export with answers query-count test ───────────────────────────────────


class TestExportAnswersQueryCount:
    """Verify export answer serialization query count is constant."""

    def test_export_answers_constant_queries(self, admin_user):
        """_serialize_answers query count does not scale with answer count per submission."""
        from exports.services import export_course_submissions

        teacher, course = _create_teacher_and_course()
        assessment, questions = _create_assessment_with_questions(
            admin_user, n_mcq=3, n_sa=2, n_ns=2,
        )
        assignment = Assignment.objects.create(
            assessment=assessment, audience_type=AudienceType.COURSE,
            course=course, created_by=teacher, open_at="2025-01-01T00:00:00Z",
        )
        # Create multiple students with submissions
        for i in range(3):
            student = UserFactory(username=f"exp_student_{i}@example.com")
            UserRole.objects.create(user=student, role=Role.STUDENT)
            sp = StudentProfile.objects.create(
                user=student, created_by=admin_user, consent=False,
            )
            Enrollment.objects.create(
                course=course, student_profile=sp, status=EnrollmentStatus.ACTIVE,
            )
            _create_submission_with_answers(assignment, student, questions)

        # Warm up
        gen, _, _ = export_course_submissions(
            admin_user, course, include_answers=True, identifiable=True,
        )
        list(gen)  # consume generator

        with CaptureQueriesContext(connection) as ctx:
            gen, _, _ = export_course_submissions(
                admin_user, course, include_answers=True, identifiable=True,
            )
            list(gen)  # consume the generator to trigger queries

        # Should be constant: 1 count + 1 audit + 1 submissions + ~5 prefetches.
        # Without the fix, this would be 1 + N*M queries (N submissions * M answers).
        assert len(ctx.captured_queries) <= 12, (
            f"Expected <= 12 queries for export with answers, got {len(ctx.captured_queries)}:\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
