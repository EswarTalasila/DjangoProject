"""Unit tests for visualizations.views endpoint logic.

All service calls are mocked. Tests focus on serializer validation,
permission gating, and response structure.

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
# get_visualizations
# ============================================================================


class TestGetVisualizations:
    """Tests for the get_visualizations view."""

    @patch("visualizations.views.get_visualization_data")
    def test_returns_200_with_empty_filters(self, mock_service):
        """Returns 200 with empty result for valid empty filters."""
        from visualizations.views import get_visualizations

        mock_service.return_value = []

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/visualization/", {}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_200_OK
        assert response.data == []

    @patch("visualizations.views.get_visualization_data")
    def test_returns_dto_list(self, mock_service):
        """Returns serialized DTO list from the service."""
        from visualizations.views import get_visualizations

        dto = MagicMock()
        dto.model_dump.return_value = {"id": 1, "score": 90.0}
        mock_service.return_value = [dto]

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/visualization/", {"courseId": 5}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == 1

    @patch("visualizations.views.get_visualization_data")
    def test_handles_value_error(self, mock_service):
        """Returns error response when service raises ValueError."""
        from visualizations.views import get_visualizations

        mock_service.side_effect = ValueError("Invalid filter combination")

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/visualization/", {}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("visualizations.views.get_visualization_data")
    def test_admin_can_access(self, mock_service):
        """Admin users can access visualization data."""
        from visualizations.views import get_visualizations

        mock_service.return_value = []

        user = _user(is_staff=True, role=Role.TEACHER)
        request = _authed_request("post", "/visualization/", {}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("visualizations.views.get_visualization_data")
    def test_researcher_can_access(self, mock_service):
        """Researcher users can access visualization data."""
        from visualizations.views import get_visualizations

        mock_service.return_value = []

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", "/visualization/", {}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("visualizations.views.get_visualization_data")
    def test_passes_validated_filters(self, mock_service):
        """Validated filter parameters are forwarded to the service."""
        from visualizations.views import get_visualizations

        mock_service.return_value = []

        user = _user(role=Role.TEACHER)
        data = {"studentId": 42, "courseId": 7, "category": "Math"}
        request = _authed_request("post", "/visualization/", data, user=user)

        get_visualizations(request)

        call_args = mock_service.call_args
        filters = call_args[0][0]
        assert filters["studentId"] == 42
        assert filters["courseId"] == 7
        assert filters["category"] == "Math"

    @patch("visualizations.views.get_visualization_data")
    def test_empty_body_treated_as_empty_filters(self, mock_service):
        """Empty request body is treated as empty filter dict."""
        from visualizations.views import get_visualizations

        mock_service.return_value = []

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/visualization/", {}, user=user)

        response = get_visualizations(request)

        assert response.status_code == http_status.HTTP_200_OK
