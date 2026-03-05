"""Pure unit tests for assignment service queries and mutations (no database)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from assignments.models import AudienceType

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helper: neutralise @transaction.atomic which was applied at import time.
# Patch Atomic.__enter__ and __exit__ so the context manager becomes a no-op.
# ---------------------------------------------------------------------------

class _NoopAtomicMixin:
    """Mixin that patches transaction.Atomic so it never touches the database."""

    def setup_method(self):
        self._p_enter = patch(
            "django.db.transaction.Atomic.__enter__", return_value=None
        )
        self._p_exit = patch(
            "django.db.transaction.Atomic.__exit__", return_value=False
        )
        self._p_enter.start()
        self._p_exit.start()

    def teardown_method(self):
        self._p_exit.stop()
        self._p_enter.stop()


# ---------------------------------------------------------------------------
# assignment_to_dto
# ---------------------------------------------------------------------------


class TestAssignmentToDto:
    """Tests for assignment_to_dto conversion."""

    def test_converts_assignment_to_dto(self):
        """Converts Assignment to AssignmentDTO with all fields."""
        from assignments.services._queries import assignment_to_dto

        now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        assignment = SimpleNamespace(
            id=1,
            assessment_id=10,
            audience_type=AudienceType.COURSE,
            course_id=20,
            teacher_id=None,
            open_at=now,
            due_at=None,
        )

        dto = assignment_to_dto(assignment)

        assert dto.id == 1
        assert dto.assessmentId == 10
        assert dto.audienceType == AudienceType.COURSE
        assert dto.courseId == 20
        assert dto.targetTeacherId is None
        assert dto.openAt == now
        assert dto.dueAt is None

    def test_teacher_type_assignment(self):
        """Converts TEACHER-type assignment with teacher_id set."""
        from assignments.services._queries import assignment_to_dto

        now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        assignment = SimpleNamespace(
            id=2,
            assessment_id=11,
            audience_type=AudienceType.TEACHER,
            course_id=None,
            teacher_id=42,
            open_at=now,
            due_at=now,
        )

        dto = assignment_to_dto(assignment)

        assert dto.audienceType == AudienceType.TEACHER
        assert dto.courseId is None
        assert dto.targetTeacherId == 42


# ---------------------------------------------------------------------------
# get_assignment
# ---------------------------------------------------------------------------


class TestGetAssignment:
    """Tests for get_assignment query."""

    @patch("assignments.services._queries.Assignment")
    def test_returns_assignment_when_found(self, mock_assignment_model):
        """Returns assignment when it exists."""
        from assignments.services._queries import get_assignment

        sentinel = SimpleNamespace(id=5)
        mock_assignment_model.objects.filter.return_value.first.return_value = sentinel

        result = get_assignment(5)

        assert result is sentinel
        mock_assignment_model.objects.filter.assert_called_once_with(id=5)

    @patch("assignments.services._queries.Assignment")
    def test_returns_none_when_not_found(self, mock_assignment_model):
        """Returns None when assignment does not exist."""
        from assignments.services._queries import get_assignment

        mock_assignment_model.objects.filter.return_value.first.return_value = None

        assert get_assignment(999) is None


# ---------------------------------------------------------------------------
# list_by_course
# ---------------------------------------------------------------------------


class TestListByCourse:
    """Tests for list_by_course query."""

    @patch("assignments.services._queries.Assignment")
    def test_returns_assignments_for_course(self, mock_assignment_model):
        """Returns list of assignments for a specific course."""
        from assignments.services._queries import list_by_course

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_assignment_model.objects.filter.return_value = sentinel

        result = list_by_course(10)

        assert result == sentinel
        mock_assignment_model.objects.filter.assert_called_once_with(course_id=10)


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------


class TestListForUser:
    """Tests for list_for_user query."""

    @patch("assignments.services._queries.timezone")
    @patch("assignments.services._queries.Enrollment")
    @patch("assignments.services._queries.Assignment")
    @patch("assignments.services._queries.primary_role", return_value="STUDENT")
    def test_student_sees_enrolled_course_assignments(
        self, mock_role, mock_assignment_model, mock_enrollment_model, mock_tz
    ):
        """Student sees assignments from courses they are enrolled in."""
        from assignments.services._queries import list_for_user

        now = datetime(2025, 6, 1, tzinfo=UTC)
        mock_tz.now.return_value = now

        enrollment1 = SimpleNamespace(course_id=10)
        enrollment2 = SimpleNamespace(course_id=20)
        mock_enrollment_model.objects.filter.return_value = [
            enrollment1, enrollment2
        ]

        sentinel = [SimpleNamespace(id=1)]
        mock_qs = MagicMock()
        mock_assignment_model.objects.filter.return_value = mock_qs
        mock_qs.filter.return_value.order_by.return_value = sentinel

        user = SimpleNamespace(id=1, is_authenticated=True)

        result = list_for_user(user)

        assert result == sentinel
        mock_assignment_model.objects.filter.assert_called_once_with(
            course_id__in=[10, 20], open_at__lte=now
        )

    @patch("assignments.services._queries.timezone")
    @patch("assignments.services._queries.Assignment")
    @patch("assignments.services._queries.primary_role", return_value="TEACHER")
    def test_teacher_sees_self_assignments(
        self, mock_role, mock_assignment_model, mock_tz
    ):
        """Teacher sees assignments targeted at them."""
        from assignments.services._queries import list_for_user

        now = datetime(2025, 6, 1, tzinfo=UTC)
        mock_tz.now.return_value = now

        sentinel = [SimpleNamespace(id=2)]
        mock_qs = MagicMock()
        mock_assignment_model.objects.filter.return_value = mock_qs
        mock_qs.filter.return_value.order_by.return_value = sentinel

        user = SimpleNamespace(id=42, is_authenticated=True)

        result = list_for_user(user)

        assert result == sentinel
        mock_assignment_model.objects.filter.assert_called_once_with(
            teacher_id=42, open_at__lte=now
        )

    @patch("assignments.services._queries.primary_role", return_value="ADMIN")
    def test_non_student_non_teacher_returns_empty(self, mock_role):
        """Unknown role returns empty list."""
        from assignments.services._queries import list_for_user

        user = SimpleNamespace(id=1, is_authenticated=True)

        result = list_for_user(user)

        assert result == []


# ---------------------------------------------------------------------------
# create_assignment (mutation)
# ---------------------------------------------------------------------------


class TestCreateAssignment:
    """Tests for create_assignment mutation."""

    def test_raises_when_no_assessment_id(self):
        """Raises ValueError when assessmentId is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="assessmentId is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"audienceType": "COURSE", "openAt": "now"},
            )

    def test_raises_when_no_audience_type(self):
        """Raises ValueError when audienceType is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="audienceType is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"assessmentId": 1, "openAt": "now"},
            )

    def test_raises_when_no_open_at(self):
        """Raises ValueError when openAt is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="openAt is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"assessmentId": 1, "audienceType": "COURSE"},
            )

    def test_raises_when_course_type_missing_course_id(self):
        """Raises ValueError when COURSE type has no courseId."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="courseId must be set"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "assessmentId": 1,
                    "audienceType": AudienceType.COURSE,
                    "openAt": "2025-01-01",
                },
            )

    def test_raises_when_teacher_type_missing_teacher_id(self):
        """Raises ValueError when TEACHER type has no targetTeacherId."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="targetTeacherId must be set"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "assessmentId": 1,
                    "audienceType": AudienceType.TEACHER,
                    "openAt": "2025-01-01",
                },
            )

    @patch("assignments.services._mutations._create_submissions_for_course")
    @patch("assignments.services._mutations.Assignment")
    def test_creates_course_assignment_with_submissions(
        self, mock_assignment_model, mock_create_subs
    ):
        """Creates COURSE assignment and triggers submission creation."""
        from assignments.services._mutations import create_assignment

        fake_assignment = SimpleNamespace(id=1, course_id=10)
        mock_assignment_model.objects.create.return_value = fake_assignment

        user = SimpleNamespace(id=1)
        payload = {
            "assessmentId": 5,
            "audienceType": AudienceType.COURSE,
            "courseId": 10,
            "openAt": "2025-01-01",
            "dueAt": None,
        }

        result = create_assignment(user, payload)

        assert result is fake_assignment
        mock_create_subs.assert_called_once_with(fake_assignment)

    @patch("assignments.services._mutations._create_submissions_for_course")
    @patch("assignments.services._mutations.Assignment")
    def test_creates_teacher_assignment_no_submissions(
        self, mock_assignment_model, mock_create_subs
    ):
        """Creates TEACHER assignment without triggering submission creation."""
        from assignments.services._mutations import create_assignment

        fake_assignment = SimpleNamespace(id=2, course_id=None)
        mock_assignment_model.objects.create.return_value = fake_assignment

        user = SimpleNamespace(id=1)
        payload = {
            "assessmentId": 5,
            "audienceType": AudienceType.TEACHER,
            "targetTeacherId": 42,
            "openAt": "2025-01-01",
        }

        result = create_assignment(user, payload)

        assert result is fake_assignment
        mock_create_subs.assert_not_called()


# ---------------------------------------------------------------------------
# delete_assignment (mutation)
# ---------------------------------------------------------------------------


class TestDeleteAssignment(_NoopAtomicMixin):
    """Tests for delete_assignment mutation."""

    @patch("assignments.services._mutations.Submission")
    def test_deletes_submissions_then_assignment(
        self, mock_submission_model
    ):
        """Deletes all submissions before the assignment."""
        from assignments.services._mutations import delete_assignment

        assignment = MagicMock()

        delete_assignment(assignment)

        mock_submission_model.objects.filter.assert_called_once_with(
            assignment=assignment
        )
        mock_submission_model.objects.filter.return_value.delete.assert_called_once()
        assignment.delete.assert_called_once()


# ---------------------------------------------------------------------------
# _create_submissions_for_course (internal)
# ---------------------------------------------------------------------------


class TestCreateSubmissionsForCourse(_NoopAtomicMixin):
    """Tests for _create_submissions_for_course internal helper."""

    @patch("assignments.services._mutations.Assessment")
    def test_skips_when_assessment_not_found(self, mock_assessment_model):
        """Skips when assessment does not exist."""
        from assignments.services._mutations import _create_submissions_for_course

        mock_assessment_model.objects.filter.return_value.first.return_value = None
        assignment = SimpleNamespace(assessment_id=999)

        # Should not raise
        _create_submissions_for_course(assignment)

    @patch("assignments.services._mutations.Assessment")
    def test_skips_mood_meter_assessments(self, mock_assessment_model):
        """Skips submission creation for MOOD_METER assessments."""
        from assessments.models import GradingMode
        from assignments.services._mutations import _create_submissions_for_course

        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(grading_mode=GradingMode.MOOD_METER)
        )
        assignment = SimpleNamespace(assessment_id=1)

        _create_submissions_for_course(assignment)

    @patch("assignments.services._mutations.Assessment")
    def test_skips_when_no_course_id(self, mock_assessment_model):
        """Skips when assignment has no course_id."""
        from assessments.models import GradingMode
        from assignments.services._mutations import _create_submissions_for_course

        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(grading_mode=GradingMode.AUTO)
        )
        assignment = SimpleNamespace(assessment_id=1, course_id=None)

        _create_submissions_for_course(assignment)

    @patch("assignments.services._mutations.NumberScaleAnswer")
    @patch("assignments.services._mutations.ShortAnswerAnswer")
    @patch("assignments.services._mutations.MultipleChoiceAnswer")
    @patch("assignments.services._mutations.Answer")
    @patch("assignments.services._mutations.Submission")
    @patch("assignments.services._mutations.Enrollment")
    @patch("assignments.services._mutations.Assessment")
    @patch("assignments.services._mutations.answer_type_from_question")
    def test_creates_submissions_for_enrolled_students(
        self,
        mock_answer_type,
        mock_assessment_model,
        mock_enrollment_model,
        mock_submission_model,
        mock_answer_model,
        mock_mca,
        mock_saa,
        mock_nsa,
    ):
        """Creates submissions with answers for each enrolled student."""
        from assessments.models import GradingMode, QuestionKind
        from assignments.services._mutations import _create_submissions_for_course

        mc_question = SimpleNamespace(kind=QuestionKind.MULTIPLE_CHOICE)
        sa_question = SimpleNamespace(kind=QuestionKind.SHORT_ANSWER)
        ns_question = SimpleNamespace(kind=QuestionKind.NUMBER_SCALE)

        fake_assessment = MagicMock()
        fake_assessment.grading_mode = GradingMode.AUTO
        fake_assessment.questions.all.return_value = [
            mc_question, sa_question, ns_question
        ]
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            fake_assessment
        )
        mock_enrollment_model.objects.filter.return_value.values_list.return_value = [
            100, 200
        ]
        mock_submission_model.objects.filter.return_value.exists.return_value = False
        fake_submission = SimpleNamespace(id=1)
        mock_submission_model.objects.create.return_value = fake_submission
        mock_answer_type.return_value = "MC"
        fake_answer = SimpleNamespace(id=10)
        mock_answer_model.objects.create.return_value = fake_answer

        assignment = SimpleNamespace(id=1, assessment_id=5, course_id=10)

        _create_submissions_for_course(assignment)

        # 2 students, each gets 1 submission
        assert mock_submission_model.objects.create.call_count == 2
        # 2 students x 3 questions = 6 answers
        assert mock_answer_model.objects.create.call_count == 6

    @patch("assignments.services._mutations.Submission")
    @patch("assignments.services._mutations.Enrollment")
    @patch("assignments.services._mutations.Assessment")
    def test_skips_existing_submissions(
        self,
        mock_assessment_model,
        mock_enrollment_model,
        mock_submission_model,
    ):
        """Skips submission creation when submission already exists for student."""
        from assessments.models import GradingMode
        from assignments.services._mutations import _create_submissions_for_course

        fake_assessment = MagicMock()
        fake_assessment.grading_mode = GradingMode.AUTO
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            fake_assessment
        )
        mock_enrollment_model.objects.filter.return_value.values_list.return_value = [100]
        mock_submission_model.objects.filter.return_value.exists.return_value = True

        assignment = SimpleNamespace(id=1, assessment_id=5, course_id=10)

        _create_submissions_for_course(assignment)

        mock_submission_model.objects.create.assert_not_called()
