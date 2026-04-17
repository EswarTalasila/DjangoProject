"""Pure unit tests for rubrics.views (no database).

DRF views are decorated with @api_view and @permission_classes, so we
use APIRequestFactory with force_authenticate to bypass token/session
auth while still exercising the permission logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

pytestmark = pytest.mark.unit

factory = APIRequestFactory()


def _user(*, id=1, is_staff=False, role=Role.TEACHER, is_authenticated=True):
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


def _authed_request(method, path="/", data=None, *, user, **kwargs):
    factory_method = getattr(factory, method)
    fmt = kwargs.pop("format", "json")
    request = factory_method(path, data, format=fmt, **kwargs)
    force_authenticate(request, user=user)
    return request


# ---------------------------------------------------------------------------
# list_or_create
# ---------------------------------------------------------------------------

class TestListOrCreate:

    @patch("rubrics.views.paginate")
    @patch("rubrics.views.list_rubrics")
    def test_get_returns_paginated_rubrics(self, mock_list, mock_paginate):
        """Returns paginated rubric list on GET request."""
        from rubrics.views import list_or_create

        from rest_framework.response import Response
        mock_list.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(role=Role.TEACHER)
        request = _authed_request("get", user=user)
        response = list_or_create(request)

        mock_list.assert_called_once()
        mock_paginate.assert_called_once()

    @patch("rubrics.views.rubric_to_dto")
    @patch("rubrics.views._rubric_with_related")
    @patch("rubrics.views.create_rubric")
    @patch("rubrics.views.RubricSerializer")
    def test_post_creates_rubric(self, mock_serializer_cls, mock_create, mock_refetch, mock_to_dto):
        """Creates a rubric and returns 201 on valid POST request."""
        from rubrics.views import list_or_create

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"title": "R1"}
        mock_serializer_cls.return_value = serializer

        fake_rubric = MagicMock()
        mock_create.return_value = fake_rubric
        mock_refetch.return_value = fake_rubric
        mock_to_dto.return_value.model_dump.return_value = {"id": 1}

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", data={"title": "R1"}, user=user)
        response = list_or_create(request)

        assert response.status_code == status.HTTP_201_CREATED
        mock_create.assert_called_once()

    def test_post_forbidden_for_student(self):
        """Returns 403 when a student attempts to create a rubric."""
        from rubrics.views import list_or_create

        user = _user(role=Role.STUDENT)
        request = _authed_request("post", data={"title": "R1"}, user=user)
        response = list_or_create(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("rubrics.views.create_rubric")
    @patch("rubrics.views.RubricSerializer")
    def test_post_returns_400_on_value_error(self, mock_serializer_cls, mock_create):
        """Returns 400 when rubric creation raises a ValueError."""
        from rubrics.views import list_or_create

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"title": ""}
        mock_serializer_cls.return_value = serializer
        mock_create.side_effect = ValueError("title is required")

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", data={"title": ""}, user=user)
        response = list_or_create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# detail
# ---------------------------------------------------------------------------

class TestDetail:

    @patch("rubrics.views.Rubric")
    def test_get_returns_404_when_not_found(self, mock_rubric_model):
        """Returns 404 when the rubric does not exist."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = None

        user = _user(role=Role.TEACHER)
        request = _authed_request("get", user=user)
        response = detail(request, rubric_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("rubrics.views.rubric_to_dto")
    @patch("rubrics.views._rubric_with_related")
    @patch("rubrics.views.Rubric")
    def test_get_returns_rubric(self, mock_rubric_model, mock_with_related, mock_to_dto):
        """Returns 200 with rubric DTO on successful GET."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()
        mock_with_related.return_value = MagicMock()
        mock_to_dto.return_value.model_dump.return_value = {"id": 1}

        user = _user(role=Role.TEACHER)
        request = _authed_request("get", user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_200_OK

    @patch("rubrics.views.Rubric")
    def test_patch_forbidden_for_teacher(self, mock_rubric_model):
        """Returns 403 when a teacher attempts to update a rubric."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()

        user = _user(role=Role.TEACHER)
        request = _authed_request("patch", data={"title": "New"}, user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("rubrics.views.rubric_to_dto")
    @patch("rubrics.views._rubric_with_related")
    @patch("rubrics.views.update_rubric")
    @patch("rubrics.views.RubricSerializer")
    @patch("rubrics.views.Rubric")
    def test_patch_updates_rubric(self, mock_rubric_model, mock_serializer_cls, mock_update, mock_refetch, mock_to_dto):
        """Returns 200 with updated rubric DTO on successful PATCH."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()
        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"title": "New"}
        mock_serializer_cls.return_value = serializer
        fake_rubric = MagicMock()
        mock_update.return_value = fake_rubric
        mock_refetch.return_value = fake_rubric
        mock_to_dto.return_value.model_dump.return_value = {"id": 1}

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("patch", data={"title": "New"}, user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_200_OK

    @patch("rubrics.views.update_rubric")
    @patch("rubrics.views.RubricSerializer")
    @patch("rubrics.views.Rubric")
    def test_patch_returns_409_on_referenced_error(self, mock_rubric_model, mock_serializer_cls, mock_update):
        """Returns 409 when updating a rubric that is referenced by an assignment_template."""
        from rubrics.views import detail
        from rubrics.services import RubricReferencedError

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()
        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"title": "X"}
        mock_serializer_cls.return_value = serializer
        mock_update.side_effect = RubricReferencedError("referenced")

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("patch", data={"title": "X"}, user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("rubrics.views.update_rubric")
    @patch("rubrics.views.RubricSerializer")
    @patch("rubrics.views.Rubric")
    def test_patch_returns_400_on_value_error(self, mock_rubric_model, mock_serializer_cls, mock_update):
        """Returns 400 when rubric update raises a ValueError."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()
        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {}
        mock_serializer_cls.return_value = serializer
        mock_update.side_effect = ValueError("bad")

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("patch", data={}, user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("rubrics.views.delete_rubric")
    @patch("rubrics.views.Rubric")
    def test_delete_succeeds(self, mock_rubric_model, mock_delete):
        """Returns 204 on successful rubric deletion."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("delete", user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once()

    @patch("rubrics.views.Rubric")
    def test_delete_forbidden_for_teacher(self, mock_rubric_model):
        """Returns 403 when a teacher attempts to delete a rubric."""
        from rubrics.views import detail

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()

        user = _user(role=Role.TEACHER)
        request = _authed_request("delete", user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("rubrics.views.delete_rubric")
    @patch("rubrics.views.Rubric")
    def test_delete_returns_409_on_referenced_error(self, mock_rubric_model, mock_delete):
        """Returns 409 when deleting a rubric that is referenced by an assignment_template."""
        from rubrics.views import detail
        from rubrics.services import RubricReferencedError

        mock_rubric_model.objects.filter.return_value.first.return_value = MagicMock()
        mock_delete.side_effect = RubricReferencedError("referenced")

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("delete", user=user)
        response = detail(request, rubric_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------

class TestArchive:

    def test_forbidden_for_teacher(self):
        """Returns 403 when a teacher attempts to archive a rubric."""
        from rubrics.views import archive

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", user=user)
        response = archive(request, rubric_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("rubrics.views.Rubric")
    def test_returns_404_when_not_found(self, mock_rubric):
        """Returns 404 when the rubric to archive does not exist."""
        from rubrics.views import archive

        mock_rubric.objects.filter.return_value.first.return_value = None

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", user=user)
        response = archive(request, rubric_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("rubrics.views.rubric_to_dto")
    @patch("rubrics.views._rubric_with_related")
    @patch("rubrics.views.archive_rubric")
    @patch("rubrics.views.Rubric")
    def test_archives_successfully(self, mock_rubric, mock_archive, mock_refetch, mock_to_dto):
        """Returns 200 with updated DTO on successful archive."""
        from rubrics.views import archive

        mock_rubric.objects.filter.return_value.first.return_value = MagicMock()
        fake_rubric = MagicMock()
        mock_archive.return_value = fake_rubric
        mock_refetch.return_value = fake_rubric
        mock_to_dto.return_value.model_dump.return_value = {"id": 1}

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", user=user)
        response = archive(request, rubric_id=1)

        assert response.status_code == status.HTTP_200_OK

    @patch("rubrics.views.archive_rubric")
    @patch("rubrics.views.Rubric")
    def test_returns_409_when_already_archived(self, mock_rubric, mock_archive):
        """Returns 409 when the rubric is already archived."""
        from rubrics.views import archive

        mock_rubric.objects.filter.return_value.first.return_value = MagicMock()
        mock_archive.side_effect = ValueError("already archived")

        user = _user(role=Role.RESEARCHER)
        request = _authed_request("post", user=user)
        response = archive(request, rubric_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT
