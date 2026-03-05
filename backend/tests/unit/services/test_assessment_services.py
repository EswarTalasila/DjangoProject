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
        assessment.scoring_policy = "STANDARD"
        assessment.questions.all.return_value = []
        assessment.question_groups.all.return_value.order_by.return_value = []

        dto = assessment_to_dto(assessment)

        assert dto.id == 1
        assert dto.title == "Test Assessment"
        assert dto.category == "General"
        assert dto.gradingMode == GradingMode.AUTO
        assert dto.scoringPolicy == "STANDARD"
        assert dto.questions == []
        assert dto.questionGroups == []

    def test_handles_scoring_policy_completion(self):
        """Handles COMPLETION scoring policy."""
        from assessments.services import assessment_to_dto

        assessment = MagicMock()
        assessment.id = 1
        assessment.title = "Test"
        assessment.category = None
        assessment.grading_mode = GradingMode.MANUAL
        assessment.scoring_policy = "COMPLETION"
        assessment.questions.all.return_value = []
        assessment.question_groups.all.return_value.order_by.return_value = []

        dto = assessment_to_dto(assessment)

        assert dto.scoringPolicy == "COMPLETION"
        assert dto.questionGroups == []


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
        question.question_group_id = None
        question.rubric_id = None
        question.grading_strategy = "AUTO"
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
        question.question_group_id = None
        question.rubric_id = None
        question.grading_strategy = "AUTO"
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
        question.question_group_id = None
        question.rubric_id = None
        question.grading_strategy = "AUTO"
        question.number_scale.min = 1
        question.number_scale.max = 5
        question.number_scale.target = 3

        dto = question_to_dto(question)

        assert dto.data == {"min": 1, "max": 5, "target": 3}
        assert dto.min == 1
        assert dto.max == 5

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
        question.question_group_id = None
        question.rubric_id = None
        question.grading_strategy = "AUTO"

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

    @patch("assessments.services._validate_rubric_rules")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services._create_question_groups")
    @patch("assessments.services.Assessment")
    def test_creates_standard_assessment(
        self, mock_assessment_model, mock_create_groups, mock_replace, mock_validate
    ):
        """Creates a standard assessment with questions."""
        from assessments.services import create_assessment

        fake_assessment = SimpleNamespace(id=5)
        mock_assessment_model.objects.create.return_value = fake_assessment
        mock_create_groups.return_value = {}
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz 1",
            "gradingMode": GradingMode.AUTO,
            "category": "Math",
            "questions": [{"type": "MULTIPLE_CHOICE", "prompt": "Q1"}],
        }

        result = create_assessment(user, payload)

        assert result is fake_assessment
        mock_assessment_model.objects.create.assert_called_once_with(
            title="Quiz 1",
            grading_mode=GradingMode.AUTO,
            scoring_policy="STANDARD",
            created_by_admin=user,
            category="Math",
        )
        mock_replace.assert_called_once()
        mock_validate.assert_called_once_with(fake_assessment)

    @patch("assessments.services._validate_rubric_rules")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services._create_question_groups")
    @patch("assessments.services.Assessment")
    def test_defaults_scoring_policy_to_standard(
        self, mock_assessment_model, mock_create_groups, mock_replace, mock_validate
    ):
        """Defaults scoringPolicy to STANDARD when not provided."""
        from assessments.services import create_assessment

        mock_assessment_model.objects.create.return_value = SimpleNamespace(id=1)
        mock_create_groups.return_value = {}
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz",
            "gradingMode": GradingMode.AUTO,
        }

        create_assessment(user, payload)

        create_call = mock_assessment_model.objects.create.call_args
        assert create_call.kwargs["scoring_policy"] == "STANDARD"


# ---------------------------------------------------------------------------
# update_assessment
# ---------------------------------------------------------------------------


class TestUpdateAssessment(_NoopAtomicMixin):
    """Tests for update_assessment service."""

    @patch("assessments.services._validate_rubric_rules")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services._create_question_groups")
    @patch("assessments.services.AssessmentQuestionGroup")
    @patch("assessments.services.Assignment")
    def test_updates_fields_and_replaces_questions(
        self, mock_assignment, mock_aqg, mock_create_groups, mock_replace, mock_validate
    ):
        """Updates assessment fields and replaces all questions."""
        from assessments.services import update_assessment

        mock_assignment.objects.filter.return_value.exists.return_value = False
        mock_create_groups.return_value = {}

        assessment = MagicMock()
        assessment.title = "Old Title"
        assessment.category = "Old Cat"
        assessment.grading_mode = GradingMode.AUTO
        assessment.scoring_policy = "STANDARD"

        payload = {
            "title": "New Title",
            "category": "New Cat",
            "gradingMode": GradingMode.MANUAL,
            "scoringPolicy": "COMPLETION",
            "questions": [{"type": "SHORT_ANSWER", "prompt": "Q"}],
        }

        result = update_assessment(assessment, payload)

        assert result.title == "New Title"
        assert result.category == "New Cat"
        assert result.grading_mode == GradingMode.MANUAL
        assert result.scoring_policy == "COMPLETION"
        assessment.save.assert_called_once()
        mock_replace.assert_called_once()
        mock_validate.assert_called_once()

    @patch("assessments.services._validate_rubric_rules")
    @patch("assessments.services._replace_questions")
    @patch("assessments.services._create_question_groups")
    @patch("assessments.services.AssessmentQuestionGroup")
    @patch("assessments.services.Assignment")
    def test_preserves_title_when_not_provided(
        self, mock_assignment, mock_aqg, mock_create_groups, mock_replace, mock_validate
    ):
        """Preserves existing title when not in payload."""
        from assessments.services import update_assessment

        mock_assignment.objects.filter.return_value.exists.return_value = False
        mock_create_groups.return_value = {}

        assessment = MagicMock()
        assessment.title = "Keep Me"
        assessment.grading_mode = GradingMode.AUTO
        assessment.scoring_policy = "STANDARD"

        payload = {"category": "New"}

        result = update_assessment(assessment, payload)

        assert result.title == "Keep Me"


# ---------------------------------------------------------------------------
# delete_assessment
# ---------------------------------------------------------------------------


class TestDeleteAssessment(_NoopAtomicMixin):
    """Tests for delete_assessment service."""

    @patch("assessments.services.Assignment")
    def test_deletes_assessment_when_no_assignments(
        self, mock_assignment_model
    ):
        """Deletes assessment when no assignments reference it."""
        from assessments.services import delete_assessment

        mock_assignment_model.objects.filter.return_value.exists.return_value = False
        assessment = MagicMock()

        delete_assessment(assessment)

        mock_assignment_model.objects.filter.assert_called_once_with(
            assessment=assessment
        )
        assessment.delete.assert_called_once()

    @patch("assessments.services.Assignment")
    def test_raises_when_assignments_reference(
        self, mock_assignment_model
    ):
        """Raises AssessmentReferencedError when assignments reference the assessment."""
        from assessments.services import AssessmentReferencedError, delete_assessment

        mock_assignment_model.objects.filter.return_value.exists.return_value = True
        assessment = MagicMock()

        with pytest.raises(AssessmentReferencedError):
            delete_assessment(assessment)


# ---------------------------------------------------------------------------
# list_assessments
# ---------------------------------------------------------------------------


class TestListAssessments:
    """Tests for list_assessments service."""

    @patch("assessments.services.Assessment")
    def test_returns_active_assessments_by_default(self, mock_assessment_model):
        """Returns list of active assessments by default."""
        from assessments.services import list_assessments

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        qs = MagicMock()
        mock_assessment_model.objects.all.return_value = qs
        qs.filter.return_value = sentinel

        result = list_assessments()

        assert result == sentinel
        qs.filter.assert_called_once()

    @patch("assessments.services.Assessment")
    def test_returns_all_when_include_archived(self, mock_assessment_model):
        """Returns all assessments when include_archived=True."""
        from assessments.services import list_assessments

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_assessment_model.objects.all.return_value = sentinel

        result = list_assessments(include_archived=True)

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
            _create_question(SimpleNamespace(id=1), {"prompt": "Q"}, {})

    def test_raises_when_no_prompt(self):
        """Raises ValueError when prompt is missing."""
        from assessments.services import _create_question

        with pytest.raises(ValueError, match="Question prompt is required"):
            _create_question(
                SimpleNamespace(id=1), {"type": QuestionKind.SHORT_ANSWER}, {}
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

        result = _create_question(SimpleNamespace(id=1), payload, {})

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

        result = _create_question(SimpleNamespace(id=1), payload, {})

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

        result = _create_question(SimpleNamespace(id=1), payload, {})

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
                {},
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
            {},
        )

        create_call = mock_ns_model.objects.create.call_args
        assert create_call.kwargs["min"] == 1
        assert create_call.kwargs["max"] == 10

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
                {},
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
            {},
        )

        create_call = mock_q_model.objects.create.call_args
        assert create_call.kwargs["auto_gradable"] is False
