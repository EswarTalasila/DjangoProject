"""Unit tests for courses.views_students endpoint logic.

All service calls and ORM lookups are mocked. Tests focus on:
- Permission/role gating via IsTeacher
- Input validation & error responses
- Status codes for each code path (add_one and add_bulk)

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
    }
    return dto


# ============================================================================
# add_one
# ============================================================================


class TestAddOne:
    """Tests for the add_one view (POST /api/v1/students)."""

    @patch("courses.views_students.enrollment_to_student_dto")
    @patch("courses.views_students.create_student_in_course")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_201_on_success(self, _mock_perm, mock_create, mock_dto):
        """Returns 201 with student DTO on successful creation."""
        from courses.views_students import add_one

        fake_enrollment = MagicMock()
        mock_create.return_value = fake_enrollment
        mock_dto.return_value = _mock_student_dto()

        user = _user(role=Role.TEACHER)
        data = {"name": "New Student", "courseId": 10}
        request = _authed_request("post", "/api/v1/students", data, user=user)

        response = add_one(request)

        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data["id"] == 42
        mock_create.assert_called_once()

    @patch("courses.views_students.create_student_in_course")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_400_on_value_error(self, _mock_perm, mock_create):
        """Returns 400 when service raises ValueError."""
        from courses.views_students import add_one

        mock_create.side_effect = ValueError("Course not found")

        user = _user(role=Role.TEACHER)
        data = {"name": "Bad Student", "courseId": 999}
        request = _authed_request("post", "/api/v1/students", data, user=user)

        response = add_one(request)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Course not found" in response.data["detail"]

    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_400_on_invalid_input(self, _mock_perm):
        """Returns 400 when required fields are missing."""
        from courses.views_students import add_one

        user = _user(role=Role.TEACHER)
        # Missing courseId
        data = {"name": "Student Only"}
        request = _authed_request("post", "/api/v1/students", data, user=user)

        response = add_one(request)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_400_on_empty_body(self, _mock_perm):
        """Returns 400 when request body is empty."""
        from courses.views_students import add_one

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/api/v1/students", {}, user=user)

        response = add_one(request)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("courses.views_students.enrollment_to_student_dto")
    @patch("courses.views_students.create_student_in_course")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_passes_validated_data_to_service(self, _mock_perm, mock_create, mock_dto):
        """Passes serializer-validated data (with consent and password) to service."""
        from courses.views_students import add_one

        mock_create.return_value = MagicMock()
        mock_dto.return_value = _mock_student_dto()

        user = _user(role=Role.TEACHER)
        data = {
            "name": "Full Student",
            "courseId": 5,
            "consent": True,
            "password": "MySecret123!",
        }
        request = _authed_request("post", "/api/v1/students", data, user=user)

        add_one(request)

        call_args = mock_create.call_args
        payload = call_args[0][1]
        assert payload["name"] == "Full Student"
        assert payload["courseId"] == 5
        assert payload["consent"] is True
        assert payload["password"] == "MySecret123!"


# ============================================================================
# add_bulk
# ============================================================================


class TestAddBulk:
    """Tests for the add_bulk view (POST /api/v1/students/import)."""

    @patch("courses.views_students.bulk_create_students")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_201_with_created_count(self, _mock_perm, mock_bulk):
        """Returns 201 with the number of successfully created students."""
        from courses.views_students import add_bulk

        mock_bulk.return_value = 2

        user = _user(role=Role.TEACHER)
        data = [
            {"name": "Student A", "courseId": 10},
            {"name": "Student B", "courseId": 10},
        ]
        request = _authed_request("post", "/api/v1/students/import", data, user=user)

        response = add_bulk(request)

        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data == 2
        mock_bulk.assert_called_once()

    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_returns_400_when_not_list(self, _mock_perm):
        """Returns 400 when request body is not a list."""
        from courses.views_students import add_bulk

        user = _user(role=Role.TEACHER)
        # dict instead of list
        data = {"name": "Not a list", "courseId": 10}
        request = _authed_request("post", "/api/v1/students/import", data, user=user)

        response = add_bulk(request)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Expected list" in response.data["detail"]

    @patch("courses.views_students.bulk_create_students")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_skips_invalid_entries(self, _mock_perm, mock_bulk):
        """Invalid entries in the list are skipped during validation."""
        from courses.views_students import add_bulk

        mock_bulk.return_value = 1

        user = _user(role=Role.TEACHER)
        data = [
            {"name": "Valid Student", "courseId": 10},
            {"invalid": "no name or courseId"},
            {"name": "Another Valid", "courseId": 10},
        ]
        request = _authed_request("post", "/api/v1/students/import", data, user=user)

        response = add_bulk(request)

        assert response.status_code == http_status.HTTP_201_CREATED
        # bulk_create_students should receive only the 2 valid entries
        call_args = mock_bulk.call_args
        validated_list = call_args[0][1]
        assert len(validated_list) == 2

    @patch("courses.views_students.bulk_create_students")
    @patch("courses.views_students.IsTeacher.has_permission", return_value=True)
    def test_empty_list_passes_to_service(self, _mock_perm, mock_bulk):
        """An empty list is passed through to the service."""
        from courses.views_students import add_bulk

        mock_bulk.return_value = 0

        user = _user(role=Role.TEACHER)
        request = _authed_request("post", "/api/v1/students/import", [], user=user)

        response = add_bulk(request)

        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data == 0
        call_args = mock_bulk.call_args
        validated_list = call_args[0][1]
        assert validated_list == []
