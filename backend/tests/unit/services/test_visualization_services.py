"""Unit tests for visualizations.services business logic.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from submissions.models import AnswerType, SubmissionStatus

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_submission(
    *,
    id=1,
    assignment_id=10,
    student_id=100,
    teacher_id=None,
    submitted_at=None,
    score=80.0,
    status=SubmissionStatus.GRADED,
    assignment=None,
):
    """Build a lightweight mock Submission for visualization tests."""
    sub = MagicMock()
    sub.id = id
    sub.assignment_id = assignment_id
    sub.student_id = student_id
    sub.teacher_id = teacher_id
    sub.submitted_at = submitted_at
    sub.score = score
    sub.status = status
    if assignment is None:
        assignment = MagicMock()
        assignment.course_id = 50
        assignment.course.name = "Test Course"
        assignment.assessment = MagicMock()
        assignment.assessment.title = "Test Assessment"
        assignment.assessment.category = "General"
    sub.assignment = assignment
    sub.answers = MagicMock()
    sub.answers.all.return_value = []
    return sub


# ============================================================================
# submission_to_visualization
# ============================================================================


class TestSubmissionToVisualization:
    """Tests for the submission_to_visualization DTO converter."""

    def test_maps_all_fields(self):
        """All DTO fields are populated from the submission and its relations."""
        from visualizations.services import submission_to_visualization

        sub = _mock_submission(
            id=42,
            assignment_id=7,
            student_id=99,
            teacher_id=None,
            score=90.0,
            status=SubmissionStatus.GRADED,
        )

        dto = submission_to_visualization(sub)

        assert dto.id == 42
        assert dto.assignmentId == 7
        assert dto.studentId == 99
        assert dto.score == 90.0
        assert dto.courseId == 50
        assert dto.courseName == "Test Course"
        assert dto.assessmentTitle == "Test Assessment"
        assert dto.assessmentCategory == "General"

    def test_handles_no_assignment(self):
        """Gracefully handles submission where assignment is None."""
        from visualizations.services import submission_to_visualization

        sub = _mock_submission()
        sub.assignment = None

        dto = submission_to_visualization(sub)

        assert dto.courseId is None
        assert dto.courseName is None
        assert dto.assessmentTitle is None
        assert dto.assessmentCategory is None

    def test_handles_no_course(self):
        """Gracefully handles assignment with no course."""
        from visualizations.services import submission_to_visualization

        assignment = MagicMock()
        assignment.course_id = None
        assignment.course = None
        assignment.assessment = MagicMock()
        assignment.assessment.title = "Title"
        assignment.assessment.category = "Cat"

        sub = _mock_submission(assignment=assignment)

        dto = submission_to_visualization(sub)

        assert dto.courseId is None
        assert dto.courseName is None
        assert dto.assessmentTitle == "Title"

    def test_handles_no_assessment(self):
        """Gracefully handles assignment with no assessment."""
        from visualizations.services import submission_to_visualization

        assignment = MagicMock()
        assignment.course_id = 5
        assignment.course.name = "Course A"
        assignment.assessment = None

        sub = _mock_submission(assignment=assignment)

        dto = submission_to_visualization(sub)

        assert dto.assessmentTitle is None
        assert dto.assessmentCategory is None

    def test_includes_answer_dtos(self):
        """Answer DTOs are generated for each answer in the submission."""
        from visualizations.services import submission_to_visualization

        ans = MagicMock()
        ans.answer_type = AnswerType.SHORT_ANSWER
        ans.question_id = 5
        ans.score = 3.0
        ans.short_answer = SimpleNamespace(text="hello")

        sub = _mock_submission()
        sub.answers.all.return_value = [ans]

        dto = submission_to_visualization(sub)

        assert len(dto.answers) == 1
        assert dto.answers[0].questionId == 5


# ============================================================================
# _get_mood_meter_assessment_id
# ============================================================================


class TestGetMoodMeterAssessmentId:
    """Tests for the mood meter assessment ID lookup."""

    @patch("visualizations.services.Assessment")
    def test_returns_id_when_found(self, mock_assess):
        """Returns the assessment ID when a MOOD_METER assessment exists."""
        from visualizations.services import _get_mood_meter_assessment_id

        mock_assess.objects.filter.return_value.values_list.return_value.first.return_value = 42

        result = _get_mood_meter_assessment_id()
        assert result == 42

    @patch("visualizations.services.Assessment")
    def test_returns_none_when_not_found(self, mock_assess):
        """Returns None when no MOOD_METER assessment exists."""
        from visualizations.services import _get_mood_meter_assessment_id

        mock_assess.objects.filter.return_value.values_list.return_value.first.return_value = None

        result = _get_mood_meter_assessment_id()
        assert result is None


# ============================================================================
# get_visualization_data
# ============================================================================


class TestGetVisualizationData:
    """Tests for the main visualization query builder."""

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_no_filters_returns_all_graded(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """With no filters and no mood meter assessment, returns all graded submissions."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = None

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = [_mock_submission()]
        mock_to_viz.return_value = MagicMock()

        result = get_visualization_data({}, MagicMock())

        assert len(result) == 1

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_student_filter(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """studentId filter is applied to the queryset."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = None

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"studentId": 100}, MagicMock())

        qs.filter.assert_any_call(student_id=100)

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_course_filter(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """courseId filter is applied to the queryset."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = None

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"courseId": 50}, MagicMock())

        qs.filter.assert_any_call(assignment__course_id=50)

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_category_filter(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """category filter is applied to the queryset."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = None

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"category": "Science"}, MagicMock())

        qs.filter.assert_any_call(assignment__assessment__category="Science")

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_assessment_filter(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """assessmentId filter is applied to the queryset."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = None

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"assessmentId": 20}, MagicMock())

        qs.filter.assert_any_call(assignment__assessment_id=20)

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_excludes_mood_meter_from_general_query(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """MOOD_METER submissions are excluded when filtering by studentId and not by mood meter ID."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = 99  # mood meter assessment has id=99

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.exclude.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"studentId": 100}, MagicMock())

        qs.exclude.assert_called_with(assignment__assessment_id=99)

    @patch("visualizations.services.submission_to_visualization")
    @patch("visualizations.services._get_mood_meter_assessment_id")
    @patch("visualizations.services.Submission")
    def test_does_not_exclude_mood_meter_when_filtered_to_it(self, mock_sub_model, mock_mood_id, mock_to_viz):
        """MOOD_METER submissions are included when assessmentId matches the mood meter."""
        from visualizations.services import get_visualization_data

        mock_mood_id.return_value = 99

        qs = MagicMock()
        mock_sub_model.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = []

        get_visualization_data({"assessmentId": 99}, MagicMock())

        qs.exclude.assert_not_called()
