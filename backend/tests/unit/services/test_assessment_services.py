"""Pure unit tests for assessment service functions (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from assessments.models import GradingMode, QuestionKind

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
# assessment_to_dto
# ---------------------------------------------------------------------------


class TestAssessmentToDto:
    """Tests for assessment_to_dto conversion."""

    def test_converts_assessment_with_no_questions(self):
        """Converts assessment with empty questions list."""
        from assessments.services import assessment_to_dto

        assessment = MagicMock()
        assessment.id = 1
        assessment.title = "Test Assessment"
        assessment.category = "General"
        assessment.grading_mode = GradingMode.AUTO
        assessment.rubric_id = None
        assessment.rubric_assessment_ids = []
        assessment.questions.all.return_value = []

        dto = assessment_to_dto(assessment)

        assert dto.id == 1
        assert dto.title == "Test Assessment"
        assert dto.category == "General"
        assert dto.gradingMode == GradingMode.AUTO
        assert dto.questions == []
        assert dto.rubricId is None
        assert dto.rubricAssessmentIds == []

    def test_handles_none_rubric_assessment_ids(self):
        """Handles None rubric_assessment_ids by defaulting to empty list."""
        from assessments.services import assessment_to_dto

        assessment = MagicMock()
        assessment.id = 1
        assessment.title = "Test"
        assessment.category = None
        assessment.grading_mode = GradingMode.MANUAL
        assessment.rubric_id = 5
        assessment.rubric_assessment_ids = None
        assessment.questions.all.return_value = []

        dto = assessment_to_dto(assessment)

        assert dto.rubricAssessmentIds == []
        assert dto.rubricId == 5


# ---------------------------------------------------------------------------
# question_to_dto
# ---------------------------------------------------------------------------


class TestQuestionToDto:
    """Tests for question_to_dto conversion."""

    def test_multiple_choice_question(self):
        """Converts MCQ with choices and selectAll flag."""
        from assessments.services import question_to_dto

        choice1 = SimpleNamespace(choice_text="Option A", points=5)
        choice2 = SimpleNamespace(choice_text="Option B", points=0)

        question = MagicMock()
        question.id = 10
        question.kind = QuestionKind.MULTIPLE_CHOICE
        question.prompt = "Pick one"
        question.max_points = 5.0
        question.auto_gradable = True
        question.graded = False
        question.mcq_choices.all.return_value = [choice1, choice2]
        question.multiple_choice.select_all = False

        dto = question_to_dto(question)

        assert dto.questionId == 10
        assert dto.type == QuestionKind.MULTIPLE_CHOICE
        assert dto.data["choices"] == [
            {"prompt": "Option A", "score": 5},
            {"prompt": "Option B", "score": 0},
        ]
        assert dto.data["selectAll"] is False
        assert dto.selectAll is False

    def test_short_answer_question(self):
        """Converts SHORT_ANSWER with case sensitivity and trim settings."""
        from assessments.services import question_to_dto

        question = MagicMock()
        question.id = 20
        question.kind = QuestionKind.SHORT_ANSWER
        question.prompt = "Type answer"
        question.max_points = 10.0
        question.auto_gradable = False
        question.graded = True
        question.short_answer.case_sensitive = True
        question.short_answer.trim = False

        dto = question_to_dto(question)

        assert dto.data == {"caseSensitive": True, "trim": False}
        assert dto.selectAll is None
        assert dto.min is None
        assert dto.max is None

    def test_number_scale_question(self):
        """Converts NUMBER_SCALE with min, max, and target."""
        from assessments.services import question_to_dto

        question = MagicMock()
        question.id = 30
        question.kind = QuestionKind.NUMBER_SCALE
        question.prompt = "Rate 1-5"
        question.max_points = 5.0
        question.auto_gradable = True
        question.graded = True
        question.number_scale.min = 1
        question.number_scale.max = 5
        question.number_scale.target = 3

        dto = question_to_dto(question)

        assert dto.data == {"min": 1, "max": 5, "target": 3}
        assert dto.min == 1
        assert dto.max == 5

    def test_mood_meter_question(self):
        """Converts MOOD_METER with custom labels."""
        from assessments.services import question_to_dto

        label1 = SimpleNamespace(label="Happy")
        label2 = SimpleNamespace(label="Sad")

        question = MagicMock()
        question.id = 40
        question.kind = QuestionKind.MOOD_METER
        question.prompt = "How are you?"
        question.max_points = 0.0
        question.auto_gradable = False
        question.graded = False
        question.mood_meter_labels.all.return_value = [label1, label2]

        dto = question_to_dto(question)

        assert dto.data == {"labels": ["Happy", "Sad"]}

    def test_unknown_question_kind_returns_none_data(self):
        """Unknown question kind produces None data field."""
        from assessments.services import question_to_dto

        question = MagicMock()
        question.id = 50
        question.kind = "UNKNOWN_TYPE"
        question.prompt = "Mystery"
        question.max_points = 0.0
        question.auto_gradable = False
        question.graded = False

        dto = question_to_dto(question)

        assert dto.data is None


# ---------------------------------------------------------------------------
# create_assessment
# ---------------------------------------------------------------------------


class TestCreateAssessment(_NoopAtomicMixin):
    """Tests for create_assessment service."""

    def test_raises_when_no_grading_mode(self):
        """Raises ValueError when gradingMode is missing."""
        from assessments.services import create_assessment

        with pytest.raises(ValueError, match="gradingMode is required"):
            create_assessment(SimpleNamespace(id=1), {"title": "T"})

    def test_raises_when_no_title(self):
        """Raises ValueError when title is missing."""
        from assessments.services import create_assessment

        with pytest.raises(ValueError, match="title is required"):
            create_assessment(
                SimpleNamespace(id=1), {"gradingMode": GradingMode.AUTO}
            )

    @patch("assessments.services.create_mood_meter_assessment")
    def test_delegates_mood_meter_to_specialized_function(
        self, mock_create_mm
    ):
        """Delegates MOOD_METER grading mode to specialized creator."""
        from assessments.services import create_assessment

        mock_create_mm.return_value = SimpleNamespace(id=1)
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Mood Check",
            "gradingMode": GradingMode.MOOD_METER,
        }

        result = create_assessment(user, payload)

        mock_create_mm.assert_called_once_with(user, payload)
        assert result.id == 1

    @patch("assessments.services._apply_rubric_links")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services.Assessment")
    def test_creates_standard_assessment(
        self, mock_assessment_model, mock_replace, mock_apply
    ):
        """Creates a standard (non-mood-meter) assessment with questions."""
        from assessments.services import create_assessment

        fake_assessment = SimpleNamespace(id=5)
        mock_assessment_model.objects.create.return_value = fake_assessment
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz 1",
            "gradingMode": GradingMode.AUTO,
            "category": "Math",
            "rubricId": None,
            "rubricAssessmentIds": [10, 20],
            "questions": [{"type": "MULTIPLE_CHOICE", "prompt": "Q1"}],
        }

        result = create_assessment(user, payload)

        assert result is fake_assessment
        mock_assessment_model.objects.create.assert_called_once_with(
            title="Quiz 1",
            grading_mode=GradingMode.AUTO,
            created_by_admin=user,
            rubric_id=None,
            rubric_assessment_ids=[10, 20],
            category="Math",
        )
        mock_replace.assert_called_once()
        mock_apply.assert_called_once_with(fake_assessment)

    @patch("assessments.services._apply_rubric_links")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services.Assessment")
    def test_defaults_empty_rubric_assessment_ids(
        self, mock_assessment_model, mock_replace, mock_apply
    ):
        """Defaults rubricAssessmentIds to empty list when None."""
        from assessments.services import create_assessment

        mock_assessment_model.objects.create.return_value = SimpleNamespace(id=1)
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz",
            "gradingMode": GradingMode.AUTO,
        }

        create_assessment(user, payload)

        create_call = mock_assessment_model.objects.create.call_args
        assert create_call.kwargs["rubric_assessment_ids"] == []


# ---------------------------------------------------------------------------
# create_mood_meter_assessment
# ---------------------------------------------------------------------------


class TestCreateMoodMeterAssessment:
    """Tests for create_mood_meter_assessment service."""

    def test_raises_when_no_title(self):
        """Raises ValueError when title is missing."""
        from assessments.services import create_mood_meter_assessment

        with pytest.raises(ValueError, match="title is required"):
            create_mood_meter_assessment(
                SimpleNamespace(id=1), {"gradingMode": GradingMode.MOOD_METER}
            )

    @patch("assessments.services.MoodMeterQuestion")
    @patch("assessments.services.Question")
    @patch("assessments.services.Assessment")
    def test_creates_mood_meter_with_default_question(
        self, mock_assessment_model, mock_question_model, mock_mm_model
    ):
        """Creates assessment with pre-configured mood meter question."""
        from assessments.services import create_mood_meter_assessment

        fake_assessment = SimpleNamespace(id=10)
        mock_assessment_model.objects.create.return_value = fake_assessment
        fake_question = SimpleNamespace(id=20)
        mock_question_model.objects.create.return_value = fake_question
        user = SimpleNamespace(id=1)

        result = create_mood_meter_assessment(
            user, {"title": "Daily Check", "category": "Wellness"}
        )

        assert result is fake_assessment
        mock_assessment_model.objects.create.assert_called_once_with(
            title="Daily Check",
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=user,
            rubric_id=None,
            rubric_assessment_ids=[],
            category="Wellness",
        )
        mock_question_model.objects.create.assert_called_once()
        mock_mm_model.objects.create.assert_called_once_with(question=fake_question)


# ---------------------------------------------------------------------------
# update_assessment
# ---------------------------------------------------------------------------


class TestUpdateAssessment(_NoopAtomicMixin):
    """Tests for update_assessment service."""

    @patch("assessments.services._apply_rubric_links")
    @patch("assessments.services._replace_questions")
    def test_updates_fields_and_replaces_questions(
        self, mock_replace, mock_apply
    ):
        """Updates assessment fields and replaces all questions."""
        from assessments.services import update_assessment

        assessment = MagicMock()
        assessment.title = "Old Title"
        assessment.category = "Old Cat"
        assessment.grading_mode = GradingMode.AUTO
        assessment.rubric_id = None
        assessment.rubric_assessment_ids = []

        payload = {
            "title": "New Title",
            "category": "New Cat",
            "gradingMode": GradingMode.MANUAL,
            "rubricId": 5,
            "rubricAssessmentIds": [10],
            "questions": [{"type": "SHORT_ANSWER", "prompt": "Q"}],
        }

        result = update_assessment(assessment, payload)

        assert result.title == "New Title"
        assert result.category == "New Cat"
        assert result.grading_mode == GradingMode.MANUAL
        assert result.rubric_id == 5
        assert result.rubric_assessment_ids == [10]
        assessment.save.assert_called_once()
        mock_replace.assert_called_once()
        mock_apply.assert_called_once()

    @patch("assessments.services._apply_rubric_links")
    @patch("assessments.services._replace_questions")
    def test_preserves_title_when_not_provided(
        self, mock_replace, mock_apply
    ):
        """Preserves existing title when not in payload."""
        from assessments.services import update_assessment

        assessment = MagicMock()
        assessment.title = "Keep Me"

        payload = {"category": "New"}

        result = update_assessment(assessment, payload)

        assert result.title == "Keep Me"


# ---------------------------------------------------------------------------
# delete_assessment
# ---------------------------------------------------------------------------


class TestDeleteAssessment(_NoopAtomicMixin):
    """Tests for delete_assessment service."""

    @patch("assessments.services.Assignment")
    def test_deletes_assignments_then_assessment(
        self, mock_assignment_model
    ):
        """Deletes associated assignments before the assessment itself."""
        from assessments.services import delete_assessment

        assessment = MagicMock()

        delete_assessment(assessment)

        mock_assignment_model.objects.filter.assert_called_once_with(
            assessment=assessment
        )
        mock_assignment_model.objects.filter.return_value.delete.assert_called_once()
        assessment.delete.assert_called_once()


# ---------------------------------------------------------------------------
# list_assessments
# ---------------------------------------------------------------------------


class TestListAssessments:
    """Tests for list_assessments service."""

    @patch("assessments.services.Assessment")
    def test_returns_all_assessments(self, mock_assessment_model):
        """Returns list of all assessments."""
        from assessments.services import list_assessments

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_assessment_model.objects.all.return_value = sentinel

        result = list_assessments()

        assert result == sentinel


# ---------------------------------------------------------------------------
# _replace_questions
# ---------------------------------------------------------------------------


class TestReplaceQuestions:
    """Tests for _replace_questions internal helper."""

    @patch("assessments.services._create_question")
    @patch("assessments.services.Question")
    def test_deletes_existing_and_creates_new(
        self, mock_question_model, mock_create_question
    ):
        """Deletes all existing questions and creates new ones."""
        from assessments.services import _replace_questions

        assessment = SimpleNamespace(id=1)
        questions = [
            {"type": "SHORT_ANSWER", "prompt": "Q1"},
            {"type": "SHORT_ANSWER", "prompt": "Q2"},
        ]

        _replace_questions(assessment, questions)

        mock_question_model.objects.filter.assert_called_once_with(
            assessment=assessment
        )
        mock_question_model.objects.filter.return_value.delete.assert_called_once()
        assert mock_create_question.call_count == 2

    @patch("assessments.services._create_question")
    @patch("assessments.services.Question")
    def test_handles_empty_questions_list(
        self, mock_question_model, mock_create_question
    ):
        """Handles empty question list without errors."""
        from assessments.services import _replace_questions

        _replace_questions(SimpleNamespace(id=1), [])

        mock_question_model.objects.filter.return_value.delete.assert_called_once()
        mock_create_question.assert_not_called()


# ---------------------------------------------------------------------------
# _create_question
# ---------------------------------------------------------------------------


class TestCreateQuestion:
    """Tests for _create_question internal helper."""

    def test_raises_when_no_type(self):
        """Raises ValueError when question type is missing."""
        from assessments.services import _create_question

        with pytest.raises(ValueError, match="Question type is required"):
            _create_question(SimpleNamespace(id=1), {"prompt": "Q"})

    def test_raises_when_no_prompt(self):
        """Raises ValueError when prompt is missing."""
        from assessments.services import _create_question

        with pytest.raises(ValueError, match="Question prompt is required"):
            _create_question(
                SimpleNamespace(id=1), {"type": QuestionKind.SHORT_ANSWER}
            )

    @patch("assessments.services.MultipleChoiceQuestion")
    @patch("assessments.services.McqChoice")
    @patch("assessments.services.Question")
    def test_creates_multiple_choice_with_choices(
        self, mock_q_model, mock_choice_model, mock_mcq_model
    ):
        """Creates MCQ question with choices."""
        from assessments.services import _create_question

        fake_question = SimpleNamespace(id=10)
        mock_q_model.objects.create.return_value = fake_question

        payload = {
            "type": QuestionKind.MULTIPLE_CHOICE,
            "prompt": "Pick one",
            "maxPoints": 5,
            "data": {
                "selectAll": True,
                "choices": [
                    {"prompt": "A", "score": 5},
                    {"prompt": "B", "score": 0},
                ],
            },
        }

        result = _create_question(SimpleNamespace(id=1), payload)

        assert result is fake_question
        mock_mcq_model.objects.create.assert_called_once_with(
            question=fake_question, select_all=True
        )
        assert mock_choice_model.objects.create.call_count == 2

    @patch("assessments.services.ShortAnswerQuestion")
    @patch("assessments.services.Question")
    def test_creates_short_answer(self, mock_q_model, mock_sa_model):
        """Creates short answer question with settings."""
        from assessments.services import _create_question

        fake_question = SimpleNamespace(id=10)
        mock_q_model.objects.create.return_value = fake_question

        payload = {
            "type": QuestionKind.SHORT_ANSWER,
            "prompt": "Answer here",
            "data": {"caseSensitive": True, "trim": False},
        }

        result = _create_question(SimpleNamespace(id=1), payload)

        assert result is fake_question
        mock_sa_model.objects.create.assert_called_once_with(
            question=fake_question, case_sensitive=True, trim=False
        )

    @patch("assessments.services.NumberScaleQuestion")
    @patch("assessments.services.Question")
    def test_creates_number_scale(self, mock_q_model, mock_ns_model):
        """Creates number scale question."""
        from assessments.services import _create_question

        fake_question = SimpleNamespace(id=10)
        mock_q_model.objects.create.return_value = fake_question

        payload = {
            "type": QuestionKind.NUMBER_SCALE,
            "prompt": "Rate 1-5",
            "data": {"min": 1, "max": 5, "target": 3},
        }

        result = _create_question(SimpleNamespace(id=1), payload)

        assert result is fake_question
        mock_ns_model.objects.create.assert_called_once_with(
            question=fake_question, min=1, max=5, target=3
        )

    @patch("assessments.services.NumberScaleQuestion")
    @patch("assessments.services.Question")
    def test_number_scale_raises_when_missing_min_max(
        self, mock_q_model, mock_ns_model
    ):
        """Raises ValueError when min or max is missing for number scale."""
        from assessments.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        with pytest.raises(
            ValueError, match="min and max are required"
        ):
            _create_question(
                SimpleNamespace(id=1),
                {
                    "type": QuestionKind.NUMBER_SCALE,
                    "prompt": "Rate",
                    "data": {"min": 1},
                },
            )

    @patch("assessments.services.NumberScaleQuestion")
    @patch("assessments.services.Question")
    def test_number_scale_swaps_min_max_when_inverted(
        self, mock_q_model, mock_ns_model
    ):
        """Swaps min and max when min > max."""
        from assessments.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        _create_question(
            SimpleNamespace(id=1),
            {
                "type": QuestionKind.NUMBER_SCALE,
                "prompt": "Rate",
                "data": {"min": 10, "max": 1},
            },
        )

        create_call = mock_ns_model.objects.create.call_args
        assert create_call.kwargs["min"] == 1
        assert create_call.kwargs["max"] == 10

    @patch("assessments.services.MoodMeterLabel")
    @patch("assessments.services.MoodMeterQuestion")
    @patch("assessments.services.Question")
    def test_creates_mood_meter_with_labels(
        self, mock_q_model, mock_mm_model, mock_label_model
    ):
        """Creates mood meter question with custom labels."""
        from assessments.services import _create_question

        fake_question = SimpleNamespace(id=10)
        mock_q_model.objects.create.return_value = fake_question

        payload = {
            "type": QuestionKind.MOOD_METER,
            "prompt": "How are you?",
            "data": {"labels": ["Happy", "Sad", "Calm", "Angry"]},
        }

        result = _create_question(SimpleNamespace(id=1), payload)

        assert result is fake_question
        mock_mm_model.objects.create.assert_called_once_with(
            question=fake_question
        )
        assert mock_label_model.objects.create.call_count == 4

    @patch("assessments.services.Question")
    def test_auto_gradable_set_for_mcq_and_number_scale(self, mock_q_model):
        """auto_gradable is set to True for MCQ and NUMBER_SCALE."""
        from assessments.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        # We need to also mock the MCQ creation
        with patch("assessments.services.MultipleChoiceQuestion"):
            _create_question(
                SimpleNamespace(id=1),
                {
                    "type": QuestionKind.MULTIPLE_CHOICE,
                    "prompt": "Q",
                    "data": {},
                },
            )

        create_call = mock_q_model.objects.create.call_args
        assert create_call.kwargs["auto_gradable"] is True

    @patch("assessments.services.ShortAnswerQuestion")
    @patch("assessments.services.Question")
    def test_auto_gradable_false_for_short_answer(
        self, mock_q_model, mock_sa_model
    ):
        """auto_gradable is False for SHORT_ANSWER."""
        from assessments.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        _create_question(
            SimpleNamespace(id=1),
            {
                "type": QuestionKind.SHORT_ANSWER,
                "prompt": "Q",
                "data": {},
            },
        )

        create_call = mock_q_model.objects.create.call_args
        assert create_call.kwargs["auto_gradable"] is False


# ---------------------------------------------------------------------------
# _apply_rubric_links
# ---------------------------------------------------------------------------


class TestApplyRubricLinks:
    """Tests for _apply_rubric_links internal helper."""

    def test_does_nothing_for_non_rubric_mode(self):
        """Does nothing when grading_mode is not RUBRIC."""
        from assessments.services import _apply_rubric_links

        assessment = SimpleNamespace(grading_mode=GradingMode.AUTO)

        # Should not raise
        _apply_rubric_links(assessment)

    def test_does_nothing_when_no_rubric_ids(self):
        """Does nothing when rubric_assessment_ids is empty."""
        from assessments.services import _apply_rubric_links

        assessment = SimpleNamespace(
            grading_mode=GradingMode.RUBRIC,
            rubric_assessment_ids=[],
        )

        _apply_rubric_links(assessment)

    @patch("assessments.services.Assessment")
    def test_links_rubric_to_target_assessments(self, mock_assessment_model):
        """Updates rubric_id on target assessments."""
        from assessments.services import _apply_rubric_links

        target1 = MagicMock()
        target2 = MagicMock()

        def filter_side_effect(id):
            mapping = {10: target1, 20: target2}
            result = MagicMock()
            result.first.return_value = mapping.get(id)
            return result

        mock_assessment_model.objects.filter.side_effect = filter_side_effect

        assessment = SimpleNamespace(
            id=99,
            grading_mode=GradingMode.RUBRIC,
            rubric_assessment_ids=[10, 20],
        )

        _apply_rubric_links(assessment)

        assert target1.rubric_id == 99
        target1.save.assert_called_once_with(update_fields=["rubric_id"])
        assert target2.rubric_id == 99
        target2.save.assert_called_once_with(update_fields=["rubric_id"])

    @patch("assessments.services.Assessment")
    def test_skips_missing_target_assessments(self, mock_assessment_model):
        """Skips target assessment IDs that do not exist."""
        from assessments.services import _apply_rubric_links

        mock_assessment_model.objects.filter.return_value.first.return_value = None

        assessment = SimpleNamespace(
            id=99,
            grading_mode=GradingMode.RUBRIC,
            rubric_assessment_ids=[999],
        )

        # Should not raise
        _apply_rubric_links(assessment)
