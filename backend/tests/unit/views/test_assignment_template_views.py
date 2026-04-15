"""Pure unit tests for assignment_template views (no database, mocked services)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from assignment_templates.models import GradingMode
from core.dtos import AssignmentTemplateDTO

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
    """Build an AssignmentTemplateDTO with sensible defaults."""
    defaults = dict(
        id=1, title="Quiz", category=None, gradingMode=GradingMode.AUTO,
        scoringPolicy="STANDARD", questions=[], questionGroups=[],
    )
    defaults.update(overrides)
    return AssignmentTemplateDTO(**defaults)


# ---------------------------------------------------------------------------
# list_or_create view
# ---------------------------------------------------------------------------


class TestListOrCreateView:
    """Tests for the list_or_create assignment_template view."""

    @patch("assignment_templates.views.paginate")
    @patch("assignment_templates.views.list_assignment_templates")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_get_lists_assignment_templates(self, mock_perm, mock_list, mock_paginate):
        """GET returns paginated assignment_template list."""
        from assignment_templates.views import list_or_create

        mock_paginate.return_value = _paginated_response()
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignment-templates", user=user)

        list_or_create(request)

        mock_list.assert_called_once()
        mock_paginate.assert_called_once()

    @patch("assignment_templates.views.assignment_template_to_dto")
    @patch("assignment_templates.views._assignment_template_with_related")
    @patch("assignment_templates.views.create_assignment_template")
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_creates_assignment_template(
        self, mock_perm, mock_is_ra, mock_create, mock_refetch, mock_dto
    ):
        """POST creates a new assignment_template and returns DTO."""
        from assignment_templates.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assignment_template = SimpleNamespace(id=1)
        mock_create.return_value = fake_assignment_template
        mock_refetch.return_value = fake_assignment_template
        mock_dto.return_value = _make_dto()

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assignment-templates",
            data={
                "title": "Quiz",
                "gradingMode": GradingMode.AUTO,
            },
            user=user,
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Quiz"

    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_forbidden_for_teacher(self, mock_perm, mock_is_ra):
        """POST returns 403 when user is not researcher or admin."""
        from assignment_templates.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = False

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assignment-templates",
            data={"title": "Q", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_post_invalid_payload_returns_400(self, mock_perm, mock_is_ra):
        """POST returns 400 for invalid serializer input."""
        from assignment_templates.views import list_or_create

        mock_is_ra.return_value.has_permission.return_value = True

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/assignment-templates", data={}, user=user
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# detail view
# ---------------------------------------------------------------------------


class TestDetailView:
    """Tests for the detail assignment_template view."""

    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_404_when_not_found(self, mock_perm, mock_assignment_template_model):
        """Returns 404 when assignment_template does not exist."""
        from assignment_templates.views import detail

        mock_assignment_template_model.objects.filter.return_value.first.return_value = None
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignment-templates/999", user=user)

        response = detail(request, assignment_template_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("assignment_templates.views.assignment_template_to_dto")
    @patch("assignment_templates.views._assignment_template_with_related")
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_get_returns_dto(
        self, mock_perm, mock_assignment_template_model, mock_is_ra, mock_with_related, mock_dto
    ):
        """GET returns assignment_template DTO."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assignment_template = SimpleNamespace(id=1, status="ACTIVE")
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        mock_with_related.return_value = fake_assignment_template
        mock_dto.return_value = _make_dto()

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignment-templates/1", user=user)

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == 1

    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_get_teacher_cannot_view_draft_assignment_template(
        self, mock_perm, mock_assignment_template_model, mock_is_ra
    ):
        """Teacher detail access hides draft assignment templates."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = False
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1, status="DRAFT")
        )

        user = MagicMock(is_authenticated=True, is_staff=False)
        request = _authed_request("get", "/api/v1/assignment-templates/1", user=user)

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("assignment_templates.views.assignment_template_to_dto")
    @patch("assignment_templates.views._assignment_template_with_related")
    @patch("assignment_templates.views.update_assignment_template")
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_updates_assignment_template(
        self, mock_perm, mock_assignment_template_model, mock_is_ra, mock_update, mock_refetch, mock_dto
    ):
        """PATCH updates assignment_template and returns DTO."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assignment_template = SimpleNamespace(id=1)
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        mock_update.return_value = fake_assignment_template
        mock_refetch.return_value = fake_assignment_template
        mock_dto.return_value = _make_dto(title="Updated")

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assignment-templates/1",
            data={"title": "Updated", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_200_OK

    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_forbidden_for_teacher(
        self, mock_perm, mock_assignment_template_model, mock_is_ra
    ):
        """PATCH returns 403 when user is not researcher or admin."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = False
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assignment-templates/1",
            data={"title": "X", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignment_templates.views.delete_assignment_template")
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_delete_without_purge_deletes_unused_assignment_template(
        self, mock_perm, mock_assignment_template_model, mock_is_ra, mock_delete
    ):
        """DELETE without ?purge=true hard-deletes an unused active assignment template."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assignment_template = SimpleNamespace(id=1, status="ACTIVE", used_at=None)
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assignment-templates/1", user=user)

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once_with(fake_assignment_template)

    @patch("assignment_templates.views.delete_assignment_template")
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_delete_without_purge_returns_409_for_used_assignment_template(
        self, mock_perm, mock_assignment_template_model, mock_is_ra, mock_delete
    ):
        """DELETE without ?purge=true returns 409 with guidance for used templates."""
        from assignment_templates.views import AssignmentTemplateReferencedError, detail

        mock_is_ra.return_value.has_permission.return_value = True
        fake_assignment_template = SimpleNamespace(id=1, status="ACTIVE", used_at="2026-04-15")
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        mock_delete.side_effect = AssignmentTemplateReferencedError(
            "Assignment template has been used by assignments and must be archived instead."
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assignment-templates/1", user=user)

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT
        mock_delete.assert_called_once_with(fake_assignment_template)

    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_delete_forbidden_for_teacher(
        self, mock_perm, mock_assignment_template_model, mock_is_ra
    ):
        """DELETE returns 403 when user is not researcher or admin."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = False
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1, status="ACTIVE")
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assignment-templates/1", user=user)

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignment_templates.views.update_assignment_template", side_effect=ValueError("bad question"))
    @patch("assignment_templates.views.IsResearcherOrAdmin")
    @patch("assignment_templates.views.AssignmentTemplate")
    @patch("assignment_templates.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_patch_handles_value_error(
        self, mock_perm, mock_assignment_template_model, mock_is_ra, mock_update
    ):
        """PATCH returns error when update_assignment_template raises ValueError."""
        from assignment_templates.views import detail

        mock_is_ra.return_value.has_permission.return_value = True
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch",
            "/api/v1/assignment-templates/1",
            data={"title": "X", "gradingMode": GradingMode.AUTO},
            user=user,
        )

        response = detail(request, assignment_template_id=1)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
