"""Pure unit tests for assignment_template service functions (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from assignment_templates.models import GradingMode, QuestionKind
from core.lifecycle import ConflictError

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
# assignment_template_to_dto
# ---------------------------------------------------------------------------


class TestAssignmentTemplateToDto:
    """Tests for assignment_template_to_dto conversion."""

    def test_converts_assignment_template_with_no_questions(self):
        """Converts assignment_template with empty questions list."""
        from assignment_templates.services import assignment_template_to_dto

        assignment_template = MagicMock()
        assignment_template.id = 1
        assignment_template.title = "Test AssignmentTemplate"
        assignment_template.category = "General"
        assignment_template.grading_mode = GradingMode.AUTO
        assignment_template.scoring_policy = "STANDARD"
        assignment_template.submission_mode = "DIGITAL"
        assignment_template.status = "ACTIVE"
        assignment_template.rubric_id = None
        assignment_template.questions.all.return_value = []
        assignment_template.question_groups.all.return_value = []

        dto = assignment_template_to_dto(assignment_template)

        assert dto.id == 1
        assert dto.title == "Test AssignmentTemplate"
        assert dto.category == "General"
        assert dto.gradingMode == GradingMode.AUTO
        assert dto.scoringPolicy == "STANDARD"
        assert dto.submissionMode == "DIGITAL"
        assert dto.questions == []
        assert dto.questionGroups == []

    def test_handles_scoring_policy_completion(self):
        """Handles COMPLETION scoring policy."""
        from assignment_templates.services import assignment_template_to_dto

        assignment_template = MagicMock()
        assignment_template.id = 1
        assignment_template.title = "Test"
        assignment_template.category = None
        assignment_template.grading_mode = GradingMode.MANUAL
        assignment_template.scoring_policy = "COMPLETION"
        assignment_template.submission_mode = "DIGITAL"
        assignment_template.status = "ACTIVE"
        assignment_template.rubric_id = None
        assignment_template.questions.all.return_value = []
        assignment_template.question_groups.all.return_value = []

        dto = assignment_template_to_dto(assignment_template)

        assert dto.scoringPolicy == "COMPLETION"
        assert dto.questionGroups == []


# ---------------------------------------------------------------------------
# question_to_dto
# ---------------------------------------------------------------------------


class TestQuestionToDto:
    """Tests for question_to_dto conversion."""

    def test_multiple_choice_question(self):
        """Converts MCQ with choices and selectAll flag."""
        from assignment_templates.services import question_to_dto

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
        from assignment_templates.services import question_to_dto

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
        from assignment_templates.services import question_to_dto

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
        from assignment_templates.services import question_to_dto

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
# create_assignment_template
# ---------------------------------------------------------------------------


class TestCreateAssignmentTemplate(_NoopAtomicMixin):
    """Tests for create_assignment_template service."""

    def test_raises_when_no_grading_mode(self):
        """Raises ValueError when gradingMode is missing."""
        from assignment_templates.services import create_assignment_template

        with pytest.raises(ValueError, match="gradingMode is required"):
            create_assignment_template(SimpleNamespace(id=1), {"title": "T"})

    def test_raises_when_no_title(self):
        """Raises ValueError when title is missing."""
        from assignment_templates.services import create_assignment_template

        with pytest.raises(ValueError, match="title is required"):
            create_assignment_template(
                SimpleNamespace(id=1), {"gradingMode": GradingMode.AUTO}
            )

    @patch("assignment_templates.services._validate_rubric_rules")
    @patch("assignment_templates.services._replace_questions")
    @patch("assignment_templates.services._create_question_groups")
    @patch("assignment_templates.services.AssignmentTemplate")
    def test_creates_standard_assignment_template(
        self, mock_assignment_template_model, mock_create_groups, mock_replace, mock_validate
    ):
        """Creates a standard assignment_template with questions."""
        from assignment_templates.services import create_assignment_template

        fake_assignment_template = SimpleNamespace(id=5)
        mock_assignment_template_model.objects.create.return_value = fake_assignment_template
        mock_create_groups.return_value = {}
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz 1",
            "gradingMode": GradingMode.AUTO,
            "category": "Math",
            "questions": [{"type": "MULTIPLE_CHOICE", "prompt": "Q1"}],
        }

        result = create_assignment_template(user, payload)

        assert result is fake_assignment_template
        mock_assignment_template_model.objects.create.assert_called_once_with(
            title="Quiz 1",
            grading_mode=GradingMode.AUTO,
            scoring_policy="STANDARD",
            submission_mode="DIGITAL",
            created_by_admin=user,
            category="Math",
            rubric_id=None,
        )
        mock_replace.assert_called_once()
        mock_validate.assert_called_once_with(fake_assignment_template)

    @patch("assignment_templates.services._validate_rubric_rules")
    @patch("assignment_templates.services._replace_questions")
    @patch("assignment_templates.services._create_question_groups")
    @patch("assignment_templates.services.AssignmentTemplate")
    def test_defaults_scoring_policy_to_standard(
        self, mock_assignment_template_model, mock_create_groups, mock_replace, mock_validate
    ):
        """Defaults scoringPolicy to STANDARD when not provided."""
        from assignment_templates.services import create_assignment_template

        mock_assignment_template_model.objects.create.return_value = SimpleNamespace(id=1)
        mock_create_groups.return_value = {}
        user = SimpleNamespace(id=1)
        payload = {
            "title": "Quiz",
            "gradingMode": GradingMode.AUTO,
        }

        create_assignment_template(user, payload)

        create_call = mock_assignment_template_model.objects.create.call_args
        assert create_call.kwargs["scoring_policy"] == "STANDARD"


# ---------------------------------------------------------------------------
# update_assignment_template
# ---------------------------------------------------------------------------


class TestUpdateAssignmentTemplate(_NoopAtomicMixin):
    """Tests for update_assignment_template service."""

    def test_raises_when_assignment_template_is_archived(self):
        """Archived assignment templates cannot be updated through the normal edit path."""
        from assignment_templates.services import update_assignment_template

        assignment_template = MagicMock()
        assignment_template.status = "ARCHIVED"

        with pytest.raises(ConflictError, match="archived"):
            update_assignment_template(assignment_template, {"title": "Nope"})

    @patch("assignment_templates.services._validate_rubric_rules")
    @patch("assignment_templates.services._replace_questions")
    @patch("assignment_templates.services._create_question_groups")
    @patch("assignment_templates.services.AssignmentTemplateQuestionGroup")
    @patch("assignment_templates.services.Assignment")
    def test_updates_fields_and_replaces_questions(
        self, mock_assignment, mock_aqg, mock_create_groups, mock_replace, mock_validate
    ):
        """Updates assignment_template fields and replaces all questions."""
        from assignment_templates.services import update_assignment_template

        mock_assignment.objects.filter.return_value.exists.return_value = False
        mock_create_groups.return_value = {}

        assignment_template = MagicMock()
        assignment_template.title = "Old Title"
        assignment_template.category = "Old Cat"
        assignment_template.grading_mode = GradingMode.AUTO
        assignment_template.scoring_policy = "STANDARD"
        assignment_template.rubric_id = None
        assignment_template.used_at = None

        payload = {
            "title": "New Title",
            "category": "New Cat",
            "gradingMode": GradingMode.MANUAL,
            "scoringPolicy": "COMPLETION",
            "questions": [{"type": "SHORT_ANSWER", "prompt": "Q"}],
        }

        result = update_assignment_template(assignment_template, payload)

        assert result.title == "New Title"
        assert result.category == "New Cat"
        assert result.grading_mode == GradingMode.MANUAL
        assert result.scoring_policy == "COMPLETION"
        assert result.rubric_id is None
        assignment_template.save.assert_called_once()
        mock_replace.assert_called_once()
        mock_validate.assert_called_once()

    @patch("assignment_templates.services.Assignment")
    def test_raises_when_assignment_template_was_previously_used(self, mock_assignment):
        """Historically used templates stay read-only even after live assignments are gone."""
        from assignment_templates.services import (
            AssignmentTemplateReferencedError,
            update_assignment_template,
        )

        mock_assignment.objects.filter.return_value.exists.return_value = False

        assignment_template = MagicMock()
        assignment_template.status = "ACTIVE"
        assignment_template.used_at = "2026-04-15T00:00:00Z"

        with pytest.raises(AssignmentTemplateReferencedError, match="used"):
            update_assignment_template(assignment_template, {"title": "Nope"})

    @patch("assignment_templates.services._validate_rubric_rules")
    @patch("assignment_templates.services._replace_questions")
    @patch("assignment_templates.services._create_question_groups")
    @patch("assignment_templates.services.AssignmentTemplateQuestionGroup")
    @patch("assignment_templates.services.Assignment")
    def test_preserves_title_when_not_provided(
        self, mock_assignment, mock_aqg, mock_create_groups, mock_replace, mock_validate
    ):
        """Preserves existing title when not in payload."""
        from assignment_templates.services import update_assignment_template

        mock_assignment.objects.filter.return_value.exists.return_value = False
        mock_create_groups.return_value = {}

        assignment_template = MagicMock()
        assignment_template.title = "Keep Me"
        assignment_template.grading_mode = GradingMode.AUTO
        assignment_template.scoring_policy = "STANDARD"
        assignment_template.rubric_id = None
        assignment_template.used_at = None

        payload = {"category": "New"}

        result = update_assignment_template(assignment_template, payload)

        assert result.title == "Keep Me"


# ---------------------------------------------------------------------------
# delete_assignment_template
# ---------------------------------------------------------------------------


class TestDeleteAssignmentTemplate(_NoopAtomicMixin):
    """Tests for delete_assignment_template service."""

    @patch("assignment_templates.services.Assignment")
    def test_deletes_assignment_template_when_no_assignments(
        self, mock_assignment_model
    ):
        """Deletes an unused assignment_template that has never been used."""
        from assignment_templates.services import delete_assignment_template

        mock_assignment_model.objects.filter.return_value.exists.return_value = False
        assignment_template = MagicMock()
        assignment_template.used_at = None

        delete_assignment_template(assignment_template)

        mock_assignment_model.objects.filter.assert_called_once_with(
            assignment_template=assignment_template
        )
        assignment_template.delete.assert_called_once()

    @patch("assignment_templates.services.Assignment")
    def test_raises_when_assignments_reference(
        self, mock_assignment_model
    ):
        """Raises AssignmentTemplateReferencedError when live assignments still use the assignment_template."""
        from assignment_templates.services import AssignmentTemplateReferencedError, delete_assignment_template

        mock_assignment_model.objects.filter.return_value.exists.return_value = True
        assignment_template = MagicMock()

        with pytest.raises(AssignmentTemplateReferencedError):
            delete_assignment_template(assignment_template)

    @patch("assignment_templates.services.Assignment")
    def test_raises_when_assignment_template_was_previously_used(
        self, mock_assignment_model
    ):
        """Previously used assignment_templates stay archive-first even after assignments are gone."""
        from assignment_templates.services import AssignmentTemplateReferencedError, delete_assignment_template

        mock_assignment_model.objects.filter.return_value.exists.return_value = False
        assignment_template = MagicMock()
        assignment_template.used_at = "2026-04-15T00:00:00Z"

        with pytest.raises(AssignmentTemplateReferencedError, match="used"):
            delete_assignment_template(assignment_template)


# ---------------------------------------------------------------------------
# list_assignment_templates
# ---------------------------------------------------------------------------


class TestListAssignmentTemplates:
    """Tests for list_assignment_templates service."""

    @patch("assignment_templates.services.AssignmentTemplate")
    def test_returns_active_assignment_templates_by_default(self, mock_assignment_template_model):
        """Returns list of active assignment_templates by default."""
        from assignment_templates.services import list_assignment_templates

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        qs = MagicMock()
        mock_assignment_template_model.objects.all.return_value = qs
        # Chain: .filter().prefetch_related() -> iterable that yields sentinel
        qs.filter.return_value.prefetch_related.return_value = sentinel

        result = list_assignment_templates()

        assert result == sentinel
        qs.filter.assert_called_once()

    @patch("assignment_templates.services.AssignmentTemplate")
    def test_returns_all_when_include_archived(self, mock_assignment_template_model):
        """Returns ACTIVE + ARCHIVED assignment_templates when include_archived=True."""
        from assignment_templates.services import list_assignment_templates

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        qs = MagicMock()
        mock_assignment_template_model.objects.all.return_value = qs
        # Chain: .filter().prefetch_related() -> iterable that yields sentinel
        qs.filter.return_value.prefetch_related.return_value = sentinel

        result = list_assignment_templates(include_archived=True)

        assert result == sentinel
        qs.filter.assert_called_once()

    @patch("assignment_templates.services.AssignmentTemplate")
    def test_returns_all_statuses_when_both_flags_set(self, mock_assignment_template_model):
        """Returns all assignment_templates (including drafts and archived) when both flags set."""
        from assignment_templates.services import list_assignment_templates

        sentinel = [SimpleNamespace(id=1)]
        qs = MagicMock()
        mock_assignment_template_model.objects.all.return_value = qs
        qs.prefetch_related.return_value = sentinel

        result = list_assignment_templates(include_archived=True, include_drafts=True)

        assert result == sentinel


# ---------------------------------------------------------------------------
# _replace_questions
# ---------------------------------------------------------------------------


class TestReplaceQuestions:
    """Tests for _replace_questions internal helper."""

    @patch("assignment_templates.services._create_question")
    @patch("assignment_templates.services.Question")
    def test_deletes_existing_and_creates_new(
        self, mock_question_model, mock_create_question
    ):
        """Deletes all existing questions and creates new ones."""
        from assignment_templates.services import _replace_questions

        assignment_template = SimpleNamespace(id=1)
        questions = [
            {"type": "SHORT_ANSWER", "prompt": "Q1"},
            {"type": "SHORT_ANSWER", "prompt": "Q2"},
        ]

        _replace_questions(assignment_template, questions)

        mock_question_model.objects.filter.assert_called_once_with(
            assignment_template=assignment_template
        )
        mock_question_model.objects.filter.return_value.delete.assert_called_once()
        assert mock_create_question.call_count == 2

    @patch("assignment_templates.services._create_question")
    @patch("assignment_templates.services.Question")
    def test_handles_empty_questions_list(
        self, mock_question_model, mock_create_question
    ):
        """Handles empty question list without errors."""
        from assignment_templates.services import _replace_questions

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
        from assignment_templates.services import _create_question

        with pytest.raises(ValueError, match="Question type is required"):
            _create_question(SimpleNamespace(id=1), {"prompt": "Q"}, {})

    def test_raises_when_no_prompt(self):
        """Raises ValueError when prompt is missing."""
        from assignment_templates.services import _create_question

        with pytest.raises(ValueError, match="Question prompt is required"):
            _create_question(
                SimpleNamespace(id=1), {"type": QuestionKind.SHORT_ANSWER}, {}
            )

    @patch("assignment_templates.services.MultipleChoiceQuestion")
    @patch("assignment_templates.services.McqChoice")
    @patch("assignment_templates.services.Question")
    def test_creates_multiple_choice_with_choices(
        self, mock_q_model, mock_choice_model, mock_mcq_model
    ):
        """Creates MCQ question with choices."""
        from assignment_templates.services import _create_question

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
        create_call = mock_q_model.objects.create.call_args
        assert create_call.kwargs["max_points"] == 5.0
        mock_mcq_model.objects.create.assert_called_once_with(
            question=fake_question, select_all=True
        )
        assert mock_choice_model.objects.create.call_count == 2

    @patch("assignment_templates.services.MultipleChoiceQuestion")
    @patch("assignment_templates.services.McqChoice")
    @patch("assignment_templates.services.Question")
    def test_single_select_mcq_uses_highest_choice_value_for_max_points(
        self, mock_q_model, mock_choice_model, mock_mcq_model
    ):
        """Single-select MCQs derive question max points from the highest choice value."""
        from assignment_templates.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        _create_question(
            SimpleNamespace(id=1),
            {
                "type": QuestionKind.MULTIPLE_CHOICE,
                "prompt": "Pick one",
                "maxPoints": 100,
                "data": {
                    "selectAll": False,
                    "choices": [
                        {"prompt": "A", "score": 1},
                        {"prompt": "B", "score": 4},
                        {"prompt": "C", "score": 2},
                    ],
                },
            },
            {},
        )

        create_call = mock_q_model.objects.create.call_args
        assert create_call.kwargs["max_points"] == 4.0

    @patch("assignment_templates.services.ShortAnswerQuestion")
    @patch("assignment_templates.services.Question")
    def test_creates_short_answer(self, mock_q_model, mock_sa_model):
        """Creates short answer question with settings."""
        from assignment_templates.services import _create_question

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

    @patch("assignment_templates.services.NumberScaleQuestion")
    @patch("assignment_templates.services.Question")
    def test_creates_number_scale(self, mock_q_model, mock_ns_model):
        """Creates number scale question."""
        from assignment_templates.services import _create_question

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

    @patch("assignment_templates.services.NumberScaleQuestion")
    @patch("assignment_templates.services.Question")
    def test_number_scale_raises_when_missing_min_max(
        self, mock_q_model, mock_ns_model
    ):
        """Raises ValueError when min or max is missing for number scale."""
        from assignment_templates.services import _create_question

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

    @patch("assignment_templates.services.NumberScaleQuestion")
    @patch("assignment_templates.services.Question")
    def test_number_scale_swaps_min_max_when_inverted(
        self, mock_q_model, mock_ns_model
    ):
        """Swaps min and max when min > max."""
        from assignment_templates.services import _create_question

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

    @patch("assignment_templates.services.Question")
    def test_auto_gradable_set_for_mcq_and_number_scale(self, mock_q_model):
        """auto_gradable is set to True for MCQ and NUMBER_SCALE."""
        from assignment_templates.services import _create_question

        mock_q_model.objects.create.return_value = SimpleNamespace(id=10)

        # We need to also mock the MCQ creation
        with patch("assignment_templates.services.MultipleChoiceQuestion"):
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

    @patch("assignment_templates.services.ShortAnswerQuestion")
    @patch("assignment_templates.services.Question")
    def test_auto_gradable_false_for_short_answer(
        self, mock_q_model, mock_sa_model
    ):
        """auto_gradable is False for SHORT_ANSWER."""
        from assignment_templates.services import _create_question

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



# ---------------------------------------------------------------------------
# archive_assignment_template / restore_assignment_template / purge_assignment_template
# ---------------------------------------------------------------------------


class TestArchiveAssignmentTemplate(_NoopAtomicMixin):
    """Tests for archive_assignment_template service."""

    @patch("assignment_templates.services.timezone")
    def test_archives_active_assignment_template(self, mock_tz):
        """Archives an active assignment_template and sets status to ARCHIVED."""
        from assignment_templates.services import archive_assignment_template

        mock_tz.now.return_value = "2025-01-01"
        assignment_template = MagicMock()
        assignment_template.status = "ACTIVE"
        user = SimpleNamespace(id=1)

        result = archive_assignment_template(user, assignment_template)

        assert result.status == "ARCHIVED"
        assignment_template.save.assert_called_once()

    def test_raises_when_already_archived(self):
        """Raises ConflictError when assignment_template is already archived."""
        from assignment_templates.services import archive_assignment_template
        from assignment_templates.models import AssignmentTemplateStatus
        from core.lifecycle import ConflictError

        assignment_template = MagicMock()
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED

        with pytest.raises(ConflictError, match="already archived"):
            archive_assignment_template(SimpleNamespace(id=1), assignment_template)

    def test_raises_when_assignment_template_is_draft(self):
        """Draft assignment templates cannot move straight to archived state."""
        from assignment_templates.services import archive_assignment_template
        from assignment_templates.models import AssignmentTemplateStatus
        from core.lifecycle import ConflictError

        assignment_template = MagicMock()
        assignment_template.status = AssignmentTemplateStatus.DRAFT

        with pytest.raises(ConflictError, match="Draft"):
            archive_assignment_template(SimpleNamespace(id=1), assignment_template)


class TestRestoreAssignmentTemplate(_NoopAtomicMixin):
    """Tests for restore_assignment_template service."""

    @patch("assignment_templates.services.timezone")
    def test_restores_archived_assignment_template(self, mock_tz):
        """Restores an archived assignment_template back to ACTIVE status."""
        from assignment_templates.services import restore_assignment_template
        from assignment_templates.models import AssignmentTemplateStatus

        mock_tz.now.return_value = "2025-06-01"
        assignment_template = MagicMock()
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        user = SimpleNamespace(id=1)

        result = restore_assignment_template(user, assignment_template)

        assert result.status == "ACTIVE"
        assert result.archived_at is None

    def test_raises_when_not_archived(self):
        """Raises ConflictError when restoring an assignment_template that is not archived."""
        from assignment_templates.services import restore_assignment_template
        from core.lifecycle import ConflictError

        assignment_template = MagicMock()
        assignment_template.status = "ACTIVE"

        with pytest.raises(ConflictError, match="not archived"):
            restore_assignment_template(SimpleNamespace(id=1), assignment_template)


class TestPurgeAssignmentTemplate(_NoopAtomicMixin):
    """Tests for purge_assignment_template service."""

    def test_raises_when_not_archived(self):
        """Raises ConflictError when purging an assignment_template that is not archived."""
        from assignment_templates.services import purge_assignment_template
        from core.lifecycle import ConflictError

        assignment_template = MagicMock()
        assignment_template.status = "ACTIVE"

        with pytest.raises(ConflictError, match="Only archived"):
            purge_assignment_template(assignment_template)

    @patch("assignment_templates.services.Assignment")
    def test_raises_when_has_assignments(self, mock_assignment):
        """Raises ConflictError when archived assignment_template still has live assignment dependents."""
        from assignment_templates.services import purge_assignment_template
        from assignment_templates.models import AssignmentTemplateStatus
        from core.lifecycle import ConflictError

        assignment_template = MagicMock()
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        mock_assignment.objects.filter.return_value.exists.return_value = True

        with pytest.raises(ConflictError, match="associated assignments"):
            purge_assignment_template(assignment_template)

    @patch("assignment_templates.services.Assignment")
    def test_purges_successfully(self, mock_assignment):
        """Permanently deletes an archived assignment_template with no assignments."""
        from assignment_templates.services import purge_assignment_template
        from assignment_templates.models import AssignmentTemplateStatus

        assignment_template = MagicMock()
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        mock_assignment.objects.filter.return_value.exists.return_value = False

        purge_assignment_template(assignment_template)

        assignment_template.delete.assert_called_once()


# ---------------------------------------------------------------------------
# _validate_rubric_rules
# ---------------------------------------------------------------------------


class TestValidateRubricRules:
    """Tests for _validate_rubric_rules helper."""

    def test_auto_mode_rejects_rubric(self):
        """Raises ValueError when AUTO mode question has a rubric attached."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = GradingMode.AUTO
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = 1
        q.question_group = None
        q.grading_strategy = "AUTO"
        assignment_template.questions.all.return_value = [q]

        with pytest.raises(ValueError, match="AUTO mode does not allow"):
            _validate_rubric_rules(assignment_template)

    def test_manual_mode_requires_rubric(self):
        """Raises ValueError when MANUAL mode question lacks a rubric."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "MANUAL"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = None
        q.question_group = None
        q.grading_strategy = "MANUAL"
        q.prompt = "Test question prompt"
        assignment_template.questions.all.return_value = [q]

        with pytest.raises(ValueError, match="must have a rubric"):
            _validate_rubric_rules(assignment_template)

    def test_manual_mode_accepts_rubric(self):
        """Passes validation when MANUAL mode question has a rubric."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "MANUAL"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = 1
        q.question_group = None
        q.grading_strategy = "MANUAL"
        assignment_template.questions.all.return_value = [q]

        _validate_rubric_rules(assignment_template)  # should not raise

    def test_hybrid_manual_strategy_requires_rubric(self):
        """Raises ValueError when HYBRID question with MANUAL strategy lacks a rubric."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "HYBRID"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = None
        q.question_group = None
        q.grading_strategy = "MANUAL"
        q.prompt = "Test question"
        assignment_template.questions.all.return_value = [q]

        with pytest.raises(ValueError, match="MANUAL strategy must have a rubric"):
            _validate_rubric_rules(assignment_template)

    def test_hybrid_auto_strategy_rejects_rubric(self):
        """Raises ValueError when HYBRID question with AUTO strategy has a rubric."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "HYBRID"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = 1
        q.question_group = None
        q.grading_strategy = "AUTO"
        q.prompt = "Test question"
        assignment_template.questions.all.return_value = [q]

        with pytest.raises(ValueError, match="AUTO strategy must not have a rubric"):
            _validate_rubric_rules(assignment_template)

    def test_hybrid_auto_strategy_accepts_no_rubric(self):
        """Passes validation when HYBRID question with AUTO strategy has no rubric."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "HYBRID"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = None
        q.question_group = None
        q.grading_strategy = "AUTO"
        assignment_template.questions.all.return_value = [q]

        _validate_rubric_rules(assignment_template)  # should not raise

    def test_group_rubric_counts_as_has_rubric(self):
        """Treats a rubric on the question group as satisfying the rubric requirement."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "MANUAL"
        assignment_template.rubric_id = None
        q = MagicMock()
        q.rubric_id = None
        q.question_group = MagicMock(rubric_id=5)
        q.grading_strategy = "MANUAL"
        assignment_template.questions.all.return_value = [q]

        _validate_rubric_rules(assignment_template)  # should not raise (group rubric)

    def test_assignment_template_rubric_counts_as_has_rubric(self):
        """Treats an assignment_template-level rubric as satisfying the rubric requirement."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "MANUAL"
        assignment_template.rubric_id = 7
        q = MagicMock()
        q.rubric_id = None
        q.question_group = None
        q.grading_strategy = "MANUAL"
        assignment_template.questions.all.return_value = [q]

        _validate_rubric_rules(assignment_template)

    def test_rejects_mixed_assignment_template_and_specific_rubrics(self):
        """AssignmentTemplate-level rubrics cannot be combined with question/group rubrics."""
        from assignment_templates.services import _validate_rubric_rules

        assignment_template = MagicMock()
        assignment_template.grading_mode = "MANUAL"
        assignment_template.rubric_id = 7
        q = MagicMock()
        q.rubric_id = 9
        q.question_group = None
        q.grading_strategy = "MANUAL"
        assignment_template.questions.all.return_value = [q]

        with pytest.raises(
            ValueError,
            match="Assignment template rubric cannot be combined with question or group rubrics",
        ):
            _validate_rubric_rules(assignment_template)
