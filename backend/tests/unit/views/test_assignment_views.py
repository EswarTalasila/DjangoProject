"""Pure unit tests for assignment views (no database, mocked services)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from assignments.models import AudienceType
from core.dtos import AssignmentDTO

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
# create view
# ---------------------------------------------------------------------------


class TestCreateView:
    """Tests for the create assignment view."""

    @patch("assignments.views.assignment_to_dto")
    @patch("assignments.views.create_assignment")
    @patch("assignments.views.IsTeacher.has_permission", return_value=True)
    def test_creates_assignment_successfully(
        self, mock_perm, mock_create, mock_dto
    ):
        """POST creates assignment and returns 201 with DTO."""
        from assignments.views import create

        now = datetime(2025, 6, 1, tzinfo=UTC)
        fake_assignment = SimpleNamespace(id=1)
        mock_create.return_value = fake_assignment
        dto = AssignmentDTO(
            id=1, assessmentId=10, audienceType=AudienceType.COURSE,
            courseId=20, targetTeacherId=None, openAt=now, dueAt=None
        )
        mock_dto.return_value = dto

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assignments",
            data={
                "assessmentId": 10,
                "audienceType": "COURSE",
                "courseId": 20,
                "openAt": "2025-06-01T00:00:00Z",
            },
            user=user,
        )

        response = create(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["assessmentId"] == 10

    @patch(
        "assignments.views.create_assignment",
        side_effect=ValueError("courseId must be set"),
    )
    @patch("assignments.views.IsTeacher.has_permission", return_value=True)
    def test_handles_value_error(self, mock_perm, mock_create):
        """POST returns error when create_assignment raises ValueError."""
        from assignments.views import create

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post",
            "/api/v1/assignments",
            data={
                "assessmentId": 10,
                "audienceType": "COURSE",
                "openAt": "2025-06-01T00:00:00Z",
            },
            user=user,
        )

        response = create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("assignments.views.IsTeacher.has_permission", return_value=True)
    def test_invalid_payload_returns_400(self, mock_perm):
        """POST returns 400 for invalid serializer input."""
        from assignments.views import create

        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "post", "/api/v1/assignments", data={}, user=user
        )

        response = create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# detail view
# ---------------------------------------------------------------------------


class TestDetailView:
    """Tests for the detail assignment view."""

    @patch("assignments.views.get_assignment", return_value=None)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_returns_404_when_not_found(self, mock_perm, mock_get):
        """Returns 404 when assignment does not exist."""
        from assignments.views import detail

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignments/999", user=user)

        response = detail(request, assignment_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("assignments.views.assignment_to_dto")
    @patch("assignments.views.primary_role", return_value="TEACHER")
    @patch("assignments.views.get_assignment")
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_returns_dto_for_teacher(
        self, mock_perm, mock_get, mock_role, mock_dto
    ):
        """GET returns assignment DTO for teacher role."""
        from assignments.views import detail

        now = datetime(2025, 6, 1, tzinfo=UTC)
        fake_assignment = SimpleNamespace(
            id=1, assessment_id=10, audience_type="COURSE",
            course_id=20, teacher_id=None, open_at=now, due_at=None
        )
        mock_get.return_value = fake_assignment
        dto = AssignmentDTO(
            id=1, assessmentId=10, audienceType="COURSE",
            courseId=20, targetTeacherId=None, openAt=now, dueAt=None
        )
        mock_dto.return_value = dto

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignments/1", user=user)

        response = detail(request, assignment_id=1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == 1

    @patch("assignments.views.Enrollment")
    @patch("assignments.views.primary_role", return_value="STUDENT")
    @patch("assignments.views.get_assignment")
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_student_forbidden_when_not_enrolled(
        self, mock_perm, mock_get, mock_role, mock_enrollment_model
    ):
        """GET returns 403 for student not enrolled in assignment's course."""
        from assignments.views import detail

        fake_assignment = SimpleNamespace(id=1, course_id=10)
        mock_get.return_value = fake_assignment
        mock_enrollment_model.objects.filter.return_value.exists.return_value = False

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignments/1", user=user)

        response = detail(request, assignment_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignments.views.primary_role", return_value="STUDENT")
    @patch("assignments.views.get_assignment")
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_get_student_forbidden_when_no_course(
        self, mock_perm, mock_get, mock_role
    ):
        """GET returns 403 for student when assignment has no course."""
        from assignments.views import detail

        fake_assignment = SimpleNamespace(id=1, course_id=None)
        mock_get.return_value = fake_assignment

        user = MagicMock(is_authenticated=True)
        request = _authed_request("get", "/api/v1/assignments/1", user=user)

        response = detail(request, assignment_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignments.views.delete_assignment")
    @patch("assignments.views.IsTeacher")
    @patch("assignments.views.get_assignment")
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_delete_removes_assignment(
        self, mock_perm, mock_get, mock_is_teacher, mock_delete
    ):
        """DELETE removes assignment and returns 204."""
        from assignments.views import detail

        mock_is_teacher.return_value.has_permission.return_value = True
        fake_assignment = SimpleNamespace(id=1)
        mock_get.return_value = fake_assignment

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assignments/1", user=user)

        response = detail(request, assignment_id=1)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once_with(fake_assignment)

    @patch("assignments.views.IsTeacher")
    @patch("assignments.views.get_assignment")
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_delete_forbidden_for_non_teacher(
        self, mock_perm, mock_get, mock_is_teacher
    ):
        """DELETE returns 403 when user is not a teacher."""
        from assignments.views import detail

        mock_is_teacher.return_value.has_permission.return_value = False
        fake_assignment = SimpleNamespace(id=1)
        mock_get.return_value = fake_assignment

        user = MagicMock(is_authenticated=True)
        request = _authed_request("delete", "/api/v1/assignments/1", user=user)

        response = detail(request, assignment_id=1)

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# list_course view
# ---------------------------------------------------------------------------


class TestListCourseView:
    """Tests for the list_course assignment view."""

    @patch("assignments.views.paginate")
    @patch("assignments.views.list_by_course")
    @patch("assignments.views.IsTeacherOrAbove.has_permission", return_value=True)
    def test_lists_assignments_for_course(
        self, mock_perm, mock_list, mock_paginate
    ):
        """GET returns paginated assignments for a course."""
        from assignments.views import list_course

        mock_paginate.return_value = _paginated_response()
        user = MagicMock(is_authenticated=True)
        request = _authed_request(
            "get", "/api/v1/assignments/course/10", user=user
        )

        list_course(request, course_id=10)

        mock_list.assert_called_once_with(10)
        mock_paginate.assert_called_once()


# ---------------------------------------------------------------------------
# list_user view
# ---------------------------------------------------------------------------


class TestListUserView:
    """Tests for the list_user assignment view."""

    @patch("assignments.views.paginate")
    @patch("assignments.views.list_for_user")
    @patch("assignments.views.User")
    @patch("assignments.views.has_role", return_value=False)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_lists_own_assignments(
        self, mock_perm, mock_has_role, mock_user_model, mock_list, mock_paginate
    ):
        """GET returns assignments for the requesting user."""
        from assignments.views import list_user

        target = SimpleNamespace(id=42)
        mock_user_model.objects.filter.return_value.first.return_value = target
        mock_paginate.return_value = _paginated_response()

        user = MagicMock(is_authenticated=True, id=42, is_staff=False)
        request = _authed_request(
            "get", "/api/v1/assignments/user/42", user=user
        )

        list_user(request, user_id=42)

        mock_list.assert_called_once_with(target)

    @patch("assignments.views.has_role", return_value=False)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_forbidden_for_different_user(self, mock_perm, mock_has_role):
        """GET returns 403 when requesting another user's assignments (non-admin)."""
        from assignments.views import list_user

        user = MagicMock(is_authenticated=True, id=42, is_staff=False)
        request = _authed_request(
            "get", "/api/v1/assignments/user/99", user=user
        )

        response = list_user(request, user_id=99)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("assignments.views.paginate")
    @patch("assignments.views.list_for_user")
    @patch("assignments.views.User")
    @patch("assignments.views.has_role", return_value=False)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_admin_can_view_other_user_assignments(
        self, mock_perm, mock_has_role, mock_user_model, mock_list, mock_paginate
    ):
        """Admin (is_staff) can view any user's assignments."""
        from assignments.views import list_user

        target = SimpleNamespace(id=99)
        mock_user_model.objects.filter.return_value.first.return_value = target
        mock_paginate.return_value = _paginated_response()

        user = MagicMock(is_authenticated=True, id=1, is_staff=True)
        request = _authed_request(
            "get", "/api/v1/assignments/user/99", user=user
        )

        list_user(request, user_id=99)

        mock_list.assert_called_once_with(target)

    @patch("assignments.views.User")
    @patch("assignments.views.has_role", return_value=False)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_returns_404_when_user_not_found(
        self, mock_perm, mock_has_role, mock_user_model
    ):
        """Returns 404 when target user does not exist."""
        from assignments.views import list_user

        mock_user_model.objects.filter.return_value.first.return_value = None

        user = MagicMock(is_authenticated=True, id=1, is_staff=True)
        request = _authed_request(
            "get", "/api/v1/assignments/user/999", user=user
        )

        response = list_user(request, user_id=999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("assignments.views.paginate")
    @patch("assignments.views.list_for_user")
    @patch("assignments.views.User")
    @patch("assignments.views.has_role", return_value=True)
    @patch("assignments.views.IsAuthenticated.has_permission", return_value=True)
    def test_researcher_can_view_other_user_assignments(
        self, mock_perm, mock_has_role, mock_user_model, mock_list, mock_paginate
    ):
        """Researcher can view any user's assignments."""
        from assignments.views import list_user

        target = SimpleNamespace(id=99)
        mock_user_model.objects.filter.return_value.first.return_value = target
        mock_paginate.return_value = _paginated_response()

        user = MagicMock(is_authenticated=True, id=2, is_staff=False)
        request = _authed_request(
            "get", "/api/v1/assignments/user/99", user=user
        )

        list_user(request, user_id=99)

        mock_list.assert_called_once_with(target)
