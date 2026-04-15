"""Domain integrity tests for Phase 1 bug fixes.

Tests cover:
  Bug 1 – Enrollment status leakage (dropped students bypass access control)
  Bug 2 – Submission answer ownership (question from wrong assignment_template accepted)
  Bug 3 – Answer type mismatch (answer type doesn't match question kind)
  Bug 4 – Placeholder submissions for inactive/archived entities
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from accounts.models import Role
from submissions.models import AnswerType, SubmissionStatus

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _patch_transaction_atomic(monkeypatch):
    """Prevent @transaction.atomic wrappers from touching a real DB connection."""
    monkeypatch.setattr("django.db.transaction.Atomic.__enter__", lambda self: None)
    monkeypatch.setattr(
        "django.db.transaction.Atomic.__exit__", lambda self, exc_type, exc, tb: False
    )
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, using=None: func())


# ---------------------------------------------------------------------------
# Bug 1: Enrollment status leakage
# ---------------------------------------------------------------------------


class TestEnrollmentStatusGating:
    """Dropped students must be denied access."""

    @patch("submissions.views.Enrollment")
    def test_dropped_student_denied_by_enrollment_check(self, mock_enrollment):
        """_student_enrolled_in_assignment returns False for DROPPED enrollment."""
        from submissions.views import _student_enrolled_in_assignment

        # Simulate a DROPPED enrollment — the queryset with status=ACTIVE returns nothing
        mock_enrollment.objects.filter.return_value.exists.return_value = False

        user = MagicMock()
        user.id = 1
        assignment = MagicMock()
        assignment.course_id = 10

        result = _student_enrolled_in_assignment(user, assignment)
        assert result is False

        # Verify the filter includes status=ACTIVE
        call_kwargs = mock_enrollment.objects.filter.call_args[1]
        assert "status" in call_kwargs, (
            "_student_enrolled_in_assignment must filter by enrollment status"
        )

    @patch("submissions.views.Enrollment")
    def test_active_student_allowed_by_enrollment_check(self, mock_enrollment):
        """_student_enrolled_in_assignment returns True for ACTIVE enrollment."""
        from submissions.views import _student_enrolled_in_assignment

        mock_enrollment.objects.filter.return_value.exists.return_value = True

        user = MagicMock()
        user.id = 1
        assignment = MagicMock()
        assignment.course_id = 10

        result = _student_enrolled_in_assignment(user, assignment)
        assert result is True

    @patch("assignments.services._queries.Enrollment")
    @patch("assignments.services._queries.Assignment")
    @patch("assignments.services._queries.primary_role", return_value="STUDENT")
    @patch("assignments.services._queries.timezone")
    def test_list_for_user_filters_by_active_enrollment(
        self, mock_tz, mock_role, mock_assignment, mock_enrollment
    ):
        """list_for_user only uses enrollments with ACTIVE status."""
        from datetime import UTC, datetime

        from assignments.services._queries import list_for_user

        mock_tz.now.return_value = datetime(2025, 6, 1, tzinfo=UTC)
        mock_enrollment.objects.filter.return_value.values_list.return_value = []

        user = MagicMock()
        user.id = 1

        # The mock returns [] so we get no course_ids, which is fine — we
        # just need to verify the filter was called with status
        mock_qs = MagicMock()
        mock_assignment.objects.select_related.return_value.filter.return_value = mock_qs
        mock_qs.filter.return_value.order_by.return_value = []

        list_for_user(user)

        call_kwargs = mock_enrollment.objects.filter.call_args[1]
        assert "status" in call_kwargs, (
            "list_for_user must filter enrollments by ACTIVE status"
        )


# ---------------------------------------------------------------------------
# Bug 2: Submission answer ownership (cross-assignment_template question)
# ---------------------------------------------------------------------------


class TestAnswerOwnership:
    """_create_answer must reject questions from a different assignment_template."""

    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_rejects_question_from_different_assessment(
        self, mock_question_model, mock_answer, mock_mca, mock_saa, mock_nsa
    ):
        """_create_answer raises ValueError when question belongs to a different assignment_template."""
        from submissions.services import _create_answer

        # Question belongs to assignment 99, but submission targets assignment 20.
        fake_question = MagicMock()
        fake_question.id = 1
        fake_question.assignment_id = 99
        fake_question.question_type = "SHORT_ANSWER"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        payload = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hello"}}

        with pytest.raises(ValueError, match="does not belong"):
            _create_answer(submission, payload)

    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_accepts_question_from_same_assessment(
        self, mock_question_model, mock_answer, mock_mca, mock_saa, mock_nsa
    ):
        """_create_answer succeeds when question belongs to the correct assignment_template."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 1
        fake_question.assignment_id = 20
        fake_question.question_type = "SHORT_ANSWER"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        fake_answer = MagicMock()
        mock_answer.objects.create.return_value = fake_answer

        payload = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hello"}}

        result = _create_answer(submission, payload)
        assert result is fake_answer


# ---------------------------------------------------------------------------
# Bug 3: Answer type mismatch
# ---------------------------------------------------------------------------


class TestAnswerTypeMismatch:
    """_create_answer must reject payloads whose type doesn't match question kind."""

    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_rejects_mismatched_answer_type(
        self, mock_question_model, mock_answer, mock_mca, mock_saa, mock_nsa
    ):
        """_create_answer raises ValueError when payload type != question_type."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 1
        fake_question.assignment_id = 20
        fake_question.question_type = "MULTIPLE_CHOICE"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        # Payload says SHORT_ANSWER but question is MULTIPLE_CHOICE
        payload = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hello"}}

        with pytest.raises(ValueError, match="type mismatch"):
            _create_answer(submission, payload)

    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_accepts_matching_answer_type(
        self, mock_question_model, mock_answer, mock_nsa, mock_mca, mock_saa
    ):
        """_create_answer succeeds when payload type matches question_type."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 1
        fake_question.assignment_id = 20
        fake_question.question_type = "SHORT_ANSWER"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        fake_answer = MagicMock()
        mock_answer.objects.create.return_value = fake_answer

        payload = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hello"}}

        result = _create_answer(submission, payload)
        assert result is fake_answer


# ---------------------------------------------------------------------------
# Bug 4: Placeholder submissions for inactive/archived
# ---------------------------------------------------------------------------


class TestPlaceholderSubmissionFiltering:
    """Submission fan-out must respect enrollment status and assignment status."""

    @patch("assignments.services._mutations.Submission")
    @patch("assignments.services._mutations.Enrollment")
    @patch("assignments.services._mutations.provision_submission_answers")
    def test_create_submissions_for_course_only_active_enrollments(
        self,
        mock_provision_answers,
        mock_enrollment,
        mock_submission,
    ):
        """_create_submissions_for_course filters enrollments by ACTIVE status."""
        from assignments.services._mutations import _create_submissions_for_course

        mock_enrollment.objects.filter.return_value.values_list.return_value = []

        assignment = SimpleNamespace(id=1, assignment_template_id=5, course_id=10)

        _create_submissions_for_course(assignment)

        call_kwargs = mock_enrollment.objects.filter.call_args[1]
        assert "status" in call_kwargs, (
            "_create_submissions_for_course must filter enrollments by ACTIVE status"
        )

    @patch("courses.services._mutations.Submission")
    @patch("assignments.services._content.provision_submission_answers")
    @patch("courses.services._mutations.Assignment")
    def test_create_submissions_for_student_skips_archived_assignments(
        self,
        mock_assignment,
        mock_provision_answers,
        mock_submission,
    ):
        """_create_submissions_for_student filters out archived assignments."""
        from courses.services._mutations import _create_submissions_for_student

        # Return an archived assignment
        archived = MagicMock()
        archived.assignment_template_id = 1
        archived.status = "ARCHIVED"
        mock_assignment.objects.filter.return_value = [archived]

        student = MagicMock()
        student.id = 100
        course = MagicMock()
        course.id = 10

        _create_submissions_for_student(student, course)

        # The filter should exclude archived assignments
        filter_kwargs = mock_assignment.objects.filter.call_args[1]
        assert "status" in filter_kwargs, (
            "_create_submissions_for_student must filter assignments by ACTIVE status"
        )


# ---------------------------------------------------------------------------
# Regression: valid payloads still succeed
# ---------------------------------------------------------------------------


class TestRegressionValidPayloads:
    """Ensure the fixes don't break happy-path scenarios."""

    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_valid_short_answer_still_works(
        self, mock_question_model, mock_answer, mock_nsa, mock_mca, mock_saa
    ):
        """A valid SHORT_ANSWER payload for the correct assignment_template succeeds."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 1
        fake_question.assignment_id = 20
        fake_question.question_type = "SHORT_ANSWER"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        fake_answer = MagicMock()
        mock_answer.objects.create.return_value = fake_answer

        payload = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "ok"}}

        result = _create_answer(submission, payload)
        assert result is fake_answer
        mock_saa.objects.create.assert_called_once()

    @patch("submissions.services.MultipleChoiceSelected")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_valid_multiple_choice_still_works(
        self, mock_question_model, mock_answer, mock_nsa, mock_saa, mock_mca, mock_mcs
    ):
        """A valid MULTIPLE_CHOICE payload for the correct assignment_template succeeds."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 2
        fake_question.assignment_id = 20
        fake_question.question_type = "MULTIPLE_CHOICE"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        fake_answer = MagicMock()
        mock_answer.objects.create.return_value = fake_answer

        payload = {"questionId": 2, "type": "MULTIPLE_CHOICE", "data": {"selected": [0, 1]}}

        result = _create_answer(submission, payload)
        assert result is fake_answer
        mock_mca.objects.create.assert_called_once()

    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_valid_number_scale_still_works(
        self, mock_question_model, mock_answer, mock_mca, mock_saa, mock_nsa
    ):
        """A valid NUMBER_SCALE payload for the correct assignment_template succeeds."""
        from submissions.services import _create_answer

        fake_question = MagicMock()
        fake_question.id = 3
        fake_question.assignment_id = 20
        fake_question.question_type = "NUMBER_SCALE"
        mock_question_model.objects.filter.return_value.first.return_value = fake_question

        submission = MagicMock()
        submission.assignment_id = 20

        fake_answer = MagicMock()
        mock_answer.objects.create.return_value = fake_answer

        payload = {"questionId": 3, "type": "NUMBER_SCALE", "data": {"val": 5}}

        result = _create_answer(submission, payload)
        assert result is fake_answer
        mock_nsa.objects.create.assert_called_once()
