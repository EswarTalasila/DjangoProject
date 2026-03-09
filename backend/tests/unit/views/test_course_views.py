"""Pure unit tests for course views (no database, mocked services)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from core.dtos import CourseDTO

pytestmark = pytest.mark.unit



factory = APIRequestFactory()


def _authed_request(method, url, data=None, user=None):
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


# ---------------------------------------------------------------------------
# list_or_create view
# ---------------------------------------------------------------------------


class TestListOrCreateView:
    """Tests for the list_or_create course view."""

    @patch("courses.views.paginate")
    @patch("courses.views.list_courses_for_user")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_lists_courses(self, mock_perm, mock_list, mock_paginate):
        """GET returns paginated course list."""
        from courses.views import list_or_create

        mock_paginate.return_value = _paginated_response()
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses", user=user)

        list_or_create(request)

        mock_list.assert_called_once_with(user, include_archived=False)
        mock_paginate.assert_called_once()

    @patch("courses.views.course_to_dto")
    @patch("courses.views.create_course")
    @patch("courses.views.IsTeacher")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_post_creates_course(self, mock_perm, mock_is_teacher, mock_create, mock_dto):
        """POST creates a new course and returns DTO."""
        from courses.views import list_or_create

        mock_is_teacher.return_value.has_permission.return_value = True
        fake_course = SimpleNamespace(id=1, name="Math")
        mock_create.return_value = fake_course
        dto = CourseDTO(
            id=1, name="Math", students=[], studentCount=0,
            assignmentIds=[], teacherId=1, teacherName="Teacher", createdAt=None
        )
        mock_dto.return_value = dto

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/courses", data={"name": "Math"}, user=user
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Math"
        mock_create.assert_called_once_with(user, "Math")

    @patch("courses.views.IsTeacher")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_post_forbidden_for_non_teacher(self, mock_perm, mock_is_teacher):
        """POST returns 403 when user is not a teacher (admin creating)."""
        from courses.views import list_or_create

        mock_is_teacher.return_value.has_permission.return_value = False

        user = MagicMock(is_authenticated=True, is_staff=True)
        request = _authed_request(
            "post", "/api/v1/courses", data={"name": "X"}, user=user
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("courses.views.create_course", side_effect=ValueError("Teacher profile not found"))
    @patch("courses.views.IsTeacher")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_post_handles_value_error(self, mock_perm, mock_is_teacher, mock_create):
        """POST returns error response when create_course raises ValueError."""
        from courses.views import list_or_create

        mock_is_teacher.return_value.has_permission.return_value = True

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/courses", data={"name": "X"}, user=user
        )

        response = list_or_create(request)

        # error_response returns 400 for generic errors
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    @patch("courses.views.IsTeacher")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_post_invalid_payload_returns_400(self, mock_perm, mock_is_teacher):
        """POST returns 400 for invalid serializer input."""
        from courses.views import list_or_create

        mock_is_teacher.return_value.has_permission.return_value = True

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/courses", data={}, user=user
        )

        response = list_or_create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# detail view
# ---------------------------------------------------------------------------


class TestDetailView:
    """Tests for the detail course view."""

    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_returns_404_when_course_not_found(self, mock_perm, mock_course_model):
        """Returns 404 when course does not exist."""
        from courses.views import detail

        mock_course_model.objects.filter.return_value.first.return_value = None
        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/999", user=user)

        response = detail(request, course_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("courses.views.course_to_dto")
    @patch("courses.views.can_view_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_returns_course_dto(self, mock_perm, mock_course_model, mock_can_view, mock_dto):
        """GET returns course DTO when user can view."""
        from courses.views import detail

        fake_course = SimpleNamespace(id=1, name="Course")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        dto = CourseDTO(
            id=1, name="Course", students=[], studentCount=0,
            assignmentIds=[], teacherId=1, teacherName="Teacher", createdAt=None
        )
        mock_dto.return_value = dto

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/1", user=user)

        response = detail(request, course_id=1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == 1

    @patch("courses.views.can_view_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_returns_403_when_not_authorized(
        self, mock_perm, mock_course_model, mock_can_view
    ):
        """GET returns 403 when user cannot view course."""
        from courses.views import detail

        mock_course_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/1", user=user)

        response = detail(request, course_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("courses.views.course_to_dto")
    @patch("courses.views.edit_course")
    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_patch_updates_course(
        self, mock_perm, mock_course_model, mock_can_manage, mock_edit, mock_dto
    ):
        """PATCH updates course name and returns DTO."""
        from courses.views import detail

        fake_course = SimpleNamespace(id=1, name="Old")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        updated_course = SimpleNamespace(id=1, name="New")
        mock_edit.return_value = updated_course
        dto = CourseDTO(
            id=1, name="New", students=[], studentCount=0,
            assignmentIds=[], teacherId=1, teacherName="Teacher", createdAt=None
        )
        mock_dto.return_value = dto

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch", "/api/v1/courses/1", data={"name": "New"}, user=user
        )

        response = detail(request, course_id=1)

        assert response.status_code == status.HTTP_200_OK
        mock_edit.assert_called_once_with(fake_course, "New")

    @patch("courses.views.can_manage_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_patch_returns_403_when_not_owner(
        self, mock_perm, mock_course_model, mock_can_manage
    ):
        """PATCH returns 403 when user is not the course owner."""
        from courses.views import detail

        mock_course_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "patch", "/api/v1/courses/1", data={"name": "X"}, user=user
        )

        response = detail(request, course_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("courses.views.Course")
    @patch("courses.views.IsAuthenticated.has_permission", return_value=True)
    def test_delete_without_purge_returns_409(
        self, mock_perm, mock_course_model
    ):
        """DELETE without ?purge=true returns 409 (use archive instead)."""
        from courses.views import detail

        fake_course = SimpleNamespace(id=1, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        user = MagicMock(is_authenticated=True, is_staff=False)
        request = _authed_request("delete", "/api/v1/courses/1", user=user)

        response = detail(request, course_id=1)

        assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# list_students view
# ---------------------------------------------------------------------------


class TestListStudentsView:
    """Tests for the list_or_add_students course view."""

    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_404_when_course_not_found(self, mock_perm, mock_course_model):
        """Returns 404 when course does not exist."""
        from courses.views import list_or_add_students

        mock_course_model.objects.filter.return_value.first.return_value = None

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/1/students", user=user)

        response = list_or_add_students(request, course_id=1)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("courses.views.can_view_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_403_when_not_authorized(
        self, mock_perm, mock_course_model, mock_can_view
    ):
        """Returns 403 when user cannot view course."""
        from courses.views import list_or_add_students

        mock_course_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/1/students", user=user)

        response = list_or_add_students(request, course_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("courses.views.paginate")
    @patch("courses.views.list_students_in_course")
    @patch("courses.views.can_view_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_returns_paginated_students(
        self, mock_perm, mock_course_model, mock_can_view, mock_list, mock_paginate
    ):
        """Returns paginated student list."""
        from courses.views import list_or_add_students

        fake_course = SimpleNamespace(id=1)
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        mock_paginate.return_value = _paginated_response()

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/courses/1/students", user=user)

        list_or_add_students(request, course_id=1)

        mock_list.assert_called_once_with(fake_course)
        mock_paginate.assert_called_once()


# ---------------------------------------------------------------------------
# remove_student view
# ---------------------------------------------------------------------------


class TestRemoveStudentView:
    """Tests for the remove_student course view."""

    @patch("courses.views.Course")
    @patch("courses.views.IsTeacher.has_permission", return_value=True)
    def test_returns_404_when_course_not_found(self, mock_perm, mock_course_model):
        """Returns 404 when course does not exist."""
        from courses.views import remove_student

        mock_course_model.objects.filter.return_value.first.return_value = None

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "delete", "/api/v1/courses/1/students/5", user=user
        )

        response = remove_student(request, course_id=1, student_user_id=5)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("courses.views.can_manage_course", return_value=False)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacher.has_permission", return_value=True)
    def test_returns_403_when_not_owner(
        self, mock_perm, mock_course_model, mock_can_manage
    ):
        """Returns 403 when teacher does not own the course."""
        from courses.views import remove_student

        mock_course_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1)
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "delete", "/api/v1/courses/1/students/5", user=user
        )

        response = remove_student(request, course_id=1, student_user_id=5)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("courses.views.remove_student_from_course")
    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacher.has_permission", return_value=True)
    def test_removes_student_successfully(
        self, mock_perm, mock_course_model, mock_can_manage, mock_remove
    ):
        """Successfully removes student and returns 204."""
        from courses.views import remove_student

        fake_course = SimpleNamespace(id=1, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "delete", "/api/v1/courses/1/students/5", user=user
        )

        response = remove_student(request, course_id=1, student_user_id=5)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_remove.assert_called_once_with(fake_course, 5)

    @patch(
        "courses.views.remove_student_from_course",
        side_effect=ValueError("Student not found in course"),
    )
    @patch("courses.views.can_manage_course", return_value=True)
    @patch("courses.views.Course")
    @patch("courses.views.IsTeacher.has_permission", return_value=True)
    def test_handles_value_error_from_service(
        self, mock_perm, mock_course_model, mock_can_manage, mock_remove
    ):
        """Returns error when service raises ValueError."""
        from courses.views import remove_student

        mock_course_model.objects.filter.return_value.first.return_value = (
            SimpleNamespace(id=1, status="ACTIVE")
        )

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "delete", "/api/v1/courses/1/students/5", user=user
        )

        response = remove_student(request, course_id=1, student_user_id=5)

        # "not found" in message triggers 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
