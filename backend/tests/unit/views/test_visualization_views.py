"""Unit tests for visualizations.views endpoint logic.

All service calls are mocked. Tests focus on permission gating
and response structure.

Uses ``force_authenticate`` to bypass DRF token/session auth while still
exercising the ``IsTeacherOrAbove`` permission class.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status as http_status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

factory = APIRequestFactory()


def _user(*, id=1, is_staff=False, role=Role.TEACHER, is_authenticated=True):
    """Build a mock user with role support."""
    user = MagicMock()
    user.id = id
    user.pk = id
    user.is_staff = is_staff
    user.is_authenticated = is_authenticated
    user.is_active = True
    user.is_anonymous = False
    user._cached_role_set = {role} if role else set()
    user.roles = MagicMock()
    user.roles.values_list.return_value = user._cached_role_set
    return user


def _authed_request(method, path, data=None, *, user, **kwargs):
    """Create an APIRequestFactory request with force_authenticate applied."""
    factory_method = getattr(factory, method)
    fmt = kwargs.pop("format", "json")
    request = factory_method(path, data, format=fmt, **kwargs)
    force_authenticate(request, user=user)
    return request


# ============================================================================
# viz_dashboard
# ============================================================================


class TestVizDashboard:
    """Tests for the viz_dashboard view."""

    @patch("visualizations.views.dashboard_overview")
    def test_returns_200_for_teacher(self, mock_service):
        """Returns 200 with dashboard data for teacher."""
        from visualizations.views import viz_dashboard

        mock_service.return_value = {"generatedAt": "2026-01-01", "courses": []}

        user = _user(role=Role.TEACHER)
        request = _authed_request("get", "/api/v1/visualizations/dashboard", user=user)

        response = viz_dashboard(request)

        assert response.status_code == http_status.HTTP_200_OK
        assert "courses" in response.data

    @patch("visualizations.views.dashboard_overview")
    def test_admin_can_access(self, mock_service):
        """Admin users can access dashboard data."""
        from visualizations.views import viz_dashboard

        mock_service.return_value = {"generatedAt": "2026-01-01", "courses": []}

        user = _user(is_staff=True, role=Role.TEACHER)
        request = _authed_request("get", "/api/v1/visualizations/dashboard", user=user)

        response = viz_dashboard(request)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("visualizations.views.dashboard_overview")
    def test_researcher_can_access(self, mock_service):
        """Researcher users can access dashboard data."""
        from visualizations.views import viz_dashboard

        mock_service.return_value = {"generatedAt": "2026-01-01", "courses": []}

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("get", "/api/v1/visualizations/dashboard", user=user)

        response = viz_dashboard(request)

        assert response.status_code == http_status.HTTP_200_OK


# ============================================================================
# viz_course_summary
# ============================================================================


class TestVizCourseSummary:
    """Tests for the viz_course_summary view."""

    @patch("visualizations.views.course_summary")
    @patch("visualizations.views.Course")
    def test_returns_200_for_valid_course(self, mock_course_model, mock_service):
        """Returns 200 with course summary data."""
        from visualizations.views import viz_course_summary

        mock_course = MagicMock()
        mock_course_model.objects.select_related.return_value.get.return_value = mock_course
        mock_service.return_value = {
            "generatedAt": "2026-01-01",
            "enrolledCount": 5,
            "assignments": [],
        }

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/courses/1/summary", user=user)

        response = viz_course_summary(request, course_id=1)

        assert response.status_code == http_status.HTTP_200_OK
        assert "enrolledCount" in response.data

    @patch("visualizations.views.Course")
    def test_returns_404_when_course_not_found(self, mock_course_model):
        """Returns 404 when course does not exist."""
        from visualizations.views import viz_course_summary
        from courses.models import Course

        mock_course_model.DoesNotExist = Course.DoesNotExist
        mock_course_model.objects.select_related.return_value.get.side_effect = Course.DoesNotExist

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/courses/999/summary", user=user)

        response = viz_course_summary(request, course_id=999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# viz_assignment_summary
# ============================================================================


class TestVizAssignmentSummary:
    """Tests for the viz_assignment_summary view."""

    @patch("visualizations.views.assignment_grade_summary")
    @patch("visualizations.views.Assignment")
    def test_returns_200_for_valid_assignment(self, mock_asgn_model, mock_service):
        """Returns 200 with assignment grade summary data."""
        from visualizations.views import viz_assignment_summary

        mock_asgn = MagicMock()
        mock_asgn.course = MagicMock()
        mock_asgn_model.objects.select_related.return_value.get.return_value = mock_asgn
        mock_service.return_value = {
            "generatedAt": "2026-01-01",
            "totalStudents": 10,
            "submittedCount": 5,
        }

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/assignments/1/summary", user=user)

        response = viz_assignment_summary(request, assignment_id=1)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("visualizations.views.Assignment")
    def test_returns_404_when_assignment_not_found(self, mock_asgn_model):
        """Returns 404 when assignment does not exist."""
        from visualizations.views import viz_assignment_summary
        from assignments.models import Assignment

        mock_asgn_model.DoesNotExist = Assignment.DoesNotExist
        mock_asgn_model.objects.select_related.return_value.get.side_effect = Assignment.DoesNotExist

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/assignments/999/summary", user=user)

        response = viz_assignment_summary(request, assignment_id=999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# viz_mood_meter
# ============================================================================


class TestVizMoodMeter:
    """Tests for the viz_mood_meter view."""

    @patch("visualizations.views.mood_meter_summary")
    @patch("visualizations.views.Assignment")
    def test_returns_409_for_non_mood_meter_assignment_template(self, mock_asgn_model, mock_service):
        """Returns 409 when assignment_template is not MOOD_METER type."""
        from visualizations.views import viz_mood_meter

        mock_asgn = MagicMock()
        mock_asgn.assignment_template.grading_mode = "AUTO"
        mock_asgn_model.objects.select_related.return_value.get.return_value = mock_asgn

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/assignments/1/mood-meter", user=user)

        response = viz_mood_meter(request, assignment_id=1)

        assert response.status_code == http_status.HTTP_409_CONFLICT

    @patch("visualizations.views.Assignment")
    def test_returns_404_when_assignment_not_found(self, mock_asgn_model):
        """Returns 404 when assignment does not exist."""
        from visualizations.views import viz_mood_meter
        from assignments.models import Assignment

        mock_asgn_model.DoesNotExist = Assignment.DoesNotExist
        mock_asgn_model.objects.select_related.return_value.get.side_effect = Assignment.DoesNotExist

        user = _user(is_staff=True)
        request = _authed_request("get", "/api/v1/visualizations/assignments/999/mood-meter", user=user)

        response = viz_mood_meter(request, assignment_id=999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
