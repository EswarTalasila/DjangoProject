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

    def test_score_is_read_only(self):
        """Score field is read-only and excluded from validated_data."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}, "score": 8.5}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors
        assert "score" not in s.validated_data

    def test_score_absent_is_valid(self):
        """Omitting score is valid."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}}
        s = AnswerSerializer(data=data)
        assert s.is_valid()

    # ── Data key structural validation ──────────────────────────────────

    def test_mcq_missing_selected_rejected(self):
        """MULTIPLE_CHOICE data without 'selected' is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {"wrong_key": [0]}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in s.errors.get("non_field_errors", [""])[0] or "data" in str(s.errors)

    def test_short_answer_missing_text_rejected(self):
        """SHORT_ANSWER data without 'text' is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"value": "hi"}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()

    def test_number_scale_missing_val_rejected(self):
        """NUMBER_SCALE data without 'val' is rejected."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "NUMBER_SCALE", "data": {"value": 5}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()

    def test_mcq_empty_selected_is_valid(self):
        """MULTIPLE_CHOICE data with empty selected list is still structurally valid."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {"selected": []}}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_mcq_selected_must_be_list(self):
        """MULTIPLE_CHOICE selected payload must be a list."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {"selected": "oops"}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in str(s.errors)

    def test_mcq_selected_entries_must_be_ints(self):
        """MULTIPLE_CHOICE selected entries must be integers."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {"selected": [0, "2"]}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in str(s.errors)

    def test_data_with_extra_keys_is_valid(self):
        """Extra keys in data dict are allowed (forward compatibility)."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi", "extra": True}}
        s = AnswerSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_mcq_empty_data_rejected(self):
        """MULTIPLE_CHOICE with empty data dict is rejected (missing 'selected')."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "MULTIPLE_CHOICE", "data": {}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()

    def test_short_answer_text_must_be_string(self):
        """SHORT_ANSWER text payload must be a string."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": ["hi"]}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in str(s.errors)

    def test_number_scale_val_must_be_integer(self):
        """NUMBER_SCALE val payload must be an integer."""
        from submissions.serializers import AnswerSerializer

        data = {"questionId": 1, "type": "NUMBER_SCALE", "data": {"val": "five"}}
        s = AnswerSerializer(data=data)
        assert not s.is_valid()
        assert "data" in str(s.errors)


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
        }
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_missing_assignment_id(self):
        """Missing assignmentId is rejected."""
        from submissions.serializers import SubmissionSerializer

        data = {"studentId": 100}
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "assignmentId" in s.errors

    def test_status_is_read_only(self):
        """Status field is read-only and excluded from validated_data."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED"}
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors
        assert "status" not in s.validated_data

    def test_status_omitted_is_valid(self):
        """Omitting status is valid (service layer controls lifecycle)."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10, "studentId": 100}
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_student_id_is_optional(self):
        """studentId field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_teacher_id_is_optional(self):
        """teacherId field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_answers_is_optional(self):
        """answers field is optional."""
        from submissions.serializers import SubmissionSerializer

        data = {"assignmentId": 10}
        s = SubmissionSerializer(data=data)
        assert s.is_valid()

    def test_nested_answer_validation(self):
        """Invalid nested answer data causes the parent serializer to fail."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "answers": [{"questionId": 1, "type": "INVALID_TYPE", "data": {}}],
        }
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "answers" in s.errors

    def test_nested_answer_structural_validation(self):
        """Nested answer with missing required data keys causes parent to fail."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "answers": [{"questionId": 1, "type": "SHORT_ANSWER", "data": {"wrong": "key"}}],
        }
        s = SubmissionSerializer(data=data)
        assert not s.is_valid()
        assert "answers" in s.errors

    def test_submitted_at_and_score_are_read_only(self):
        """submittedAt and score are read-only and excluded from validated_data."""
        from submissions.serializers import SubmissionSerializer

        data = {
            "assignmentId": 10,
            "submittedAt": "2026-01-01T00:00:00Z",
            "score": 95.0,
        }
        s = SubmissionSerializer(data=data)
        assert s.is_valid(), s.errors
        assert "submittedAt" not in s.validated_data
        assert "score" not in s.validated_data
