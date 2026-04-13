"""Unit tests for assessments.image_views."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

pytestmark = pytest.mark.unit


factory = APIRequestFactory()


def _user(*, id=1, is_staff=False, role=Role.STUDENT, is_authenticated=True):
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


def _authed_request(method: str, path: str, *, user, data=None):
    builder = getattr(factory, method)
    request = builder(path, data=data, format="json")
    force_authenticate(request, user=user)
    return request


class TestFindQuestionByStorageKey:
    @patch("assessments.image_views.parse_question_image")
    @patch("assessments.image_views.Question")
    def test_returns_exact_storage_key_match(self, mock_question_model, mock_parse):
        """Finds the question whose parsed storageKey matches exactly."""
        from assessments.image_views import _find_question_by_storage_key

        wrong = MagicMock()
        right = MagicMock()
        mock_question_model.objects.filter.return_value = [wrong, right]
        mock_parse.side_effect = [
            {"storageKey": "abc-other"},
            {"storageKey": "abc"},
        ]

        result = _find_question_by_storage_key("abc")

        assert result is right
        mock_question_model.objects.filter.assert_called_once_with(
            image__contains='"storageKey": "abc"'
        )


class TestCanReadQuestionImage:
    @patch("assessments.image_views.Enrollment")
    @patch("assessments.image_views.Assignment")
    def test_student_can_read_via_enrolled_assignment(
        self,
        mock_assignment_model,
        mock_enrollment_model,
    ):
        """Student enrolled in assignment's course can read the question image."""
        from assessments.image_views import _can_read_question_image

        user = _user(role=Role.STUDENT)
        question = SimpleNamespace(assessment_id=11)
        mock_assignment_model.objects.select_related.return_value.filter.return_value = [
            SimpleNamespace(course_id=7),
        ]
        mock_enrollment_model.objects.filter.return_value.exists.return_value = True

        assert _can_read_question_image(user, question) is True

    @patch("assessments.image_views.can_view_course", return_value=True)
    @patch("assessments.image_views.Assignment")
    def test_teacher_can_read_via_course_assignment(
        self,
        mock_assignment_model,
        mock_can_view_course,
    ):
        """Teacher who can view the course can read the question image."""
        from assessments.image_views import _can_read_question_image

        user = _user(role=Role.TEACHER)
        question = SimpleNamespace(assessment_id=11)
        assignment = SimpleNamespace(course_id=7, course=MagicMock())
        mock_assignment_model.objects.select_related.return_value.filter.return_value = [
            assignment,
        ]

        assert _can_read_question_image(user, question) is True
        mock_can_view_course.assert_called_once_with(user, assignment.course)


class TestUploadOrDeleteView:
    @patch("assessments.image_views._assessment_is_locked", return_value=True)
    @patch("assessments.image_views.Assessment")
    def test_returns_409_when_assessment_is_locked(
        self,
        mock_assessment_model,
        mock_locked,
    ):
        """Returns 409 when assessment is referenced by assignments."""
        from assessments.image_views import upload_or_delete

        mock_assessment_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )
        request = _authed_request(
            "post",
            "/api/v1/assessments/1/questions/2/image",
            user=_user(role=Role.RESEARCHER),
        )

        response = upload_or_delete(request, assessment_id=1, question_id=2)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["detail"] == "Cannot modify assessment referenced by assignments"


class TestServeImageView:
    @patch("assessments.image_views._can_read_question_image", return_value=False)
    @patch("assessments.image_views._find_question_by_storage_key")
    def test_returns_403_when_request_user_cannot_read_image(
        self,
        mock_find_question,
        mock_can_read,
    ):
        """Returns 403 when user lacks permission to view the image."""
        from assessments.image_views import serve_image

        mock_find_question.return_value = SimpleNamespace(id=5)
        request = _authed_request(
            "get",
            "/api/v1/assessments/images/demo-key",
            user=_user(role=Role.STUDENT),
        )

        response = serve_image(request, "demo-key")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assessments.image_views.get_storage_backend")
    @patch("assessments.image_views.parse_question_image")
    @patch("assessments.image_views._can_read_question_image", return_value=True)
    @patch("assessments.image_views._find_question_by_storage_key")
    def test_returns_image_bytes_for_allowed_user(
        self,
        mock_find_question,
        mock_can_read,
        mock_parse,
        mock_get_storage_backend,
    ):
        """Returns 200 with streamed image bytes for authorized user."""
        from assessments.image_views import serve_image

        mock_find_question.return_value = SimpleNamespace(id=5)
        mock_parse.return_value = {
            "storageKey": "demo-key",
            "mimeType": "image/png",
        }
        mock_get_storage_backend.return_value.retrieve.return_value = b"png-bytes"
        request = _authed_request(
            "get",
            "/api/v1/assessments/images/demo-key",
            user=_user(role=Role.STUDENT),
        )

        response = serve_image(request, "demo-key")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/png"
        assert bytes(response.content) == b"png-bytes"
