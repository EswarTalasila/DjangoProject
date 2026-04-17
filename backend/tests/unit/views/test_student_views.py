"""Unit tests for student add/enroll endpoint logic via courses.views.

All service calls and ORM lookups are mocked. Tests focus on:
- Permission/role gating via IsTeacherOrAbove
- Input validation & error responses
- Status codes for POST (add student to course)

DRF views are decorated with ``@api_view`` and ``@permission_classes``, so we
use ``APIRequestFactory`` with ``force_authenticate`` to bypass token/session
auth while still exercising the permission logic.
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
    """Build a mock user with role support for permission checks."""
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


def _mock_student_dto():
    """Return a mock DTO whose model_dump() returns a serializable dict."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "id": 42,
        "name": "Test Student",
        "username": "stu12345",
        "role": "STUDENT",
        "consent": False,
        "courseId": 10,
        "enrolledAt": None,
    }
    return dto


# ============================================================================
# list_or_add_students POST (add student)
# ============================================================================


class TestAddStudent:
    """Tests for POST /api/v1/courses/{id}/students via list_or_add_students."""

    @patch("courses.views.enrollment_to_student_dto")
    @patch("courses.views.create_student_in_course")
    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_201_on_success(
        self, _mock_perm, mock_course_model, mock_can_manage, mock_create, mock_dto
    ):
        """Returns 201 with student DTO on successful creation."""
        from courses.views import list_or_add_students

        fake_course = MagicMock(id=10)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        fake_enrollment = MagicMock()
        mock_create.return_value = fake_enrollment
        mock_dto.return_value = _mock_student_dto()

        user = _user(role=Role.TEACHER)
        data = {"name": "New Student"}
        request = _authed_request(
            "post", "/api/v1/courses/10/students", data, user=user
        )

        response = list_or_add_students(request, course_id=10)

        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data["id"] == 42
        mock_create.assert_called_once()

    @patch("courses.views.create_student_in_course")
    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_400_on_value_error(
        self, _mock_perm, mock_course_model, mock_can_manage, mock_create
    ):
        """Returns 400 when service raises ValueError."""
        from courses.views import list_or_add_students

        fake_course = MagicMock(id=10)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        mock_create.side_effect = ValueError("StudentProfile not created")

        user = _user(role=Role.TEACHER)
        data = {"name": "Bad Student"}
        request = _authed_request(
            "post", "/api/v1/courses/10/students", data, user=user
        )

        response = list_or_add_students(request, course_id=10)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_400_on_empty_body(
        self, _mock_perm, mock_course_model, mock_can_manage
    ):
        """Returns 400 when request body is empty."""
        from courses.views import list_or_add_students

        fake_course = MagicMock(id=10)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        user = _user(role=Role.TEACHER)
        request = _authed_request(
            "post", "/api/v1/courses/10/students", {}, user=user
        )

        response = list_or_add_students(request, course_id=10)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("courses.views.can_manage_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_403_when_not_owner(
        self, _mock_perm, mock_course_model, mock_can_manage
    ):
        """Returns 403 when teacher does not own the course."""
        from courses.views import list_or_add_students

        fake_course = MagicMock(id=10)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        user = _user(role=Role.TEACHER)
        data = {"name": "Student"}
        request = _authed_request(
            "post", "/api/v1/courses/10/students", data, user=user
        )

        response = list_or_add_students(request, course_id=10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# list_or_add_students GET (list students)
# ============================================================================


class TestListStudents:
    """Tests for GET /api/v1/courses/{id}/students via list_or_add_students."""

    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_404_when_course_not_found(self, _mock_perm, mock_course_model):
        """Returns 404 when course does not exist."""
        from courses.views import list_or_add_students

        mock_course_model.objects.filter.return_value.first.return_value = None

        user = _user(role=Role.TEACHER)
        request = _authed_request(
            "get", "/api/v1/courses/999/students", user=user
        )

        response = list_or_add_students(request, course_id=999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("courses.views.can_view_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_403_when_not_authorized(
        self, _mock_perm, mock_course_model, mock_can_view
    ):
        """Returns 403 when user cannot view course."""
        from courses.views import list_or_add_students

        mock_course_model.objects.filter.return_value.first.return_value = MagicMock(id=1)

        user = _user(role=Role.TEACHER)
        request = _authed_request(
            "get", "/api/v1/courses/1/students", user=user
        )

        response = list_or_add_students(request, course_id=1)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("courses.views.paginate")
    @patch("courses.views.list_students_in_course")
    @patch("courses.views.can_view_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_paginated_students(
        self, _mock_perm, mock_course_model, mock_can_view, mock_list, mock_paginate
    ):
        """Returns paginated student list."""
        from rest_framework.response import Response
        from courses.views import list_or_add_students

        fake_course = MagicMock(id=1)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        mock_paginate.return_value = Response(
            {"count": 0, "next": None, "previous": None, "results": []},
            status=http_status.HTTP_200_OK,
        )

        user = _user(role=Role.TEACHER)
        request = _authed_request(
            "get", "/api/v1/courses/1/students", user=user
        )

        list_or_add_students(request, course_id=1)

        mock_list.assert_called_once_with(fake_course)
        mock_paginate.assert_called_once()
