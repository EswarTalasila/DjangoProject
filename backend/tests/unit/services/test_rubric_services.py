"""Pure unit tests for rubrics.services (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper: neutralise @transaction.atomic
# ---------------------------------------------------------------------------

class _NoopAtomicMixin:
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
# rubric_to_dto
# ---------------------------------------------------------------------------

class TestRubricToDto:
    """Tests for rubric_to_dto conversion."""

    def test_converts_rubric_with_no_criteria(self):
        """Converts a rubric with no criteria to a DTO with empty criteria list."""
        from rubrics.services import rubric_to_dto

        rubric = MagicMock()
        rubric.id = 1
        rubric.title = "My Rubric"
        rubric.description = "desc"
        rubric.status = "ACTIVE"
        rubric.created_by_id = 42
        rubric.created_at = "2025-01-01T00:00:00Z"
        rubric.updated_at = "2025-01-02T00:00:00Z"
        rubric.criteria.all.return_value.order_by.return_value = []

        dto = rubric_to_dto(rubric)

        assert dto.id == 1
        assert dto.title == "My Rubric"
        assert dto.description == "desc"
        assert dto.status == "ACTIVE"
        assert dto.createdBy == 42
        assert dto.criteria == []

    def test_converts_rubric_with_criteria_and_levels(self):
        """Converts a rubric with nested criteria and levels to a complete DTO."""
        from rubrics.services import rubric_to_dto

        level = MagicMock()
        level.id = 100
        level.label = "Excellent"
        level.points = 5.0
        level.description = "Great work"
        level.order_index = 0

        criterion = MagicMock()
        criterion.id = 10
        criterion.title = "Quality"
        criterion.description = "Work quality"
        criterion.order_index = 0
        criterion.weight = 1.0
        criterion.levels.all.return_value.order_by.return_value = [level]

        rubric = MagicMock()
        rubric.id = 1
        rubric.title = "Rubric"
        rubric.description = ""
        rubric.status = "ACTIVE"
        rubric.created_by_id = 1
        rubric.created_at = "2025-01-01"
        rubric.updated_at = "2025-01-01"
        rubric.criteria.all.return_value.order_by.return_value = [criterion]

        dto = rubric_to_dto(rubric)

        assert len(dto.criteria) == 1
        assert dto.criteria[0].title == "Quality"
        assert len(dto.criteria[0].levels) == 1
        assert dto.criteria[0].levels[0].label == "Excellent"
        assert dto.criteria[0].levels[0].points == 5.0


# ---------------------------------------------------------------------------
# list_rubrics
# ---------------------------------------------------------------------------

class TestListRubrics:

    @patch("rubrics.services.Rubric")
    def test_returns_all_rubrics(self, mock_rubric_model):
        """Returns all rubrics from the database."""
        from rubrics.services import list_rubrics

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_rubric_model.objects.prefetch_related.return_value.all.return_value = sentinel

        result = list_rubrics()

        assert result == sentinel


# ---------------------------------------------------------------------------
# create_rubric
# ---------------------------------------------------------------------------

class TestCreateRubric(_NoopAtomicMixin):

    def test_raises_when_no_title(self):
        """Raises ValueError when title key is missing from payload."""
        from rubrics.services import create_rubric

        with pytest.raises(ValueError, match="title is required"):
            create_rubric(SimpleNamespace(id=1), {"description": "d"})

    def test_raises_when_empty_title(self):
        """Raises ValueError when title is an empty string."""
        from rubrics.services import create_rubric

        with pytest.raises(ValueError, match="title is required"):
            create_rubric(SimpleNamespace(id=1), {"title": ""})

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services.Rubric")
    def test_creates_rubric_with_title_and_description(
        self, mock_rubric_model, mock_replace
    ):
        """Creates a rubric with valid title and description fields."""
        from rubrics.services import create_rubric

        fake_rubric = SimpleNamespace(id=5)
        mock_rubric_model.objects.create.return_value = fake_rubric
        user = SimpleNamespace(id=1)

        result = create_rubric(user, {"title": "Test", "description": "D"})

        assert result is fake_rubric
        mock_rubric_model.objects.create.assert_called_once_with(
            title="Test", description="D", created_by=user
        )
        mock_replace.assert_called_once_with(fake_rubric, [])

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services.Rubric")
    def test_creates_rubric_with_criteria(
        self, mock_rubric_model, mock_replace
    ):
        """Passes criteria list to _replace_criteria when provided."""
        from rubrics.services import create_rubric

        fake_rubric = SimpleNamespace(id=5)
        mock_rubric_model.objects.create.return_value = fake_rubric
        criteria = [{"title": "C1"}]

        create_rubric(SimpleNamespace(id=1), {"title": "T", "criteria": criteria})

        mock_replace.assert_called_once_with(fake_rubric, criteria)

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services.Rubric")
    def test_defaults_description_to_empty(self, mock_rubric_model, mock_replace):
        """Defaults description to empty string when not provided."""
        from rubrics.services import create_rubric

        mock_rubric_model.objects.create.return_value = SimpleNamespace(id=1)

        create_rubric(SimpleNamespace(id=1), {"title": "T"})

        create_call = mock_rubric_model.objects.create.call_args
        assert create_call.kwargs["description"] == ""


# ---------------------------------------------------------------------------
# update_rubric
# ---------------------------------------------------------------------------

class TestUpdateRubric(_NoopAtomicMixin):

    @patch("rubrics.services._is_referenced", return_value=True)
    def test_raises_when_referenced(self, mock_ref):
        """Raises RubricReferencedError when rubric is in use by an assessment."""
        from rubrics.services import RubricReferencedError, update_rubric

        rubric = MagicMock()
        with pytest.raises(RubricReferencedError):
            update_rubric(rubric, {"title": "New"})

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services._is_referenced", return_value=False)
    def test_updates_title_and_description(self, mock_ref, mock_replace):
        """Updates title and description fields on an unreferenced rubric."""
        from rubrics.services import update_rubric

        rubric = MagicMock()
        rubric.title = "Old"
        rubric.description = "Old desc"

        result = update_rubric(rubric, {"title": "New", "description": "New desc"})

        assert result.title == "New"
        assert result.description == "New desc"
        rubric.save.assert_called_once()

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services._is_referenced", return_value=False)
    def test_replaces_criteria_when_in_payload(self, mock_ref, mock_replace):
        """Replaces criteria when criteria key is present in the payload."""
        from rubrics.services import update_rubric

        rubric = MagicMock()
        rubric.title = "T"
        rubric.description = "D"
        criteria = [{"title": "C1"}]

        update_rubric(rubric, {"criteria": criteria})

        mock_replace.assert_called_once_with(rubric, criteria)

    @patch("rubrics.services._replace_criteria")
    @patch("rubrics.services._is_referenced", return_value=False)
    def test_does_not_replace_criteria_when_not_in_payload(self, mock_ref, mock_replace):
        """Skips criteria replacement when criteria key is absent from payload."""
        from rubrics.services import update_rubric

        rubric = MagicMock()
        rubric.title = "T"
        rubric.description = "D"

        update_rubric(rubric, {"title": "New Title"})

        mock_replace.assert_not_called()

    @patch("rubrics.services._is_referenced", return_value=False)
    def test_preserves_title_when_not_in_payload(self, mock_ref):
        """Preserves existing title when title key is absent from payload."""
        from rubrics.services import update_rubric

        rubric = MagicMock()
        rubric.title = "Keep"
        rubric.description = "D"

        result = update_rubric(rubric, {"description": "New D"})

        assert result.title == "Keep"


# ---------------------------------------------------------------------------
# delete_rubric
# ---------------------------------------------------------------------------

class TestDeleteRubric(_NoopAtomicMixin):

    @patch("rubrics.services._is_referenced", return_value=False)
    def test_deletes_when_not_referenced(self, mock_ref):
        """Deletes an unreferenced rubric successfully."""
        from rubrics.services import delete_rubric

        rubric = MagicMock()
        delete_rubric(rubric)
        rubric.delete.assert_called_once()

    @patch("rubrics.services._is_referenced", return_value=True)
    def test_raises_when_referenced(self, mock_ref):
        """Raises RubricReferencedError when deleting a referenced rubric."""
        from rubrics.services import RubricReferencedError, delete_rubric

        with pytest.raises(RubricReferencedError):
            delete_rubric(MagicMock())


# ---------------------------------------------------------------------------
# archive_rubric
# ---------------------------------------------------------------------------

class TestArchiveRubric(_NoopAtomicMixin):

    def test_archives_active_rubric(self):
        """Sets an active rubric status to archived."""
        from rubrics.services import archive_rubric

        rubric = MagicMock()
        rubric.status = "ACTIVE"

        result = archive_rubric(rubric)

        assert result.status == "ARCHIVED"
        rubric.save.assert_called_once_with(update_fields=["status"])

    def test_raises_when_already_archived(self):
        """Raises ValueError when archiving an already-archived rubric."""
        from rubrics.services import archive_rubric
        from rubrics.models import RubricStatus

        rubric = MagicMock()
        rubric.status = RubricStatus.ARCHIVED

        with pytest.raises(ValueError, match="already archived"):
            archive_rubric(rubric)


# ---------------------------------------------------------------------------
# _is_referenced
# ---------------------------------------------------------------------------

class TestIsReferenced:

    @patch("assessments.models.AssessmentQuestionGroup")
    @patch("assessments.models.Question")
    def test_returns_true_when_question_references(self, mock_q, mock_aqg):
        """Returns true when a question references the rubric."""
        from rubrics.services import _is_referenced

        mock_q.objects.filter.return_value.exists.return_value = True
        rubric = MagicMock()

        assert _is_referenced(rubric) is True

    @patch("assessments.models.AssessmentQuestionGroup")
    @patch("assessments.models.Question")
    def test_returns_true_when_group_references(self, mock_q, mock_aqg):
        """Returns true when an assessment question group references the rubric."""
        from rubrics.services import _is_referenced

        mock_q.objects.filter.return_value.exists.return_value = False
        mock_aqg.objects.filter.return_value.exists.return_value = True
        rubric = MagicMock()

        assert _is_referenced(rubric) is True

    @patch("assessments.models.AssessmentQuestionGroup")
    @patch("assessments.models.Question")
    def test_returns_false_when_not_referenced(self, mock_q, mock_aqg):
        """Returns false when no questions or groups reference the rubric."""
        from rubrics.services import _is_referenced

        mock_q.objects.filter.return_value.exists.return_value = False
        mock_aqg.objects.filter.return_value.exists.return_value = False
        rubric = MagicMock()

        assert _is_referenced(rubric) is False


# ---------------------------------------------------------------------------
# _replace_criteria
# ---------------------------------------------------------------------------

class TestReplaceCriteria:

    @patch("rubrics.services.RubricLevel")
    @patch("rubrics.services.RubricCriterion")
    def test_deletes_existing_and_creates_new(self, mock_crit, mock_level):
        """Deletes existing criteria and creates new ones with levels."""
        from rubrics.services import _replace_criteria

        fake_criterion = SimpleNamespace(id=10)
        mock_crit.objects.create.return_value = fake_criterion
        rubric = MagicMock()

        criteria = [{
            "title": "C1",
            "description": "D",
            "orderIndex": 0,
            "weight": 2.0,
            "levels": [{"label": "Good", "points": 3, "description": "ok", "orderIndex": 0}],
        }]

        _replace_criteria(rubric, criteria)

        mock_crit.objects.filter.assert_called_once_with(rubric=rubric)
        mock_crit.objects.filter.return_value.delete.assert_called_once()
        mock_crit.objects.create.assert_called_once()
        mock_level.objects.create.assert_called_once()

    @patch("rubrics.services.RubricCriterion")
    def test_raises_when_criterion_missing_title(self, mock_crit):
        """Raises ValueError when a criterion is missing its title."""
        from rubrics.services import _replace_criteria

        rubric = MagicMock()
        with pytest.raises(ValueError, match="requires a title"):
            _replace_criteria(rubric, [{"description": "no title"}])

    @patch("rubrics.services.RubricLevel")
    @patch("rubrics.services.RubricCriterion")
    def test_raises_when_level_missing_label(self, mock_crit, mock_level):
        """Raises ValueError when a level is missing its label."""
        from rubrics.services import _replace_criteria

        mock_crit.objects.create.return_value = SimpleNamespace(id=10)
        rubric = MagicMock()

        with pytest.raises(ValueError, match="requires a label"):
            _replace_criteria(rubric, [{"title": "C1", "levels": [{"points": 5}]}])

    @patch("rubrics.services.RubricCriterion")
    def test_handles_empty_criteria(self, mock_crit):
        """Deletes existing criteria without creating new ones when list is empty."""
        from rubrics.services import _replace_criteria

        rubric = MagicMock()
        _replace_criteria(rubric, [])

        mock_crit.objects.filter.return_value.delete.assert_called_once()
        mock_crit.objects.create.assert_not_called()

    @patch("rubrics.services.RubricLevel")
    @patch("rubrics.services.RubricCriterion")
    def test_defaults_order_index_and_weight(self, mock_crit, mock_level):
        """Defaults order_index to 0 and weight to 1.0 when not specified."""
        from rubrics.services import _replace_criteria

        mock_crit.objects.create.return_value = SimpleNamespace(id=10)
        rubric = MagicMock()

        _replace_criteria(rubric, [{"title": "C1"}])

        create_call = mock_crit.objects.create.call_args
        assert create_call.kwargs["order_index"] == 0
        assert create_call.kwargs["weight"] == 1.0
