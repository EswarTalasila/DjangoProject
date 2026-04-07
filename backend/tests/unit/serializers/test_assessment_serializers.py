"""Pure unit tests for assessment serializer validation (no database)."""

from __future__ import annotations

import pytest

from assessments.models import GradingMode, QuestionKind
from assessments.serializers import (
    AssessmentSerializer,
    MCQChoiceSerializer,
    MultipleChoiceDataSerializer,
    NumberScaleDataSerializer,
    QuestionSerializer,
    ShortAnswerDataSerializer,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# MCQChoiceSerializer
# ---------------------------------------------------------------------------


class TestMCQChoiceSerializer:
    """Tests for MCQChoiceSerializer validation."""

    def test_valid_choice(self):
        """Accepts valid choice with prompt and score."""
        s = MCQChoiceSerializer(data={"prompt": "Option A", "score": 5.0})
        assert s.is_valid()

    def test_rejects_missing_prompt(self):
        """Rejects choice without prompt."""
        s = MCQChoiceSerializer(data={"score": 5.0})
        assert not s.is_valid()
        assert "prompt" in s.errors

    def test_rejects_missing_score(self):
        """Rejects choice without score."""
        s = MCQChoiceSerializer(data={"prompt": "A"})
        assert not s.is_valid()
        assert "score" in s.errors

    def test_accepts_zero_score(self):
        """Accepts zero as a valid score."""
        s = MCQChoiceSerializer(data={"prompt": "Wrong", "score": 0.0})
        assert s.is_valid()

    def test_accepts_blank_prompt(self):
        """Allows blank prompts for in-progress draft choices."""
        s = MCQChoiceSerializer(data={"prompt": "", "score": 0.0})
        assert s.is_valid()

    def test_accepts_negative_score(self):
        """Accepts negative score for penalty choices."""
        s = MCQChoiceSerializer(data={"prompt": "Penalty", "score": -1.0})
        assert s.is_valid()


# ---------------------------------------------------------------------------
# MultipleChoiceDataSerializer
# ---------------------------------------------------------------------------


class TestMultipleChoiceDataSerializer:
    """Tests for MultipleChoiceDataSerializer validation."""

    def test_valid_data_with_choices(self):
        """Accepts valid MCQ data with choices list."""
        data = {
            "choices": [
                {"prompt": "A", "score": 5.0},
                {"prompt": "B", "score": 0.0},
            ],
            "selectAll": True,
        }
        s = MultipleChoiceDataSerializer(data=data)
        assert s.is_valid()

    def test_select_all_is_optional(self):
        """selectAll field is not required."""
        data = {"choices": [{"prompt": "A", "score": 1.0}]}
        s = MultipleChoiceDataSerializer(data=data)
        assert s.is_valid()

    def test_rejects_missing_choices(self):
        """Rejects data without choices field."""
        s = MultipleChoiceDataSerializer(data={})
        assert not s.is_valid()
        assert "choices" in s.errors

    def test_rejects_invalid_choice_in_list(self):
        """Rejects data when a choice is invalid."""
        data = {"choices": [{"prompt": "A"}]}  # missing score
        s = MultipleChoiceDataSerializer(data=data)
        assert not s.is_valid()


# ---------------------------------------------------------------------------
# ShortAnswerDataSerializer
# ---------------------------------------------------------------------------


class TestShortAnswerDataSerializer:
    """Tests for ShortAnswerDataSerializer validation."""

    def test_valid_data(self):
        """Accepts valid short answer data."""
        s = ShortAnswerDataSerializer(data={"caseSensitive": True, "trim": False})
        assert s.is_valid()

    def test_all_fields_optional(self):
        """All fields are optional."""
        s = ShortAnswerDataSerializer(data={})
        assert s.is_valid()


# ---------------------------------------------------------------------------
# NumberScaleDataSerializer
# ---------------------------------------------------------------------------


class TestNumberScaleDataSerializer:
    """Tests for NumberScaleDataSerializer validation."""

    def test_valid_data(self):
        """Accepts valid number scale data."""
        s = NumberScaleDataSerializer(data={"min": 1, "max": 10, "target": 5})
        assert s.is_valid()

    def test_target_is_optional(self):
        """Target field is optional."""
        s = NumberScaleDataSerializer(data={"min": 1, "max": 10})
        assert s.is_valid()

    def test_target_allows_null(self):
        """Target field allows null."""
        s = NumberScaleDataSerializer(data={"min": 1, "max": 10, "target": None})
        assert s.is_valid()

    def test_rejects_missing_min(self):
        """Allows missing min for incomplete drafts."""
        s = NumberScaleDataSerializer(data={"max": 10})
        assert s.is_valid()
        assert "min" not in s.validated_data

    def test_rejects_missing_max(self):
        """Allows missing max for incomplete drafts."""
        s = NumberScaleDataSerializer(data={"min": 1})
        assert s.is_valid()
        assert "max" not in s.validated_data



# ---------------------------------------------------------------------------
# QuestionSerializer
# ---------------------------------------------------------------------------


class TestQuestionSerializer:
    """Tests for QuestionSerializer validation."""

    def test_valid_question(self):
        """Accepts valid question payload."""
        data = {
            "type": QuestionKind.SHORT_ANSWER,
            "prompt": "What is 2+2?",
            "maxPoints": 10.0,
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()

    def test_question_id_is_optional(self):
        """questionId is optional for new questions."""
        data = {
            "type": QuestionKind.MULTIPLE_CHOICE,
            "prompt": "Pick one",
            "maxPoints": 5.0,
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()
        assert "questionId" not in s.validated_data

    def test_question_id_allows_null(self):
        """questionId allows null value."""
        data = {
            "questionId": None,
            "type": QuestionKind.MULTIPLE_CHOICE,
            "prompt": "Pick one",
            "maxPoints": 5.0,
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()

    def test_rejects_invalid_type(self):
        """Rejects invalid question type."""
        data = {
            "type": "INVALID_TYPE",
            "prompt": "Q",
            "maxPoints": 5.0,
        }
        s = QuestionSerializer(data=data)
        assert not s.is_valid()
        assert "type" in s.errors

    def test_rejects_missing_prompt(self):
        """Rejects question without prompt."""
        data = {"type": QuestionKind.SHORT_ANSWER, "maxPoints": 5.0}
        s = QuestionSerializer(data=data)
        assert not s.is_valid()
        assert "prompt" in s.errors

    def test_accepts_blank_prompt(self):
        """Allows blank question prompts for in-progress drafts."""
        data = {
            "type": QuestionKind.SHORT_ANSWER,
            "prompt": "",
            "maxPoints": 5.0,
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()

    def test_rejects_missing_max_points(self):
        """Rejects question without maxPoints."""
        data = {"type": QuestionKind.SHORT_ANSWER, "prompt": "Q"}
        s = QuestionSerializer(data=data)
        assert not s.is_valid()
        assert "maxPoints" in s.errors

    def test_data_field_is_optional(self):
        """data field is optional."""
        data = {
            "type": QuestionKind.SHORT_ANSWER,
            "prompt": "Q",
            "maxPoints": 0.0,
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()

    def test_data_field_accepts_dict(self):
        """data field accepts a dictionary."""
        data = {
            "type": QuestionKind.SHORT_ANSWER,
            "prompt": "Q",
            "maxPoints": 0.0,
            "data": {"caseSensitive": True},
        }
        s = QuestionSerializer(data=data)
        assert s.is_valid()


# ---------------------------------------------------------------------------
# AssessmentSerializer
# ---------------------------------------------------------------------------


class TestAssessmentSerializer:
    """Tests for AssessmentSerializer validation."""

    def test_valid_assessment(self):
        """Accepts valid assessment payload."""
        data = {
            "title": "Quiz 1",
            "gradingMode": GradingMode.AUTO,
            "questions": [
                {
                    "type": QuestionKind.SHORT_ANSWER,
                    "prompt": "Q1",
                    "maxPoints": 10.0,
                }
            ],
        }
        s = AssessmentSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_rejects_missing_title(self):
        """Rejects assessment without title."""
        s = AssessmentSerializer(data={"gradingMode": GradingMode.AUTO})
        assert not s.is_valid()
        assert "title" in s.errors

    def test_accepts_blank_title(self):
        """Allows blank titles for in-progress drafts."""
        s = AssessmentSerializer(data={"title": "", "gradingMode": GradingMode.AUTO})
        assert s.is_valid(), s.errors

    def test_rejects_missing_grading_mode(self):
        """Rejects assessment without gradingMode."""
        s = AssessmentSerializer(data={"title": "Quiz"})
        assert not s.is_valid()
        assert "gradingMode" in s.errors

    def test_rejects_invalid_grading_mode(self):
        """Rejects invalid grading mode value."""
        s = AssessmentSerializer(
            data={"title": "Quiz", "gradingMode": "INVALID"}
        )
        assert not s.is_valid()
        assert "gradingMode" in s.errors

    def test_questions_are_optional(self):
        """questions field is optional."""
        data = {"title": "Quiz", "gradingMode": GradingMode.MANUAL}
        s = AssessmentSerializer(data=data)
        assert s.is_valid()

    def test_id_is_optional(self):
        """id field is optional (for new assessments)."""
        data = {"title": "Quiz", "gradingMode": GradingMode.AUTO}
        s = AssessmentSerializer(data=data)
        assert s.is_valid()
        assert "id" not in s.validated_data

    def test_category_allows_blank_and_null(self):
        """category allows blank and null values."""
        data = {"title": "Quiz", "gradingMode": GradingMode.AUTO, "category": ""}
        s = AssessmentSerializer(data=data)
        assert s.is_valid()

        data["category"] = None
        s = AssessmentSerializer(data=data)
        assert s.is_valid()

    def test_accepts_rubric_id_field(self):
        """rubricId is now a real field for assessment-level rubrics."""
        data = {
            "title": "Quiz",
            "gradingMode": GradingMode.AUTO,
            "rubricId": None,
        }
        s = AssessmentSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_rejects_legacy_rubric_assessment_ids_field(self):
        """Rejects legacy rubricAssessmentIds field with validation error."""
        data = {
            "title": "Quiz",
            "gradingMode": GradingMode.AUTO,
            "rubricAssessmentIds": [],
        }
        s = AssessmentSerializer(data=data)
        assert not s.is_valid()

    def test_scoring_policy_is_optional(self):
        """scoringPolicy is optional and defaults to STANDARD."""
        data = {"title": "Quiz", "gradingMode": GradingMode.AUTO}
        s = AssessmentSerializer(data=data)
        assert s.is_valid()

    def test_question_groups_are_optional(self):
        """questionGroups field is optional."""
        data = {"title": "Quiz", "gradingMode": GradingMode.MANUAL}
        s = AssessmentSerializer(data=data)
        assert s.is_valid()
