"""Unit tests for assignment image extension views."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

pytestmark = pytest.mark.unit


factory = APIRequestFactory()


def _user(*, id=1, is_staff=False, role=Role.TEACHER):
    user = MagicMock()
    user.id = id
    user.pk = id
    user.is_staff = is_staff
    user.is_authenticated = True
    user.is_active = True
    user.is_anonymous = False
    user._cached_role_set = {role} if role else set()
    user.roles = MagicMock()
    user.roles.values_list.return_value = user._cached_role_set
    return user


def _authed_request(method: str, path: str, *, user, data=None):
    builder = getattr(factory, method)
    request = builder(path, data=data, format="json")
    force_authenticate(request, user=user)
    return request


class TestAssignmentImageMutationLifecycle:
    @patch("assignments.image_views.AssignmentQuestion")
    def test_upload_or_delete_returns_409_for_archived_assignment(self, mock_question_model):
        """Archived assignments reject teacher image uploads with lifecycle guidance."""
        from assignments.image_views import upload_or_delete

        mock_question_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            SimpleNamespace(
                id=5,
                image=None,
                locked_from_source=False,
                assignment=SimpleNamespace(status="ARCHIVED", created_by_id=1),
            )
        )
        request = _authed_request(
            "post",
            "/api/v1/assignments/1/questions/5/image",
            user=_user(id=1),
        )

        response = upload_or_delete(request, assignment_id=1, question_id=5)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "cannot be extended" in response.data["detail"].lower()

    @patch("assignments.image_views.AssignmentQuestion")
    def test_reuse_image_returns_409_for_archived_assignment(self, mock_question_model):
        """Archived assignments reject image reuse mutations too."""
        from assignments.image_views import reuse_image

        mock_question_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            SimpleNamespace(
                id=5,
                locked_from_source=False,
                assignment=SimpleNamespace(status="ARCHIVED", created_by_id=1),
            )
        )
        request = _authed_request(
            "post",
            "/api/v1/assignments/1/questions/5/image/reuse",
            user=_user(id=1),
            data={"assetId": "img-1"},
        )

        response = reuse_image(request, assignment_id=1, question_id=5)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "cannot be extended" in response.data["detail"].lower()
