"""Unit tests for visualizations.services business logic.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_course(*, id=1, name="Test Course", teacher_profile=None):
    """Build a lightweight mock Course."""
    course = MagicMock()
    course.id = id
    course.name = name
    course.teacher_profile = teacher_profile
    return course


def _make_assignment(*, id=10, course=None, assessment=None):
    """Build a lightweight mock Assignment."""
    asgn = MagicMock()
    asgn.id = id
    asgn.course = course or _make_course()
    asgn.assessment = assessment or MagicMock(title="Test Assessment", category="General")
    return asgn


def _make_user(*, is_staff=False, is_researcher=False, has_viz_perm=True):
    """Build a mock user."""
    user = MagicMock()
    user.is_staff = is_staff
    return user


# ============================================================================
# dashboard_overview
# ============================================================================


class TestDashboardOverview:
    """Tests for the dashboard_overview aggregate function."""

    @patch("visualizations.services.Submission")
    @patch("visualizations.services.Assignment")
    @patch("visualizations.services.Enrollment")
    @patch("visualizations.services.Course")
    def test_returns_generated_at_and_courses(
        self, mock_course, mock_enrollment, mock_assignment, mock_submission
    ):
        """Returns a dict with generatedAt and courses list."""
        from visualizations.services import dashboard_overview

        user = MagicMock()
        user.is_staff = True

        # Setup course queryset chain
        qs = MagicMock()
        mock_course.objects.all.return_value.select_related.return_value = qs
        qs.annotate.return_value = []  # no courses

        result = dashboard_overview(user)

        assert "generatedAt" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    @patch("visualizations.services.Submission")
    @patch("visualizations.services.Assignment")
    @patch("visualizations.services.Enrollment")
    @patch("visualizations.services.Course")
    def test_admin_sees_all_courses(
        self, mock_course, mock_enrollment, mock_assignment, mock_submission
    ):
        """Admin user queries all courses."""
        from visualizations.services import dashboard_overview

        user = MagicMock()
        user.is_staff = True

        qs = MagicMock()
        mock_course.objects.all.return_value.select_related.return_value = qs
        qs.annotate.return_value = []

        dashboard_overview(user)

        mock_course.objects.all.assert_called_once()


# ============================================================================
# course_summary
# ============================================================================


class TestCourseSummary:
    """Tests for the course_summary aggregate function."""

    @patch("visualizations.services.Submission")
    @patch("visualizations.services.Enrollment")
    def test_returns_structure_with_assignments(self, mock_enrollment, mock_submission):
        """Returns proper structure with enrolledCount and assignments."""
        from visualizations.services import course_summary

        user = MagicMock()
        user.is_staff = True

        mock_enrollment.objects.filter.return_value.count.return_value = 5

        course = MagicMock()
        course.id = 1
        course.name = "Course A"
        course.assignments.select_related.return_value.annotate.return_value = []

        result = course_summary(user, course)

        assert "generatedAt" in result
        assert "enrolledCount" in result
        assert result["enrolledCount"] == 5
        assert "assignments" in result
        assert result["courseId"] == 1
        assert result["courseName"] == "Course A"

    @patch("visualizations.services.Submission")
    @patch("visualizations.services.Enrollment")
    def test_filters_by_category(self, mock_enrollment, mock_submission):
        """Category filter is applied to assignments queryset."""
        from visualizations.services import course_summary

        user = MagicMock()
        user.is_staff = True

        mock_enrollment.objects.filter.return_value.count.return_value = 0

        course = MagicMock()
        course.id = 1
        course.name = "Course A"
        qs = MagicMock()
        course.assignments.select_related.return_value = qs
        qs.filter.return_value = qs
        qs.annotate.return_value = []

        course_summary(user, course, category="Math")

        qs.filter.assert_any_call(assessment__category="Math")

    @patch("visualizations.services.Submission")
    @patch("visualizations.services.Enrollment")
    def test_filters_by_assessment_id(self, mock_enrollment, mock_submission):
        """assessmentId filter is applied to assignments queryset."""
        from visualizations.services import course_summary

        user = MagicMock()
        user.is_staff = True

        mock_enrollment.objects.filter.return_value.count.return_value = 0

        course = MagicMock()
        course.id = 1
        course.name = "Course A"
        qs = MagicMock()
        course.assignments.select_related.return_value = qs
        qs.filter.return_value = qs
        qs.annotate.return_value = []

        course_summary(user, course, assessment_id=42)

        qs.filter.assert_any_call(assessment_id=42)


# ============================================================================
# assignment_grade_summary
# ============================================================================


class TestAssignmentGradeSummary:
    """Tests for the assignment_grade_summary function."""

    @patch("visualizations.services._distribution_from_graded_queryset")
    @patch("visualizations.services.Submission")
    def test_returns_grade_summary_structure(self, mock_submission, mock_dist):
        """Returns proper grade summary structure."""
        from visualizations.services import assignment_grade_summary

        user = MagicMock()
        user.is_staff = True

        course = MagicMock()
        course.enrollments.filter.return_value.count.return_value = 10

        assignment = MagicMock()
        assignment.id = 5
        assignment.course = course
        assignment.assessment.title = "Quiz 1"
        assignment.assessment.category = "Math"

        qs = MagicMock()
        mock_submission.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.count.return_value = 0
        qs.aggregate.return_value = {"avg": None, "high": None, "low": None}
        qs.values_list.return_value = []

        mock_dist.return_value = [
            {"range": "0-59", "count": 0},
            {"range": "60-69", "count": 0},
            {"range": "70-79", "count": 0},
            {"range": "80-89", "count": 0},
            {"range": "90-100", "count": 0},
        ]

        result = assignment_grade_summary(user, assignment)

        assert "generatedAt" in result
        assert "totalStudents" in result
        assert result["totalStudents"] == 10
        assert result["assignmentId"] == 5
        assert result["assessmentTitle"] == "Quiz 1"
        assert result["assessmentCategory"] == "Math"

    @patch("visualizations.services._distribution_from_graded_queryset")
    @patch("visualizations.services.Submission")
    def test_returns_none_scores_when_no_graded(self, mock_submission, mock_dist):
        """Returns None for score fields when no graded submissions exist."""
        from visualizations.services import assignment_grade_summary

        user = MagicMock()
        user.is_staff = True

        course = MagicMock()
        course.enrollments.filter.return_value.count.return_value = 5

        assignment = MagicMock()
        assignment.id = 1
        assignment.course = course
        assignment.assessment.title = "Quiz"
        assignment.assessment.category = None

        qs = MagicMock()
        mock_submission.objects.filter.return_value = qs
        qs.filter.return_value = qs
        qs.count.return_value = 0
        qs.aggregate.return_value = {"avg": None, "high": None, "low": None}
        qs.values_list.return_value = []

        mock_dist.return_value = []

        result = assignment_grade_summary(user, assignment)

        assert result["avgScore"] is None
        assert result["medianScore"] is None
        assert result["highScore"] is None
        assert result["lowScore"] is None


# ============================================================================
# mood_meter_summary
# ============================================================================


class TestMoodMeterSummary:
    """Tests for the mood_meter_summary function."""

    @patch("visualizations.services.NumberScaleAnswer")
    @patch("visualizations.services.Submission")
    def test_returns_quadrant_structure(self, mock_submission, mock_ns_answer):
        """Returns a structure with quadrants and totalResponses."""
        from visualizations.services import mood_meter_summary

        user = MagicMock()
        user.is_staff = True

        assignment = MagicMock()
        assignment.id = 10
        assignment.assessment.questions.filter.return_value.select_related.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        qs = MagicMock()
        mock_submission.objects.filter.return_value = qs
        qs.annotate.return_value = qs
        qs.filter.return_value = qs
        qs.aggregate.return_value = {
            "total": 0,
            "high_positive": 0,
            "high_negative": 0,
            "low_positive": 0,
            "low_negative": 0,
        }

        result = mood_meter_summary(user, assignment)

        assert "generatedAt" in result
        assert "totalResponses" in result
        assert "quadrants" in result
        assert len(result["quadrants"]) == 4
        assert result["assignmentId"] == 10


# ============================================================================
# _is_researcher_without_viz
# ============================================================================


class TestIsResearcherWithoutViz:
    """Tests for the _is_researcher_without_viz helper."""

    @patch("visualizations.services.has_sudo_permission")
    @patch("visualizations.services.has_role")
    def test_admin_returns_false(self, mock_has_role, mock_has_sudo):
        """Admin user always returns False."""
        from visualizations.services import _is_researcher_without_viz

        user = MagicMock()
        user.is_staff = True

        assert _is_researcher_without_viz(user) is False

    @patch("visualizations.services.has_sudo_permission")
    @patch("visualizations.services.has_role")
    def test_researcher_without_perm_returns_true(self, mock_has_role, mock_has_sudo):
        """Researcher without VIEW_IDENTIFIABLE_VIZ returns True."""
        from visualizations.services import _is_researcher_without_viz

        user = MagicMock()
        user.is_staff = False
        mock_has_role.return_value = True
        mock_has_sudo.return_value = False

        assert _is_researcher_without_viz(user) is True

    @patch("visualizations.services.has_sudo_permission")
    @patch("visualizations.services.has_role")
    def test_researcher_with_perm_returns_false(self, mock_has_role, mock_has_sudo):
        """Researcher with VIEW_IDENTIFIABLE_VIZ returns False."""
        from visualizations.services import _is_researcher_without_viz

        user = MagicMock()
        user.is_staff = False
        mock_has_role.return_value = True
        mock_has_sudo.return_value = True

        assert _is_researcher_without_viz(user) is False
