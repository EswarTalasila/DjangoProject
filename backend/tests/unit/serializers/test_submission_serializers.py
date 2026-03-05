"""Unit tests for submissions.serializers validation logic.

No database access required -- serializer validation is purely in-memory.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ============================================================================
# AnswerSerializer
# ============================================================================


class TestAnswerSerializer:
    """Tests for AnswerSerializer field validation."""

    def test_valid_multiple_choice(self):
        """Valid MULTIPLE_CHOICE payload passes validation."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {"selected": [0, 2]}}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_valid_short_answer(self):
        """Valid SHORT_ANSWER payload passes validation."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 2, "type": "SHORT_ANSWER", "data": {"text": "hello"}}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_valid_number_scale(self):
        """Valid NUMBER_SCALE payload passes validation."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 3, "type": "NUMBER_SCALE", "data": {"val": 5}}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_invalid_mood_meter_rejected(self):
        """MOOD_METER type is no longer valid and is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 4, "type": "MOOD_METER", "data": {"row": 1, "col": 2}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "type" in s.errors

    def test_invalid_type_rejected(self):
        """Invalid answer type is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "INVALID_TYPE", "data": {}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "type" in s.errors

    def test_missing_question_id(self):
        """Missing questionId is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"type": "SHORT_ANSWER", "data": {"text": "hi"}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "questionId" in s.errors

    def test_missing_type(self):
        """Missing type field is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "data": {}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "type" in s.errors

    def test_missing_data(self):
        """Missing data field is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER"}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in s.errors

    def test_score_is_optional(self):
        """Score field is optional and defaults to absent."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}}
        s = AnswerSerializer(data=data)
        assert s.is_valid()
        assert "score" not in s.validated_data or s.validated_data.get("score") is None

    def test_score_accepts_null(self):
        """Score field accepts null value."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}, "score": None}
        s = AnswerSerializer(data=data)
        assert s.is_valid()

    def test_score_accepts_float(self):
        """Score field accepts float values."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}, "score": 8.5}
        s = AnswerSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["score"] == 8.5


# ============================================================================
# SubmissionSerializer
# ============================================================================


class TestSubmissionSerializer:
    """Tests for SubmissionSerializer field validation."""

    def test_valid_student_submission(self):
        """Valid student submission payload passes validation."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "studentId": 100,
            "status": "SUBMITTED",
            "answers": [{"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}}],
        }
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_valid_teacher_submission(self):
        """Valid teacher self-assessment payload passes validation."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "teacherId": 200,
            "status": "SUBMITTED",
        }
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_missing_assignment_id(self):
        """Missing assignmentId is rejected."""
        from submissions.serializers import SubmissionSerializer

        data = {"studentId": 100, "status": "SUBMITTED"}
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "assignmentId" in s.errors

    def test_missing_status(self):
        """Missing status is rejected."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "studentId": 100}
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "status" in s.errors

    def test_invalid_status(self):
        """Invalid status value is rejected."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "studentId": 100, "status": "INVALID"}
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "status" in s.errors

    def test_all_valid_statuses(self):
        """All four status values are accepted."""
        from submissions.serializers import SubmissionSerializer

        for status_val in ("NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "GRADED"):
            data = {"assignmentId": 10, "status": status_val}
            s = SubmissionSerializer(data=data)
            assert s.is_valid(), f"{status_val} should be valid, errors: {s.errors}"

    def test_student_id_is_optional(self):
        """studentId field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "status": "SUBMITTED"}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_teacher_id_is_optional(self):
        """teacherId field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "status": "SUBMITTED"}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_answers_is_optional(self):
        """answers field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "status": "SUBMITTED"}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_nested_answer_validation(self):
        """Invalid nested answer data causes the parent serializer to fail."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "status": "SUBMITTED",
            "answers": [{"questionId": 1, "type": "INVALID_TYPE", "data": {}}],
        }
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "answers" in s.errors
