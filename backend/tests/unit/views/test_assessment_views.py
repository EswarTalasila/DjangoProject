"""Pure unit tests for assessment views (no database, mocked services)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from assessments.models import GradingMode
from core.dtos import AssessmentDTO

pytestmark = pytest.mark.unit



factory = APIRequestFactory()


def _authed_request(method, url, data=None, user=None, query_params=None):
    """Build an authenticated DRF request with force_authenticate."""
    builder = getattr(factory, method)
    request = builder(url, data=data, format="json")
    user = user or MagicMock(is_authenticated=True, is_staff=False)
    force_authenticate(request, user=user)
    return request


def _paginated_response(results=None):
    """Return a real DRF Response shaped like paginate() output."""
    return Response(
        {"count": len(results or []), "next": None, "previous": None, "results": results or []},
        status=status.HTTP_200_OK,
    )


def _make_dto(**overrides):
    """Build an AssessmentDTO with sensible defaults."""
    defaults = dict(
        id=1, title="Quiz", category=None, gradingMode=GradingMode.AUTO,
        scoringPolicy="STANDARD", questions=[], questionGroups=[],
    )
    defaults.update(overrides)
    return AssessmentDTO(**defaults)


# ---------------------------------------------------------------------------
# list_or_create view
# ---------------------------------------------------------------------------


class TestListOrCreateView:
    """Tests for the list_or_create assessment view."""

    @patch("assessments.views.paginate")
    @patch("assessments.views.list_assessments")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_get_lists_assessments(self, mock_perm, mock_list, mock_paginate):
        """GET returns paginated assessment list."""
        from assessments.views import list_or_create

        mock_paginate.return_value = _paginated_response()
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assessments", user=user)

        list_or_create(request)

        mock_list.assert_called_once()
        mock_paginate.assert_called_once()

    @patch("assessments.views.assessment_to_dto")
    @patch("assessments.views._assessment_with_related")
    @patch("assessments.views.create_assessment")
    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_creates_assessment(
        self, mock_perm, mock_is_ra, mock_create, mock_refetch, mock_dto
    ):
        """POST creates a new assessment and returns DTO."""
        from assessments.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assessment = SimpleNamespace(id=1)
        mock_create.return_value = fake_assessment
        mock_refetch.return_value = fake_assessment
        mock_dto.return_value = _make_dto()

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assessments",
            data={
                "title": "Quiz",
                "gradingMode": GradingMode.AUTO,
            },
            user=user,
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Quiz"

    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_forbidden_for_teacher(self, mock_perm, mock_is_ra):
        """POST returns 403 when user is not researcher or admin."""
        from assessments.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = False

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assessments",
            data={"title": "Q", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_invalid_payload_returns_400(self, mock_perm, mock_is_ra):
        """POST returns 400 for invalid serializer input."""
        from assessments.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = True

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/assessments", data={}, user=user
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# detail view
# ---------------------------------------------------------------------------


class TestDetailView:
    """Tests for the detail assessment view."""

    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_404_when_not_found(self, mock_perm, mock_assessment_model):
        """Returns 404 when assessment does not exist."""
        from assessments.views import detail

        mock_assessment_model.objects.filter.return_value.first.return_value = None
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assessments/999", user=user)

        response = detail(request, assessment_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("assessments.views.assessment_to_dto")
    @patch("assessments.views._assessment_with_related")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_get_returns_dto(
        self, mock_perm, mock_assessment_model, mock_with_related, mock_dto
    ):
        """GET returns assessment DTO."""
        from assessments.views import detail

        fake_assessment = SimpleNamespace(id=1)
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            fake_assessment
        )
        mock_with_related.return_value = fake_assessment
        mock_dto.return_value = _make_dto()

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assessments/1", user=user)

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == 1

    @patch("assessments.views.assessment_to_dto")
    @patch("assessments.views._assessment_with_related")
    @patch("assessments.views.update_assessment")
    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_updates_assessment(
        self, mock_perm, mock_assessment_model, mock_is_ra, mock_update, mock_refetch, mock_dto
    ):
        """PATCH updates assessment and returns DTO."""
        from assessments.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assessment = SimpleNamespace(id=1)
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            fake_assessment
        )
        mock_update.return_value = fake_assessment
        mock_refetch.return_value = fake_assessment
        mock_dto.return_value = _make_dto(title="Updated")

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assessments/1",
            data={"title": "Updated", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_200_OK

    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_forbidden_for_teacher(
        self, mock_perm, mock_assessment_model, mock_is_ra
    ):
        """PATCH returns 403 when user is not researcher or admin."""
        from assessments.views import detail

        mock_is_ra.return_value.has_permission.return_value = False
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assessments/1",
            data={"title": "X", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_delete_without_purge_returns_409(
        self, mock_perm, mock_assessment_model, mock_is_ra
    ):
        """DELETE without ?purge=true returns 409 with guidance."""
        from assessments.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assessment = SimpleNamespace(id=1, status="ACTIVE")
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            fake_assessment
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assessments/1", user=user)

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_delete_forbidden_for_teacher(
        self, mock_perm, mock_assessment_model, mock_is_ra
    ):
        """DELETE returns 403 when user is not researcher or admin."""
        from assessments.views import detail

        mock_is_ra.return_value.has_permission.return_value = False
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assessments/1", user=user)

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assessments.views.update_assessment", side_effect=ValueError("bad question"))
    @patch("assessments.views.IsResearcherOrAdmin")
    @patch("assessments.views.Assessment")
    @patch("assessments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_handles_value_error(
        self, mock_perm, mock_assessment_model, mock_is_ra, mock_update
    ):
        """PATCH returns error when update_assessment raises ValueError."""
        from assessments.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assessments/1",
            data={"title": "X", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assessment_id=1)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
