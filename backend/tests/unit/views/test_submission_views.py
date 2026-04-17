"""Unit tests for submissions.views endpoint logic.

All service calls and ORM lookups are mocked. Tests focus on:
- Permission/role gating
- Input validation & error responses
- Status codes for each code path

DRF views are decorated with ``@api_view`` and ``@permission_classes``, so we
use ``APIRequestFactory`` with ``force_authenticate`` to bypass token/session
auth while still exercising the permission logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

factory = APIRequestFactory()


def _user(*, id=1, is_staff=False, role=Role.STUDENT, is_authenticated=True):
    """Build a mock user with role support for permission checks."""
    user = MagicMock()
    user.id = id
    user.pk = id
    user.is_staff = is_staff
    user.is_authenticated = is_authenticated
    user.is_active = True
    user.is_anonymous = False
    # _cached_role_set is consumed by core.permissions._role_set
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


def _mock_submission_dto():
    """Return a mock DTO whose model_dump() returns a serializable dict."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "id": 1,
        "assignmentId": 10,
        "studentId": 100,
        "teacherId": None,
        "submittedAt": None,
        "score": None,
        "status": "SUBMITTED",
        "answers": [],
    }
    return dto


def _mock_assignment(*, id=10, teacher_id=1, course=None, course_id=None, status="ACTIVE", open_at=None):
    """Build a mock assignment."""
    a = MagicMock()
    a.id = id
    a.teacher_id = teacher_id
    a.course = course
    a.course_id = course_id
    a.status = status
    a.open_at = open_at
    return a


# ============================================================================
# create_for_assignment
# ============================================================================


class TestCreateForAssignment:
    """Tests for the create_for_assignment view."""

    @patch("submissions.views._assignment_for")
    def test_returns_404_when_assignment_not_found(self, mock_assign_for):
        """Returns 404 when assignment does not exist."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = None
        user = _user(role=Role.STUDENT)
        request = _authed_request("post", "/submissions/assignments/999/", {}, user=user)

        response = create_for_assignment(request, 999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_submission_for_dto")
    @patch("submissions.views.create_submission")
    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_can_create_own_submission(self, mock_assign_for, mock_enrolled, mock_create, mock_refetch, mock_dto):
        """Student creating their own submission gets 201."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = _mock_assignment()
        mock_enrolled.return_value = True
        mock_create.return_value = MagicMock()
        mock_refetch.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=100, role=Role.STUDENT)
        data = {
            "assignmentId": 10,
            "studentId": 100,
            "status": "SUBMITTED",
            "answers": [],
        }
        request = _authed_request("post", "/submissions/", data, user=user)

        response = create_for_assignment(request, 10)

        assert response.status_code == http_status.HTTP_201_CREATED

    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_cannot_create_for_other(self, mock_assign_for, mock_enrolled):
        """Student gets 403 when trying to submit as another student."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = _mock_assignment()
        mock_enrolled.return_value = True

        user = _user(id=100, role=Role.STUDENT)
        data = {
            "assignmentId": 10,
            "studentId": 999,
            "status": "SUBMITTED",
        }
        request = _authed_request("post", "/submissions/", data, user=user)

        response = create_for_assignment(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_not_enrolled_gets_403(self, mock_assign_for, mock_enrolled):
        """Student who is not enrolled in the course gets 403."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = _mock_assignment()
        mock_enrolled.return_value = False

        user = _user(id=100, role=Role.STUDENT)
        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED"}
        request = _authed_request("post", "/submissions/", data, user=user)

        response = create_for_assignment(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views._assignment_for")
    def test_teacher_gets_403(self, mock_assign_for):
        """Teachers cannot create student submissions via this endpoint."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=200, role=Role.TEACHER)
        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED"}
        request = _authed_request("post", "/submissions/", data, user=user)

        response = create_for_assignment(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# get_one
# ============================================================================


class TestGetOne:
    """Tests for the get_one submission retrieval view."""

    @patch("submissions.views.get_submission_for_dto")
    def test_returns_404_when_not_found(self, mock_get):
        """Returns 404 when submission does not exist."""
        from submissions.views import get_one

        mock_get.side_effect = ValueError("Submission not found")

        user = _user()
        request = _authed_request("get", "/submissions/999/", user=user)

        response = get_one(request, 999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views._can_access_submission")
    @patch("submissions.views.get_submission_for_dto")
    def test_returns_200_for_authorized_user(self, mock_get, mock_access, mock_dto):
        """Returns 200 with submission DTO for authorized user."""
        from submissions.views import get_one

        sub = MagicMock()
        mock_get.return_value = sub
        mock_access.return_value = True
        mock_dto.return_value = _mock_submission_dto()

        user = _user()
        request = _authed_request("get", "/submissions/1/", user=user)

        response = get_one(request, 1)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views._can_access_submission")
    @patch("submissions.views.get_submission_for_dto")
    def test_returns_403_for_unauthorized_user(self, mock_get, mock_access):
        """Returns 403 when user cannot access the submission."""
        from submissions.views import get_one

        mock_get.return_value = MagicMock()
        mock_access.return_value = False

        user = _user()
        request = _authed_request("get", "/submissions/1/", user=user)

        response = get_one(request, 1)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# _can_access_submission (helper tests -- no auth needed)
# ============================================================================


class TestCanAccessSubmission:
    """Tests for the _can_access_submission permission helper."""

    def test_admin_always_has_access(self):
        """Admins (is_staff) can access any submission."""
        from submissions.views import _can_access_submission

        user = _user(is_staff=True, role=Role.STUDENT)
        sub = MagicMock()

        assert _can_access_submission(user, sub) is True

    @patch("submissions.views.has_sudo_permission")
    def test_researcher_has_access(self, mock_sudo):
        """Researchers with sudo permission can access any submission."""
        from submissions.views import _can_access_submission

        mock_sudo.return_value = True
        user = _user(role=Role.RESEARCHER)
        sub = MagicMock()

        assert _can_access_submission(user, sub) is True

    def test_student_can_access_own(self):
        """Student can access their own submission."""
        from submissions.views import _can_access_submission

        user = _user(id=100, role=Role.STUDENT)
        sub = MagicMock()
        sub.student_id = 100

        assert _can_access_submission(user, sub) is True

    def test_student_cannot_access_others(self):
        """Student cannot access another student's submission."""
        from submissions.views import _can_access_submission

        user = _user(id=100, role=Role.STUDENT)
        sub = MagicMock()
        sub.student_id = 999

        assert _can_access_submission(user, sub) is False

    @patch("submissions.views.teacher_owns_assignment")
    def test_teacher_can_access_owned_assignment(self, mock_owns):
        """Teacher can access submissions for assignments they own."""
        from submissions.views import _can_access_submission

        mock_owns.return_value = True
        user = _user(id=200, role=Role.TEACHER)
        sub = MagicMock()

        assert _can_access_submission(user, sub) is True

    @patch("submissions.views.teacher_owns_assignment")
    def test_teacher_cannot_access_unowned_assignment(self, mock_owns):
        """Teacher cannot access submissions for assignments they do not own."""
        from submissions.views import _can_access_submission

        mock_owns.return_value = False
        user = _user(id=200, role=Role.TEACHER)
        sub = MagicMock()

        assert _can_access_submission(user, sub) is False


# ============================================================================
# _teacher_owns_assignment (helper tests -- no auth needed)
# ============================================================================


class TestTeacherOwnsAssignment:
    """Tests for the _teacher_owns_assignment helper."""

    def test_direct_teacher_id_match(self):
        """Returns True when assignment.teacher_id matches user.id."""
        from submissions.views import _teacher_owns_assignment

        user = _user(id=5)
        assignment = _mock_assignment(teacher_id=5)

        assert _teacher_owns_assignment(user, assignment) is True

    def test_course_teacher_profile_match(self):
        """Returns True when the course teacher profile matches the user."""
        from submissions.views import _teacher_owns_assignment

        user = _user(id=5)
        course = MagicMock()
        course.teacher_profile = MagicMock()
        course.teacher_profile.user_id = 5
        assignment = _mock_assignment(teacher_id=999, course=course)

        assert _teacher_owns_assignment(user, assignment) is True

    def test_no_match(self):
        """Returns False when neither direct nor course match."""
        from submissions.views import _teacher_owns_assignment

        user = _user(id=5)
        course = MagicMock()
        course.teacher_profile = MagicMock()
        course.teacher_profile.user_id = 999
        assignment = _mock_assignment(teacher_id=888, course=course)

        assert _teacher_owns_assignment(user, assignment) is False

    def test_no_course(self):
        """Returns False when assignment has no course."""
        from submissions.views import _teacher_owns_assignment

        user = _user(id=5)
        assignment = _mock_assignment(teacher_id=999, course=None)

        assert _teacher_owns_assignment(user, assignment) is False


# ============================================================================
# _student_enrolled_in_assignment
# ============================================================================


class TestStudentEnrolledInAssignment:
    """Tests for the _student_enrolled_in_assignment helper."""

    def test_returns_false_when_no_course(self):
        """Returns False when assignment has no associated course."""
        from submissions.views import _student_enrolled_in_assignment

        user = _user(id=100)
        assignment = _mock_assignment(course_id=None)

        assert _student_enrolled_in_assignment(user, assignment) is False

    @patch("submissions.views.Enrollment")
    def test_returns_true_when_enrolled(self, mock_enrollment):
        """Returns True when enrollment exists for the student and course."""
        from submissions.views import _student_enrolled_in_assignment

        mock_enrollment.objects.filter.return_value.exists.return_value = True
        user = _user(id=100)
        assignment = _mock_assignment(course_id=50)

        assert _student_enrolled_in_assignment(user, assignment) is True

    @patch("submissions.views.Enrollment")
    def test_returns_false_when_not_enrolled(self, mock_enrollment):
        """Returns False when no enrollment exists."""
        from submissions.views import _student_enrolled_in_assignment

        mock_enrollment.objects.filter.return_value.exists.return_value = False
        user = _user(id=100)
        assignment = _mock_assignment(course_id=50)

        assert _student_enrolled_in_assignment(user, assignment) is False


# ============================================================================
# list_me_view
# ============================================================================


class TestListMeView:
    """Tests for the list_me_view endpoint."""

    @patch("submissions.views.paginate")
    @patch("submissions.views.list_me")
    def test_returns_own_submissions(self, mock_list, mock_paginate):
        """Returns submissions for the authenticated user."""
        from submissions.views import list_me_view

        mock_list.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/mine/", user=user)

        list_me_view(request)

        mock_list.assert_called_once_with(100, None)

    @patch("submissions.views.paginate")
    @patch("submissions.views.list_me")
    def test_passes_status_filter(self, mock_list, mock_paginate):
        """Status query param is forwarded to service."""
        from submissions.views import list_me_view

        mock_list.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/mine/?status=GRADED", user=user)

        list_me_view(request)

        mock_list.assert_called_once_with(100, "GRADED")

    @patch("submissions.views.has_sudo_permission")
    def test_researcher_without_sudo_gets_403(self, mock_sudo):
        """Researcher without sudo permission gets 403."""
        from submissions.views import list_me_view

        mock_sudo.return_value = False
        user = _user(id=100, role=Role.RESEARCHER)
        request = _authed_request("get", "/submissions/mine/", user=user)

        response = list_me_view(request)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# override_score_view
# ============================================================================


class TestOverrideScoreView:
    """Tests for the override_score_view endpoint."""

    def test_returns_400_when_body_not_list(self):
        """Returns 400 when request body is not a list."""
        from submissions.views import override_score_view

        user = _user(id=1, is_staff=True)
        request = _authed_request("patch", "/submissions/1/score/", {"score": 10}, user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_returns_403_for_student(self):
        """Students cannot override scores."""
        from submissions.views import override_score_view

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("patch", "/submissions/1/score/", [10], user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.Submission")
    def test_returns_404_when_submission_not_found(self, mock_sub_model):
        """Returns 404 when submission does not exist."""
        from submissions.views import override_score_view

        mock_sub_model.objects.filter.return_value.select_related.return_value.first.return_value = None

        user = _user(id=1, is_staff=True)
        request = _authed_request("patch", "/submissions/999/score/", [10], user=user)

        response = override_score_view(request, 999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_submission_for_dto")
    @patch("submissions.views.override_score")
    @patch("submissions.views.Submission")
    def test_admin_can_override(self, mock_sub_model, mock_override, mock_refetch, mock_dto):
        """Admin can override scores on any submission."""
        from submissions.views import override_score_view

        sub = MagicMock()
        sub.assignment = _mock_assignment()
        mock_sub_model.objects.filter.return_value.select_related.return_value.first.return_value = sub
        mock_refetch.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=1, is_staff=True)
        request = _authed_request("patch", "/submissions/1/score/", [10, 8], user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views.Submission")
    def test_teacher_not_owning_gets_403(self, mock_sub_model, mock_owns):
        """Teacher who does not own the assignment gets 403."""
        from submissions.views import override_score_view

        sub = MagicMock()
        sub.assignment = _mock_assignment()
        mock_sub_model.objects.filter.return_value.select_related.return_value.first.return_value = sub
        mock_owns.return_value = False

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("patch", "/submissions/1/score/", [10], user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# get_by_student_id
# ============================================================================


class TestGetByStudentId:
    """Tests for the get_by_student_id view."""

    def test_student_cannot_view_other_student(self):
        """Student cannot view another student's submissions."""
        from submissions.views import get_by_student_id

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/999/", user=user)

        response = get_by_student_id(request, 999)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_student")
    def test_student_can_view_own(self, mock_get, mock_paginate):
        """Student can view their own submissions."""
        from submissions.views import get_by_student_id

        mock_get.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/100/", user=user)

        get_by_student_id(request, 100)

        mock_get.assert_called_once_with(100)


# ============================================================================
# save_draft
# ============================================================================


class TestSaveDraft:
    """Tests for the save_draft view."""

    @patch("submissions.views._assignment_for")
    def test_returns_404_when_assignment_missing(self, mock_assign_for):
        """Returns 404 when assignment does not exist."""
        from submissions.views import save_draft

        mock_assign_for.return_value = None

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("patch", "/submissions/students/100/assignments/999/draft/", {}, user=user)

        response = save_draft(request, 100, 999)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_not_enrolled_gets_403(self, mock_assign_for, mock_enrolled):
        """Student not enrolled in the course gets 403."""
        from submissions.views import save_draft

        mock_assign_for.return_value = _mock_assignment(course_id=50)
        mock_enrolled.return_value = False

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("patch", "/submissions/students/100/assignments/10/draft/", {}, user=user)

        response = save_draft(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views._assignment_for")
    def test_teacher_gets_403(self, mock_assign_for):
        """Teachers cannot save drafts (they use teacher_self_assess)."""
        from submissions.views import save_draft

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("patch", "/submissions/students/100/assignments/10/draft/", {}, user=user)

        response = save_draft(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_admin_non_student_gets_403(self):
        """Admin who is not a student cannot save drafts (student-only endpoint)."""
        from submissions.views import save_draft

        user = _user(id=1, is_staff=True)
        request = _authed_request(
            "patch",
            "/submissions/students/100/assignments/10/draft/",
            {"answers": []},
            user=user,
        )

        response = save_draft(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views._assignment_for")
    def test_student_cannot_save_for_other_student(self, mock_assign_for):
        """Student gets 403 when saving draft for another student."""
        from submissions.views import save_draft

        mock_assign_for.return_value = _mock_assignment(course_id=50)

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request(
            "patch",
            "/submissions/students/999/assignments/10/draft/",
            {"answers": []},
            user=user,
        )

        response = save_draft(request, 999, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.create_submission")
    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_value_error_from_create_returns_error(self, mock_assign_for, mock_enrolled, mock_create):
        """Returns error response when create_submission raises ValueError."""
        from submissions.views import save_draft

        mock_assign_for.return_value = _mock_assignment(course_id=50)
        mock_enrolled.return_value = True
        mock_create.side_effect = ValueError("Submission already exists")

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request(
            "patch",
            "/submissions/students/100/assignments/10/draft/",
            {"answers": []},
            user=user,
        )

        response = save_draft(request, 100, 10)

        assert response.status_code in (
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_404_NOT_FOUND,
        )


# ============================================================================
# assignment_submissions (GET & POST combined endpoint)
# ============================================================================


class TestAssignmentSubmissions:
    """Tests for the assignment_submissions dual-method view."""

    @patch("submissions.views._assignment_for")
    def test_post_returns_404_when_assignment_missing(self, mock_assign_for):
        """POST returns 404 when assignment does not exist."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = None

        user = _user(id=100, role=Role.STUDENT)
        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED", "answers": []}
        request = _authed_request("post", "/submissions/assignments/10/", data, user=user)

        response = assignment_submissions(request, 10)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_submission_for_dto")
    @patch("submissions.views.create_submission")
    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_post_creates_submission(self, mock_assign_for, mock_enrolled, mock_create, mock_refetch, mock_dto):
        """POST creates a submission and returns 201."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = _mock_assignment()
        mock_enrolled.return_value = True
        mock_create.return_value = MagicMock()
        mock_refetch.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=100, role=Role.STUDENT)
        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED", "answers": []}
        request = _authed_request("post", "/submissions/assignments/10/", data, user=user)

        response = assignment_submissions(request, 10)

        assert response.status_code == http_status.HTTP_201_CREATED

    @patch("submissions.views._assignment_for")
    def test_get_returns_404_when_assignment_missing(self, mock_assign_for):
        """GET returns 404 when assignment does not exist."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = None

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        response = assignment_submissions(request, 10)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views._assignment_for")
    def test_get_student_gets_403(self, mock_assign_for):
        """GET as student returns 403 (students use get_student_submission)."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        response = assignment_submissions(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_get_teacher_owns_returns_paginated(
        self, mock_assign_for, mock_owns, mock_get_by, mock_paginate
    ):
        """GET as teacher who owns assignment returns paginated results."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = _mock_assignment(teacher_id=200)
        mock_owns.return_value = True
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        assignment_submissions(request, 10)

        mock_get_by.assert_called_once_with(10)

    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_get_teacher_not_owning_gets_403(self, mock_assign_for, mock_owns):
        """GET as teacher who does not own the assignment returns 403."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = _mock_assignment(teacher_id=999)
        mock_owns.return_value = False

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        response = assignment_submissions(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views._assignment_for")
    def test_get_admin_can_view_any_assignment(self, mock_assign_for, mock_get_by, mock_paginate):
        """GET as admin can view any assignment's submissions."""
        from submissions.views import assignment_submissions

        mock_assign_for.return_value = _mock_assignment(teacher_id=999)
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, is_staff=True, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        assignment_submissions(request, 10)

        mock_get_by.assert_called_once_with(10)

    @patch("submissions.views.has_sudo_permission")
    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views._assignment_for")
    def test_get_researcher_can_view_any_assignment(self, mock_assign_for, mock_get_by, mock_paginate, mock_sudo):
        """GET as researcher can view any assignment's submissions."""
        from submissions.views import assignment_submissions

        mock_sudo.return_value = True
        mock_assign_for.return_value = _mock_assignment(teacher_id=999)
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, role=Role.RESEARCHER)
        request = _authed_request("get", "/submissions/assignments/10/", user=user)

        assignment_submissions(request, 10)

        mock_get_by.assert_called_once_with(10)


# ============================================================================
# get_by_assignment_id
# ============================================================================


class TestGetByAssignmentId:
    """Tests for the get_by_assignment_id view."""

    @patch("submissions.views._assignment_for")
    def test_returns_404_when_assignment_missing(self, mock_assign_for):
        """Returns 404 when assignment does not exist."""
        from submissions.views import get_by_assignment_id

        mock_assign_for.return_value = None

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        response = get_by_assignment_id(request, 10)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views._assignment_for")
    def test_student_gets_403(self, mock_assign_for):
        """Student cannot list all submissions for an assignment."""
        from submissions.views import get_by_assignment_id

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        response = get_by_assignment_id(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_teacher_not_owning_gets_403(self, mock_assign_for, mock_owns):
        """Teacher who does not own the assignment gets 403."""
        from submissions.views import get_by_assignment_id

        mock_assign_for.return_value = _mock_assignment(teacher_id=999)
        mock_owns.return_value = False

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        response = get_by_assignment_id(request, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_teacher_owning_gets_paginated(self, mock_assign_for, mock_owns, mock_get_by, mock_paginate):
        """Teacher who owns the assignment gets paginated results."""
        from submissions.views import get_by_assignment_id

        mock_assign_for.return_value = _mock_assignment(teacher_id=200)
        mock_owns.return_value = True
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        get_by_assignment_id(request, 10)

        mock_get_by.assert_called_once_with(10)

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views._assignment_for")
    def test_admin_can_view_any(self, mock_assign_for, mock_get_by, mock_paginate):
        """Admin can view any assignment's submissions."""
        from submissions.views import get_by_assignment_id

        mock_assign_for.return_value = _mock_assignment()
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, is_staff=True)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        get_by_assignment_id(request, 10)

        mock_get_by.assert_called_once_with(10)

    @patch("submissions.views.has_sudo_permission")
    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_assignment")
    @patch("submissions.views._assignment_for")
    def test_researcher_can_view_any(self, mock_assign_for, mock_get_by, mock_paginate, mock_sudo):
        """Researcher can view any assignment's submissions."""
        from submissions.views import get_by_assignment_id

        mock_sudo.return_value = True
        mock_assign_for.return_value = _mock_assignment()
        mock_get_by.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, role=Role.RESEARCHER)
        request = _authed_request("get", "/submissions/by-assignment/10/", user=user)

        get_by_assignment_id(request, 10)

        mock_get_by.assert_called_once_with(10)


# ============================================================================
# get_by_student_id (extended coverage for admin, researcher, teacher paths)
# ============================================================================


class TestGetByStudentIdExtended:
    """Extended tests for the get_by_student_id view covering uncovered paths."""

    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_student")
    def test_admin_can_view_any_student(self, mock_get, mock_paginate):
        """Admin can view any student's submissions (is_staff bypass)."""
        from submissions.views import get_by_student_id

        mock_get.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, is_staff=True)
        request = _authed_request("get", "/submissions/students/999/", user=user)

        get_by_student_id(request, 999)

        mock_get.assert_called_once_with(999)

    @patch("submissions.views.has_sudo_permission")
    @patch("submissions.views.paginate")
    @patch("submissions.views.get_by_student")
    def test_researcher_can_view_any_student(self, mock_get, mock_paginate, mock_sudo):
        """Researcher can view any student's submissions."""
        from submissions.views import get_by_student_id

        mock_sudo.return_value = True
        mock_get.return_value = []
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=1, role=Role.RESEARCHER)
        request = _authed_request("get", "/submissions/students/999/", user=user)

        get_by_student_id(request, 999)

        mock_get.assert_called_once_with(999)

    @patch("submissions.views.paginate")
    @patch("submissions.views.Submission")
    def test_teacher_owning_student_can_view(self, mock_sub_model, mock_paginate):
        """Teacher who owns the student (via assignment course) can view their submissions."""
        from submissions.views import get_by_student_id

        owned_qs = MagicMock()
        owned_qs.exists.return_value = True
        mock_sub_model.objects.filter.return_value = owned_qs
        mock_paginate.return_value = Response([], status=200)

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/students/100/", user=user)

        get_by_student_id(request, 100)

        mock_paginate.assert_called_once()

    @patch("submissions.views.Submission")
    def test_teacher_no_owned_submissions_gets_403(self, mock_sub_model):
        """Teacher with no owned submissions for the student gets 403."""
        from submissions.views import get_by_student_id

        owned_qs = MagicMock()
        owned_qs.exists.return_value = False
        mock_sub_model.objects.filter.return_value = owned_qs

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/students/100/", user=user)

        response = get_by_student_id(request, 100)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_unknown_role_gets_403(self):
        """User with unrecognized role gets 403."""
        from submissions.views import get_by_student_id

        user = _user(id=300, role="UNKNOWN")
        request = _authed_request("get", "/submissions/students/100/", user=user)

        response = get_by_student_id(request, 100)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# get_student_submission
# ============================================================================


class TestGetStudentSubmission:
    """Tests for the get_student_submission view."""

    @patch("submissions.views._assignment_for")
    def test_returns_404_when_assignment_missing(self, mock_assign_for):
        """Returns 404 when assignment does not exist."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = None

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_by_student_and_assignment_for_dto")
    @patch("submissions.views._assignment_for")
    def test_admin_can_view_any(self, mock_assign_for, mock_get, mock_dto):
        """Admin can view any student's submission for any assignment."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment()
        mock_get.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=1, is_staff=True)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views.has_sudo_permission")
    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_by_student_and_assignment_for_dto")
    @patch("submissions.views._assignment_for")
    def test_researcher_can_view_any(self, mock_assign_for, mock_get, mock_dto, mock_sudo):
        """Researcher with sudo can view any student's submission."""
        from submissions.views import get_student_submission

        mock_sudo.return_value = True
        mock_assign_for.return_value = _mock_assignment()
        mock_get.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=1, role=Role.RESEARCHER)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_cannot_view_other_students(self, mock_assign_for, mock_enrolled):
        """Student cannot view another student's submission."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/999/assignments/10/", user=user)

        response = get_student_submission(request, 999, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_not_enrolled_gets_403(self, mock_assign_for, mock_enrolled):
        """Student not enrolled in assignment's course gets 403."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment(course_id=50)
        mock_enrolled.return_value = False

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_by_student_and_assignment_for_dto")
    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_student_enrolled_can_view_own(self, mock_assign_for, mock_enrolled, mock_get, mock_dto):
        """Enrolled student can view their own submission."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment(course_id=50)
        mock_enrolled.return_value = True
        mock_get.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=100, role=Role.STUDENT)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_teacher_not_owning_gets_403(self, mock_assign_for, mock_owns):
        """Teacher who does not own the assignment gets 403."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment(teacher_id=999)
        mock_owns.return_value = False

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_by_student_and_assignment_for_dto")
    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views._assignment_for")
    def test_teacher_owning_can_view(self, mock_assign_for, mock_owns, mock_get, mock_dto):
        """Teacher who owns the assignment can view student submission."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment(teacher_id=200)
        mock_owns.return_value = True
        mock_get.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views._assignment_for")
    def test_unknown_role_gets_403(self, mock_assign_for):
        """User with unrecognized role gets 403."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment()

        user = _user(id=300, role="UNKNOWN")
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @patch("submissions.views.get_by_student_and_assignment_for_dto")
    @patch("submissions.views._assignment_for")
    def test_value_error_returns_error_response(self, mock_assign_for, mock_get):
        """ValueError from service returns error response."""
        from submissions.views import get_student_submission

        mock_assign_for.return_value = _mock_assignment()
        mock_get.side_effect = ValueError("Submission not found")

        user = _user(id=1, is_staff=True)
        request = _authed_request("get", "/submissions/students/100/assignments/10/", user=user)

        response = get_student_submission(request, 100, 10)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND




# ============================================================================
# override_score_view (extended coverage)
# ============================================================================


class TestOverrideScoreViewExtended:
    """Extended tests for override_score_view covering uncovered branches."""

    @patch("submissions.views.submission_to_dto")
    @patch("submissions.views.get_submission_for_dto")
    @patch("submissions.views.override_score")
    @patch("submissions.views.teacher_owns_assignment")
    @patch("submissions.views.Submission")
    def test_teacher_owning_can_override(self, mock_sub_model, mock_owns, mock_override, mock_refetch, mock_dto):
        """Teacher who owns the assignment can override scores."""
        from submissions.views import override_score_view

        sub = MagicMock()
        sub.assignment = _mock_assignment(teacher_id=200)
        mock_sub_model.objects.filter.return_value.select_related.return_value.first.return_value = sub
        mock_owns.return_value = True
        mock_refetch.return_value = MagicMock()
        mock_dto.return_value = _mock_submission_dto()

        user = _user(id=200, role=Role.TEACHER)
        request = _authed_request("patch", "/submissions/1/score/", [{"answerId": 1, "score": 10}], user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_200_OK

    @patch("submissions.views.override_score")
    @patch("submissions.views.Submission")
    def test_value_error_returns_error_response(self, mock_sub_model, mock_override):
        """ValueError from override_score returns error response."""
        from submissions.views import override_score_view

        sub = MagicMock()
        sub.assignment = _mock_assignment()
        mock_sub_model.objects.filter.return_value.select_related.return_value.first.return_value = sub
        mock_override.side_effect = ValueError("Answer not found")

        user = _user(id=1, is_staff=True)
        request = _authed_request("patch", "/submissions/1/score/", [{"answerId": 1, "score": 10}], user=user)

        response = override_score_view(request, 1)

        assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# _create_for_assignment (extended coverage for teacher and error paths)
# ============================================================================


class TestCreateForAssignmentExtended:
    """Extended tests for _create_for_assignment covering uncovered paths."""

    @patch("submissions.views.create_submission")
    @patch("submissions.views._student_enrolled_in_assignment")
    @patch("submissions.views._assignment_for")
    def test_value_error_from_create_returns_error(self, mock_assign_for, mock_enrolled, mock_create):
        """Returns error response when create_submission raises ValueError."""
        from submissions.views import create_for_assignment

        mock_assign_for.return_value = _mock_assignment()
        mock_enrolled.return_value = True
        mock_create.side_effect = ValueError("Duplicate submission")

        user = _user(id=100, role=Role.STUDENT)
        data = {"assignmentId": 10, "studentId": 100, "status": "SUBMITTED", "answers": []}
        request = _authed_request("post", "/submissions/assignments/10/", data, user=user)

        response = create_for_assignment(request, 10)

        assert response.status_code in (
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_404_NOT_FOUND,
        )
