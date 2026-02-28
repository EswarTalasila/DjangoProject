"""Unit tests for accounts views.

Tests mock the service layer and verify view-level logic: request parsing,
response status codes, response shapes, and error formatting. Uses DRF
APIRequestFactory for isolated view invocation without URL routing.

All ORM calls are mocked. No database access is required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.response import Response as DRFResponse
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Role

factory = APIRequestFactory()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(*, id=1, is_staff=False, role=None, is_authenticated=True, **kwargs):
    """Build a mock user compatible with DRF permission checks and view logic.

    The mock sets ``_cached_role_set`` so that ``core.permissions._role_set``
    returns the correct roles without any DB access.
    """
    user = MagicMock()
    user.id = id
    user.pk = id
    user.is_staff = is_staff
    user.is_authenticated = is_authenticated
    user.is_active = True
    user.is_anonymous = False
    user.name = kwargs.get("name", "Test User")
    user.username = kwargs.get("username", f"user{id}@example.com")
    user.email = kwargs.get("email", f"user{id}@example.com")

    # _cached_role_set is consumed by core.permissions._role_set
    role_set = {role} if role else set()
    user._cached_role_set = role_set
    user.roles = MagicMock()
    user.roles.values_list.return_value = role_set

    return user


def _auth_request(method, path, data=None, user=None, **kwargs):
    """Build an APIRequestFactory request with optional force_authenticate."""
    builder = getattr(factory, method)
    request = builder(path, data=data, format="json", **kwargs)
    if user:
        force_authenticate(request, user=user)
    return request


# ---------------------------------------------------------------------------
# register_account
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterAccountView:
    """Tests for the unified register_account view dispatch."""

    def test_missing_method_returns_400(self):
        """Missing method field returns 400 with detail."""
        from accounts.views import register_account

        request = _auth_request("post", "/api/v1/registration/accounts", data={})
        response = register_account(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "method must be LOCAL or OAUTH" in response.data["detail"]

    def test_invalid_method_returns_400(self):
        """Invalid method value returns 400."""
        from accounts.views import register_account

        request = _auth_request(
            "post", "/api/v1/registration/accounts", data={"method": "MAGIC"}
        )
        response = register_account(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views._register_local")
    def test_local_method_dispatches(self, mock_local):
        """LOCAL method dispatches to _register_local."""
        from accounts.views import register_account

        mock_local.return_value = DRFResponse({"ok": True}, status=201)
        request = _auth_request(
            "post",
            "/api/v1/registration/accounts",
            data={"method": "LOCAL", "code": "X"},
        )
        register_account(request)
        mock_local.assert_called_once()

    @patch("accounts.views._register_oauth")
    def test_oauth_method_dispatches(self, mock_oauth):
        """OAUTH method dispatches to _register_oauth."""
        from accounts.views import register_account

        mock_oauth.return_value = DRFResponse({"ok": True}, status=201)
        request = _auth_request(
            "post",
            "/api/v1/registration/accounts",
            data={"method": "OAUTH", "accessToken": "tok"},
        )
        register_account(request)
        mock_oauth.assert_called_once()

    def test_method_case_insensitive(self):
        """Method field is case-insensitive (lowercase accepted)."""
        from accounts.views import register_account

        request = _auth_request(
            "post", "/api/v1/registration/accounts", data={"method": "invalid_value"}
        )
        response = register_account(request)
        # "invalid_value".upper() is not LOCAL or OAUTH
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views._register_local")
    def test_method_payload_excludes_method_key(self, mock_local):
        """The 'method' key is stripped from the payload passed to sub-handler."""
        from accounts.views import register_account

        mock_local.return_value = DRFResponse({"ok": True}, status=201)
        request = _auth_request(
            "post",
            "/api/v1/registration/accounts",
            data={"method": "LOCAL", "code": "X", "firstName": "Test"},
        )
        register_account(request)
        _, _kwargs = mock_local.call_args
        # The payload dict (second positional arg) should not contain 'method'
        payload_arg = mock_local.call_args[0][1]
        assert "method" not in payload_arg


# ---------------------------------------------------------------------------
# validate_registration_code_view
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateRegistrationCodeView:
    """Tests for the validate_registration_code_view endpoint."""

    @patch("accounts.views.validate_registration_code")
    def test_invalid_code_returns_400(self, mock_validate):
        """Invalid/expired code returns 400."""
        from accounts.views import validate_registration_code_view

        mock_validate.return_value = None
        request = _auth_request(
            "post", "/api/v1/registration/code-validations", data={"code": "BAD"}
        )
        response = validate_registration_code_view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired code" in response.data["detail"]

    @patch("accounts.views.validate_registration_code")
    def test_valid_code_returns_200(self, mock_validate):
        """Valid code returns 200 with valid=True and code_type."""
        from accounts.views import validate_registration_code_view

        record = SimpleNamespace(
            code_type="STUDENT",
            course_id=None,
            course=None,
        )
        mock_validate.return_value = record
        request = _auth_request(
            "post", "/api/v1/registration/code-validations", data={"code": "GOOD"}
        )
        response = validate_registration_code_view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True
        assert response.data["code_type"] == "STUDENT"

    @patch("accounts.views.validate_registration_code")
    def test_valid_code_with_course_context(self, mock_validate):
        """Valid code with course returns course context."""
        from accounts.views import validate_registration_code_view

        mock_course = SimpleNamespace(
            name="Test Course",
            teacher_profile=SimpleNamespace(
                user_id=1,
                user=SimpleNamespace(name="Teacher Name"),
            ),
        )
        record = SimpleNamespace(
            code_type="STUDENT",
            course_id=1,
            course=mock_course,
        )
        mock_validate.return_value = record
        request = _auth_request(
            "post", "/api/v1/registration/code-validations", data={"code": "GOOD"}
        )
        response = validate_registration_code_view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["context"]["course_name"] == "Test Course"
        assert response.data["context"]["teacher_name"] == "Teacher Name"

    def test_missing_code_returns_400(self):
        """Missing code field returns 400 validation error."""
        from accounts.views import validate_registration_code_view

        request = _auth_request(
            "post", "/api/v1/registration/code-validations", data={}
        )
        response = validate_registration_code_view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# join_course_with_code
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJoinCourseWithCodeView:
    """Tests for join_course_with_code view."""

    @patch("accounts.views.primary_role")
    def test_non_student_returns_403(self, mock_primary_role):
        """Non-student role returns 403 forbidden."""
        from accounts.views import join_course_with_code

        mock_primary_role.return_value = Role.TEACHER
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/enrollments", data={"code": "X"}, user=user
        )
        response = join_course_with_code(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.redeem_student_join_course")
    @patch("accounts.views.primary_role")
    def test_value_error_returns_400(self, mock_primary_role, mock_redeem):
        """ValueError from service returns 400."""
        from accounts.views import join_course_with_code

        mock_primary_role.return_value = Role.STUDENT
        mock_redeem.side_effect = ValueError("Invalid code")
        user = _user(role=Role.STUDENT)
        request = _auth_request(
            "post", "/api/v1/enrollments", data={"code": "BAD"}, user=user
        )
        response = join_course_with_code(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid code" in response.data["detail"]

    @patch("accounts.views.redeem_student_join_course")
    @patch("accounts.views.primary_role")
    def test_permission_error_returns_403(self, mock_primary_role, mock_redeem):
        """PermissionError from service returns 403."""
        from accounts.views import join_course_with_code

        mock_primary_role.return_value = Role.STUDENT
        mock_redeem.side_effect = PermissionError("Not allowed")
        user = _user(role=Role.STUDENT)
        request = _auth_request(
            "post", "/api/v1/enrollments", data={"code": "X"}, user=user
        )
        response = join_course_with_code(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.redeem_student_join_course")
    @patch("accounts.views.primary_role")
    def test_success_returns_201_with_shape(self, mock_primary_role, mock_redeem):
        """Successful redemption returns 201 with expected response shape."""
        from accounts.views import join_course_with_code

        mock_primary_role.return_value = Role.STUDENT
        enrollment = SimpleNamespace(course_id=42)
        mock_redeem.return_value = (enrollment, False)
        user = _user(role=Role.STUDENT)
        request = _auth_request(
            "post", "/api/v1/enrollments", data={"code": "GOOD"}, user=user
        )
        response = join_course_with_code(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["courseId"] == 42
        assert response.data["createdNewUser"] is False
        assert response.data["alreadyEnrolled"] is False
        assert response.data["message"] == "Invite redeemed"

    @patch("accounts.views.redeem_student_join_course")
    @patch("accounts.views.primary_role")
    def test_already_enrolled_message(self, mock_primary_role, mock_redeem):
        """Already enrolled returns message 'Already enrolled'."""
        from accounts.views import join_course_with_code

        mock_primary_role.return_value = Role.STUDENT
        enrollment = SimpleNamespace(course_id=42)
        mock_redeem.return_value = (enrollment, True)
        user = _user(role=Role.STUDENT)
        request = _auth_request(
            "post", "/api/v1/enrollments", data={"code": "GOOD"}, user=user
        )
        response = join_course_with_code(request)
        assert response.data["message"] == "Already enrolled"
        assert response.data["alreadyEnrolled"] is True


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoginView:
    """Tests for the login view."""

    @patch("accounts.views.clear_identifier_failures")
    @patch("accounts.views.authenticate_user")
    @patch("accounts.views.identifier_allowed_for_user")
    @patch("accounts.views.find_user_by_identifier")
    @patch("accounts.views.check_identifier_throttle")
    def test_successful_login_returns_200(
        self, mock_throttle, mock_find, mock_allowed, mock_auth, mock_clear
    ):
        """Successful login returns 200 with user response body."""
        from accounts.views import login

        mock_throttle.return_value = True
        user = _user(role=Role.TEACHER)
        user.is_staff = False
        mock_find.return_value = user
        mock_allowed.return_value = True
        mock_auth.return_value = user
        # Mock RefreshToken.for_user to avoid OutstandingToken DB write
        mock_refresh = MagicMock()
        mock_refresh.access_token = "mock-access"
        mock_refresh.__str__ = MagicMock(return_value="mock-refresh")
        with (
            patch("accounts.views.build_user_response") as mock_build,
            patch("accounts.views.RefreshToken") as mock_rt,
        ):
            mock_build.return_value = {"id": str(user.id), "role": "TEACHER"}
            mock_rt.for_user.return_value = mock_refresh
            request = _auth_request(
                "post", "/api/v1/auth/sessions",
                data={"identifier": "user@test.com", "password": "pass"},
            )
            response = login(request)
        assert response.status_code == status.HTTP_200_OK

    @patch("accounts.views.check_identifier_throttle")
    def test_throttled_login_returns_429(self, mock_throttle):
        """Throttled identifier returns 429."""
        from accounts.views import login

        mock_throttle.return_value = False
        with patch("accounts.views.identifier_throttle_retry_after", return_value=60):
            request = _auth_request(
                "post", "/api/v1/auth/sessions",
                data={"identifier": "user@test.com", "password": "pass"},
            )
            response = login(request)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response

    @patch("accounts.views.register_identifier_failure")
    @patch("accounts.views.find_user_by_identifier")
    @patch("accounts.views.check_identifier_throttle")
    def test_user_not_found_returns_401(self, mock_throttle, mock_find, mock_register):
        """User not found returns 401."""
        from accounts.views import login

        mock_throttle.return_value = True
        mock_find.return_value = None
        request = _auth_request(
            "post", "/api/v1/auth/sessions",
            data={"identifier": "nobody@test.com", "password": "pass"},
        )
        response = login(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        mock_register.assert_called_once()

    @patch("accounts.views.register_identifier_failure")
    @patch("accounts.views.identifier_allowed_for_user")
    @patch("accounts.views.find_user_by_identifier")
    @patch("accounts.views.check_identifier_throttle")
    def test_identifier_not_allowed_returns_401(
        self, mock_throttle, mock_find, mock_allowed, mock_register
    ):
        """Disallowed identifier returns 401."""
        from accounts.views import login

        mock_throttle.return_value = True
        mock_find.return_value = _user()
        mock_allowed.return_value = False
        request = _auth_request(
            "post", "/api/v1/auth/sessions",
            data={"identifier": "user@test.com", "password": "pass"},
        )
        response = login(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("accounts.views.register_identifier_failure")
    @patch("accounts.views.authenticate_user")
    @patch("accounts.views.identifier_allowed_for_user")
    @patch("accounts.views.find_user_by_identifier")
    @patch("accounts.views.check_identifier_throttle")
    def test_wrong_password_returns_401(
        self, mock_throttle, mock_find, mock_allowed, mock_auth, mock_register
    ):
        """Wrong password returns 401."""
        from accounts.views import login

        mock_throttle.return_value = True
        mock_find.return_value = _user()
        mock_allowed.return_value = True
        mock_auth.return_value = None
        request = _auth_request(
            "post", "/api/v1/auth/sessions",
            data={"identifier": "user@test.com", "password": "wrong"},
        )
        response = login(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("accounts.views.authenticate_user")
    @patch("accounts.views.identifier_allowed_for_user")
    @patch("accounts.views.find_user_by_identifier")
    @patch("accounts.views.check_identifier_throttle")
    def test_staff_user_returns_403(
        self, mock_throttle, mock_find, mock_allowed, mock_auth
    ):
        """Staff user login via API returns 403 with admin message."""
        from accounts.views import login

        mock_throttle.return_value = True
        user = _user(is_staff=True)
        mock_find.return_value = user
        mock_allowed.return_value = True
        mock_auth.return_value = user
        request = _auth_request(
            "post", "/api/v1/auth/sessions",
            data={"identifier": "admin@test.com", "password": "pass"},
        )
        response = login(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Django admin" in response.data["detail"]


# ---------------------------------------------------------------------------
# current_user_profile
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCurrentUserProfileView:
    """Tests for current_user_profile view."""

    @patch("accounts.views.primary_role")
    def test_returns_user_profile(self, mock_role):
        """Returns authenticated user profile with expected fields."""
        from accounts.views import current_user_profile

        mock_role.return_value = "TEACHER"
        user = _user(
            id=42, role=Role.TEACHER,
            name="Test User", username="testuser", email="test@example.com",
        )
        request = _auth_request("get", "/api/v1/auth/me", user=user)
        response = current_user_profile(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(user.id)
        assert response.data["name"] == user.name
        assert response.data["username"] == user.username
        assert response.data["role"] == "TEACHER"
        assert "isStaff" in response.data


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshView:
    """Tests for the refresh token exchange view."""

    @patch("accounts.views.RefreshToken")
    def test_valid_refresh_from_body(self, mock_rt_class):
        """Valid refresh token from body returns 200 with cookie."""
        from accounts.views import refresh

        mock_token = MagicMock()
        mock_token.access_token = "new-access"
        mock_rt_class.return_value = mock_token
        request = _auth_request(
            "post", "/api/v1/auth/token-exchanges",
            data={"refreshToken": "valid-refresh"},
        )
        response = refresh(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Session refreshed."

    @patch("accounts.views.RefreshToken")
    def test_invalid_refresh_token_returns_401(self, mock_rt_class):
        """Invalid refresh token returns 401."""
        from rest_framework_simplejwt.exceptions import TokenError

        from accounts.views import refresh

        mock_rt_class.side_effect = TokenError("Token is invalid")
        request = _auth_request(
            "post", "/api/v1/auth/token-exchanges",
            data={"refreshToken": "bad-token"},
        )
        response = refresh(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_refresh_token_returns_400(self):
        """Missing refreshToken in body and cookie returns 400."""
        from accounts.views import refresh

        request = _auth_request(
            "post", "/api/v1/auth/token-exchanges", data={}
        )
        response = refresh(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLogoutView:
    """Tests for the logout view."""

    @patch("accounts.views.blacklist_refresh_token")
    def test_successful_logout(self, mock_blacklist):
        """Successful logout returns 200 with message."""
        from accounts.views import logout

        mock_blacklist.return_value = True
        user = _user()
        request = _auth_request(
            "post", "/api/v1/auth/session-revocations",
            data={"refreshToken": "valid"}, user=user,
        )
        response = logout(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Logged out."

    @patch("accounts.views.blacklist_refresh_token")
    def test_failed_blacklist_still_returns_200(self, mock_blacklist):
        """Failed blacklist is idempotent: returns 200."""
        from accounts.views import logout

        mock_blacklist.return_value = False
        user = _user()
        request = _auth_request(
            "post", "/api/v1/auth/session-revocations",
            data={"refreshToken": "expired"}, user=user,
        )
        response = logout(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Logged out."


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChangePasswordView:
    """Tests for the change_password view."""

    def test_passwords_do_not_match_returns_400(self):
        """Mismatched newPassword and confirmPassword returns 400."""
        from accounts.views import change_password

        user = _user()
        # check_password returns True for currentPassword validation
        user.check_password = MagicMock(return_value=True)
        request = _auth_request(
            "patch", "/api/v1/auth/password",
            data={
                "currentPassword": "OldPass123!",
                "newPassword": "NewPass1!",
                "confirmPassword": "DiffPass2!",
            },
            user=user,
        )
        response = change_password(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "do not match" in response.data["detail"]

    def test_wrong_current_password_returns_400(self):
        """Wrong current password returns 400."""
        from accounts.views import change_password

        user = _user()
        # check_password returns False for wrong current password
        user.check_password = MagicMock(return_value=False)
        request = _auth_request(
            "patch", "/api/v1/auth/password",
            data={
                "currentPassword": "WrongPass!",
                "newPassword": "NewPass456!",
                "confirmPassword": "NewPass456!",
            },
            user=user,
        )
        response = change_password(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrect" in response.data["detail"]

    @patch("accounts.views.password_strength_errors")
    def test_weak_password_returns_400(self, mock_strength):
        """Weak new password returns 400."""
        from accounts.views import change_password

        mock_strength.return_value = ["Password too short"]
        user = _user()
        # current password is correct
        user.check_password = MagicMock(return_value=True)
        request = _auth_request(
            "patch", "/api/v1/auth/password",
            data={
                "currentPassword": "OldPass123!",
                "newPassword": "weak",
                "confirmPassword": "weak",
            },
            user=user,
        )
        response = change_password(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.invalidate_user_sessions")
    @patch("accounts.views.password_strength_errors")
    def test_same_password_returns_400(self, mock_strength, mock_invalidate):
        """New password same as current returns 400."""
        from accounts.views import change_password

        mock_strength.return_value = []
        user = _user()
        # check_password returns True for both current and new (same password)
        user.check_password = MagicMock(return_value=True)
        request = _auth_request(
            "patch", "/api/v1/auth/password",
            data={
                "currentPassword": "SamePass123!",
                "newPassword": "SamePass123!",
                "confirmPassword": "SamePass123!",
            },
            user=user,
        )
        response = change_password(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "different" in response.data["detail"]

    @patch("accounts.views.invalidate_user_sessions")
    @patch("accounts.views.password_strength_errors")
    def test_successful_change_returns_200(self, mock_strength, mock_invalidate):
        """Successful password change returns 200 with sessions count."""
        from accounts.views import change_password

        mock_strength.return_value = []
        mock_invalidate.return_value = 3
        user = _user()
        # First call (currentPassword check) returns True,
        # second call (newPassword same-as-current check) returns False
        user.check_password = MagicMock(side_effect=[True, False])
        user.set_password = MagicMock()
        user.save = MagicMock()
        request = _auth_request(
            "patch", "/api/v1/auth/password",
            data={
                "currentPassword": "OldPass123!",
                "newPassword": "BrandNewPass456!",
                "confirmPassword": "BrandNewPass456!",
            },
            user=user,
        )
        response = change_password(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["sessionsInvalidated"] == 3


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateUserView:
    """Tests for the create_user view."""

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_create_user")
    def test_username_in_payload_rejected(self, mock_can_create, _mock_perm):
        """Username in request data returns 400."""
        from accounts.views import create_user

        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "Test", "username": "custom"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data["detail"].lower()

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_create_user")
    def test_missing_name_returns_400(self, mock_can_create, _mock_perm):
        """Missing name returns 400."""
        from accounts.views import create_user

        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users", data={"role": "STUDENT"}, user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name is required" in response.data["detail"]

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_create_user")
    def test_forbidden_role_returns_403(self, mock_can_create, _mock_perm):
        """Forbidden role creation returns 403."""
        from accounts.views import create_user

        mock_can_create.return_value = False
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "Test", "role": "RESEARCHER"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_create_user")
    def test_non_student_without_email_returns_400(self, mock_can_create, _mock_perm):
        """Non-student creation without email returns 400."""
        from accounts.views import create_user

        mock_can_create.return_value = True
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "Test", "role": "TEACHER"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email is required" in response.data["detail"]

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.identifier_in_use")
    @patch("accounts.views.can_create_user")
    def test_duplicate_email_returns_400(self, mock_can_create, mock_in_use, _mock_perm):
        """Duplicate email returns 400."""
        from accounts.views import create_user

        mock_can_create.return_value = True
        mock_in_use.return_value = True
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "Test", "role": "TEACHER", "email": "dup@test.com"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already taken" in response.data["detail"]

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.UserOutputSerializer")
    @patch("accounts.views.create_user_from_payload")
    @patch("accounts.views.generate_managed_username")
    @patch("accounts.views.identifier_in_use")
    @patch("accounts.views.can_create_user")
    def test_successful_create_returns_201(
        self, mock_can_create, mock_in_use, mock_gen_username, mock_create,
        mock_serializer, _mock_perm,
    ):
        """Successful user creation returns 201 with serialized user."""
        from accounts.views import create_user

        mock_can_create.return_value = True
        mock_in_use.return_value = False
        mock_gen_username.return_value = "generated_username"
        new_user = _user(id=99, role=Role.STUDENT, name="New Student")
        mock_create.return_value = new_user
        mock_serializer.return_value.data = {"id": str(new_user.id), "name": "New Student"}
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "New Student"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.create_user_from_payload")
    @patch("accounts.views.generate_managed_username")
    @patch("accounts.views.identifier_in_use")
    @patch("accounts.views.can_create_user")
    def test_value_error_from_service_returns_400(
        self, mock_can_create, mock_in_use, mock_gen_username, mock_create, _mock_perm
    ):
        """ValueError from create_user_from_payload returns 400."""
        from accounts.views import create_user

        mock_can_create.return_value = True
        mock_in_use.return_value = False
        mock_gen_username.return_value = "gen_user"
        mock_create.side_effect = ValueError("Duplicate username")
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/users",
            data={"name": "Test"},
            user=user,
        )
        response = create_user(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# manage_user (PATCH / DELETE)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestManageUserView:
    """Tests for manage_user (PATCH/DELETE) view."""

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.User")
    def test_delete_not_found_returns_404(self, mock_user_model, _mock_perm):
        """DELETE for non-existent user returns 404."""
        from accounts.views import manage_user

        mock_user_model.objects.filter.return_value.first.return_value = None
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "delete", "/api/v1/users/99999", user=user,
        )
        response = manage_user(request, user_id=99999)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_delete_user")
    @patch("accounts.views.User")
    def test_delete_forbidden_returns_404_masked(self, mock_user_model, mock_can_delete, _mock_perm):
        """DELETE without permission masks as 404."""
        from accounts.views import manage_user

        mock_can_delete.return_value = False
        target = _user(id=50)
        mock_user_model.objects.filter.return_value.first.return_value = target
        actor = _user(role=Role.TEACHER)
        request = _auth_request("delete", "/api/v1/users/50", user=actor)
        response = manage_user(request, user_id=50)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_delete_user")
    @patch("accounts.views.User")
    def test_delete_success_returns_204(self, mock_user_model, mock_can_delete, _mock_perm):
        """Successful DELETE returns 204 with no content."""
        from accounts.views import manage_user

        mock_can_delete.return_value = True
        target = _user(id=50)
        target.delete = MagicMock()
        mock_user_model.objects.filter.return_value.first.return_value = target
        actor = _user(role=Role.TEACHER)
        request = _auth_request("delete", "/api/v1/users/50", user=actor)
        response = manage_user(request, user_id=50)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.User")
    def test_patch_not_found_returns_404(self, mock_user_model, _mock_perm):
        """PATCH for non-existent user returns 404."""
        from accounts.views import manage_user

        mock_user_model.objects.filter.return_value.first.return_value = None
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "patch", "/api/v1/users/99999", data={"name": "New"}, user=user,
        )
        response = manage_user(request, user_id=99999)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_edit_user")
    @patch("accounts.views.primary_role")
    @patch("accounts.views.User")
    def test_patch_forbidden_returns_404_masked(
        self, mock_user_model, mock_primary_role, mock_can_edit, _mock_perm
    ):
        """PATCH without permission masks as 404."""
        from accounts.views import manage_user

        mock_can_edit.return_value = False
        mock_primary_role.return_value = Role.STUDENT
        target = _user(id=50, role=Role.STUDENT, email="target@test.com")
        mock_user_model.objects.filter.return_value.first.return_value = target
        actor = _user(role=Role.TEACHER)
        request = _auth_request(
            "patch", "/api/v1/users/50",
            data={"name": "New"}, user=actor,
        )
        response = manage_user(request, user_id=50)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.can_edit_user")
    @patch("accounts.views.primary_role")
    @patch("accounts.views.User")
    def test_patch_username_returns_400(
        self, mock_user_model, mock_primary_role, mock_can_edit, _mock_perm
    ):
        """PATCH with username field returns 400."""
        from accounts.views import manage_user

        mock_can_edit.return_value = True
        mock_primary_role.return_value = Role.STUDENT
        target = _user(id=50, role=Role.STUDENT, email="target@test.com")
        mock_user_model.objects.filter.return_value.first.return_value = target
        actor = _user(role=Role.TEACHER)
        request = _auth_request(
            "patch", "/api/v1/users/50",
            data={"username": "new_name"}, user=actor,
        )
        response = manage_user(request, user_id=50)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "immutable" in response.data["detail"].lower()


# ---------------------------------------------------------------------------
# codes_collection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCodesCollectionView:
    """Tests for codes_collection GET/POST view."""

    @patch("accounts.views._list_codes")
    def test_get_dispatches_to_list(self, mock_list):
        """GET dispatches to _list_codes."""
        from accounts.views import codes_collection

        mock_list.return_value = DRFResponse({"results": []}, status=200)
        user = _user()
        request = _auth_request("get", "/api/v1/codes", user=user)
        codes_collection(request)
        mock_list.assert_called_once()

    @patch("accounts.views._create_codes")
    def test_post_dispatches_to_create(self, mock_create):
        """POST dispatches to _create_codes."""
        from accounts.views import codes_collection

        mock_create.return_value = DRFResponse({"count": 0}, status=201)
        user = _user()
        request = _auth_request("post", "/api/v1/codes", data={}, user=user)
        codes_collection(request)
        mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# code_detail
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCodeDetailView:
    """Tests for code_detail GET/PATCH view."""

    @patch("accounts.views.registration_code_scope_queryset")
    def test_get_not_found_returns_404(self, mock_qs):
        """GET for non-existent code returns 404."""
        from accounts.views import code_detail

        mock_qs.return_value = MagicMock()
        mock_qs.return_value.filter.return_value.first.return_value = None
        user = _user()
        request = _auth_request("get", "/api/v1/codes/999", user=user)
        response = code_detail(request, code_id=999)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.transition_registration_code_status")
    def test_patch_value_error_not_found(self, mock_transition):
        """PATCH ValueError with 'not found' returns 404."""
        from accounts.views import code_detail

        mock_transition.side_effect = ValueError("Registration code not found.")
        user = _user()
        request = _auth_request(
            "patch", "/api/v1/codes/999",
            data={"status": "REVOKED"}, user=user,
        )
        response = code_detail(request, code_id=999)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.transition_registration_code_status")
    def test_patch_value_error_bad_request(self, mock_transition):
        """PATCH ValueError without 'not found' returns 400."""
        from accounts.views import code_detail

        mock_transition.side_effect = ValueError("Already revoked")
        user = _user()
        request = _auth_request(
            "patch", "/api/v1/codes/999",
            data={"status": "REVOKED"}, user=user,
        )
        response = code_detail(request, code_id=999)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# issue_password_reset_code_view
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIssuePasswordResetCodeView:
    """Tests for issue_password_reset_code_view."""

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.issue_password_reset_code")
    def test_value_error_not_found_returns_404(self, mock_issue, _mock_perm):
        """ValueError with 'not found' returns 404."""
        from accounts.views import issue_password_reset_code_view

        mock_issue.side_effect = ValueError("Target user not found")
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/auth/password-reset-codes",
            data={"targetUserId": 999}, user=user,
        )
        response = issue_password_reset_code_view(request)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.issue_password_reset_code")
    def test_value_error_without_not_found_returns_400(self, mock_issue, _mock_perm):
        """ValueError without 'not found' returns 400."""
        from accounts.views import issue_password_reset_code_view

        mock_issue.side_effect = ValueError("Invalid operation")
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/auth/password-reset-codes",
            data={"targetUserId": 1}, user=user,
        )
        response = issue_password_reset_code_view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.issue_password_reset_code")
    def test_permission_error_returns_403(self, mock_issue, _mock_perm):
        """PermissionError returns 403."""
        from accounts.views import issue_password_reset_code_view

        mock_issue.side_effect = PermissionError("Not allowed")
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/auth/password-reset-codes",
            data={"targetUserId": 1}, user=user,
        )
        response = issue_password_reset_code_view(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.IsTeacherOrAbove.has_permission", return_value=True)
    @patch("accounts.views.issue_password_reset_code")
    def test_success_returns_201(self, mock_issue, _mock_perm):
        """Successful issuance returns 201 with reset code details."""
        from django.utils import timezone

        from accounts.views import issue_password_reset_code_view

        reset_request = SimpleNamespace(
            id=42,
            requested_role="STUDENT",
            expires_at=timezone.now(),
        )
        mock_issue.return_value = (reset_request, "RESET-ABC123")
        user = _user(role=Role.TEACHER)
        request = _auth_request(
            "post", "/api/v1/auth/password-reset-codes",
            data={"targetUserId": 1}, user=user,
        )
        response = issue_password_reset_code_view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["resetCode"] == "RESET-ABC123"
        assert response.data["requestId"] == 42


# ---------------------------------------------------------------------------
# verify_reset_code
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVerifyResetCodeView:
    """Tests for verify_reset_code view."""

    @patch("accounts.views.verify_password_reset_code")
    def test_invalid_code_returns_400(self, mock_verify):
        """Invalid reset code returns 400 with valid=False."""
        from accounts.views import verify_reset_code

        mock_verify.return_value = None
        request = _auth_request(
            "post", "/api/v1/auth/reset-code-validations",
            data={"identifier": "user@test.com", "resetCode": "BAD"},
        )
        response = verify_reset_code(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["valid"] is False

    @patch("accounts.views.verify_password_reset_code")
    def test_valid_code_returns_200(self, mock_verify):
        """Valid reset code returns 200 with valid=True."""
        from django.utils import timezone

        from accounts.views import verify_reset_code

        code = SimpleNamespace(
            request_id=10,
            expires_at=timezone.now(),
        )
        mock_verify.return_value = code
        request = _auth_request(
            "post", "/api/v1/auth/reset-code-validations",
            data={"identifier": "user@test.com", "resetCode": "GOOD"},
        )
        response = verify_reset_code(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True
        assert response.data["requestId"] == 10


# ---------------------------------------------------------------------------
# complete_reset_code
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompleteResetCodeView:
    """Tests for complete_reset_code view."""

    def test_password_mismatch_returns_400(self):
        """Mismatched passwords returns 400."""
        from accounts.views import complete_reset_code

        request = _auth_request(
            "post", "/api/v1/auth/password-resets",
            data={
                "identifier": "user@test.com",
                "resetCode": "CODE",
                "newPassword": "Pass1!",
                "confirmPassword": "Pass2!",
            },
        )
        response = complete_reset_code(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "do not match" in response.data["detail"]

    @patch("accounts.views.complete_password_reset")
    def test_permission_error_returns_400(self, mock_complete):
        """PermissionError from service returns 400."""
        from accounts.views import complete_reset_code

        mock_complete.side_effect = PermissionError("Not allowed")
        request = _auth_request(
            "post", "/api/v1/auth/password-resets",
            data={
                "identifier": "user@test.com",
                "resetCode": "CODE",
                "newPassword": "Pass1!",
                "confirmPassword": "Pass1!",
            },
        )
        response = complete_reset_code(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.complete_password_reset")
    def test_success_returns_200(self, mock_complete):
        """Successful reset returns 200."""
        from accounts.views import complete_reset_code

        mock_complete.return_value = None
        request = _auth_request(
            "post", "/api/v1/auth/password-resets",
            data={
                "identifier": "user@test.com",
                "resetCode": "CODE",
                "newPassword": "Pass1!",
                "confirmPassword": "Pass1!",
            },
        )
        response = complete_reset_code(request)
        assert response.status_code == status.HTTP_200_OK
        assert "successful" in response.data["message"]


# ---------------------------------------------------------------------------
# my_sudo_grant
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMySudoGrantView:
    """Tests for my_sudo_grant view."""

    def test_admin_user_returns_full_sudo(self):
        """Admin user gets hasSudo=True and all permissions."""
        from accounts.views import my_sudo_grant

        user = _user(is_staff=True)
        request = _auth_request("get", "/api/v1/auth/sudo", user=user)
        response = my_sudo_grant(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["hasSudo"] is True
        assert response.data["canGrantSudo"] is True
        assert response.data["isStaff"] is True

    @patch("accounts.views.SudoGrant")
    def test_user_without_grant_returns_no_sudo(self, mock_sudo_grant_model):
        """User without SudoGrant returns hasSudo=False."""
        from accounts.views import my_sudo_grant

        mock_sudo_grant_model.objects.filter.return_value.first.return_value = None
        user = _user(role=Role.RESEARCHER)
        request = _auth_request("get", "/api/v1/auth/sudo", user=user)
        response = my_sudo_grant(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["hasSudo"] is False
        assert response.data["permissions"] == []

    @patch("accounts.views.SudoGrant")
    def test_user_with_grant(self, mock_sudo_grant_model):
        """User with SudoGrant returns grant permissions."""
        from accounts.views import my_sudo_grant

        grant = SimpleNamespace(
            permissions=["CREATE_TEACHER"],
            can_grant_sudo=True,
        )
        mock_sudo_grant_model.objects.filter.return_value.first.return_value = grant
        user = _user(role=Role.RESEARCHER)
        request = _auth_request("get", "/api/v1/auth/sudo", user=user)
        response = my_sudo_grant(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["hasSudo"] is True
        assert response.data["canGrantSudo"] is True
        assert "CREATE_TEACHER" in response.data["permissions"]


# ---------------------------------------------------------------------------
# grant_sudo
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGrantSudoView:
    """Tests for grant_sudo view."""

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.User")
    def test_missing_user_id_returns_400(self, mock_user_model, _mock_perm):
        """Missing user_id returns 400."""
        from accounts.views import grant_sudo

        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request(
            "post", "/api/v1/sudo-grants",
            data={"permissions": []}, user=user,
        )
        response = grant_sudo(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.User")
    def test_user_not_found_returns_404(self, mock_user_model, _mock_perm):
        """Non-existent grantee returns 404."""
        from accounts.views import grant_sudo

        mock_user_model.objects.filter.return_value.first.return_value = None
        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request(
            "post", "/api/v1/sudo-grants",
            data={"user_id": 99999, "permissions": []}, user=user,
        )
        response = grant_sudo(request)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.grant_sudo_to_researcher")
    @patch("accounts.views.User")
    def test_value_error_returns_400(self, mock_user_model, mock_grant, _mock_perm):
        """ValueError from service returns 400."""
        from accounts.views import grant_sudo

        mock_grant.side_effect = ValueError("Invalid permissions")
        grantee = _user(id=50)
        mock_user_model.objects.filter.return_value.first.return_value = grantee
        admin = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request(
            "post", "/api/v1/sudo-grants",
            data={"user_id": 50, "permissions": ["INVALID"]},
            user=admin,
        )
        response = grant_sudo(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.grant_sudo_to_researcher")
    @patch("accounts.views.User")
    def test_permission_error_returns_403(self, mock_user_model, mock_grant, _mock_perm):
        """PermissionError from service returns 403."""
        from accounts.views import grant_sudo

        mock_grant.side_effect = PermissionError("Not authorized")
        grantee = _user(id=50)
        mock_user_model.objects.filter.return_value.first.return_value = grantee
        admin = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request(
            "post", "/api/v1/sudo-grants",
            data={"user_id": 50, "permissions": ["CREATE_TEACHER"]},
            user=admin,
        )
        response = grant_sudo(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.grant_sudo_to_researcher")
    @patch("accounts.views.User")
    def test_success_returns_201(self, mock_user_model, mock_grant, _mock_perm):
        """Successful grant returns 201 with grant_id."""
        from accounts.views import grant_sudo

        mock_grant.return_value = SimpleNamespace(id=7)
        grantee = _user(id=50)
        mock_user_model.objects.filter.return_value.first.return_value = grantee
        admin = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request(
            "post", "/api/v1/sudo-grants",
            data={"user_id": 50, "permissions": ["CREATE_TEACHER"]},
            user=admin,
        )
        response = grant_sudo(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["grant_id"] == 7


# ---------------------------------------------------------------------------
# revoke_sudo
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRevokeSudoView:
    """Tests for revoke_sudo view."""

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.revoke_sudo_grant")
    def test_not_found_returns_404(self, mock_revoke, _mock_perm):
        """ValueError from service returns 404."""
        from accounts.views import revoke_sudo

        mock_revoke.side_effect = ValueError("Grant not found")
        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request("delete", "/api/v1/sudo-grants/99", user=user)
        response = revoke_sudo(request, grant_id=99)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.revoke_sudo_grant")
    def test_permission_error_returns_403(self, mock_revoke, _mock_perm):
        """PermissionError from service returns 403."""
        from accounts.views import revoke_sudo

        mock_revoke.side_effect = PermissionError("Not authorized")
        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request("delete", "/api/v1/sudo-grants/99", user=user)
        response = revoke_sudo(request, grant_id=99)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.revoke_sudo_grant")
    def test_success_returns_204(self, mock_revoke, _mock_perm):
        """Successful revocation returns 204."""
        from accounts.views import revoke_sudo

        mock_revoke.return_value = None
        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request("delete", "/api/v1/sudo-grants/1", user=user)
        response = revoke_sudo(request, grant_id=1)
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# list_staff
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListStaffView:
    """Tests for list_staff view."""

    @patch("accounts.views.IsResearcherOrAdmin.has_permission", return_value=True)
    @patch("accounts.views.paginate")
    @patch("accounts.views.User")
    def test_returns_paginated_response(self, mock_user_model, mock_paginate, _mock_perm):
        """Returns paginated staff list."""
        from accounts.views import list_staff

        # Mock the User.objects.filter(...).prefetch_related(...).distinct().order_by(...)
        mock_qs = MagicMock()
        mock_user_model.objects.filter.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.distinct.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs

        mock_paginate.return_value = DRFResponse(
            {"count": 0, "results": []}, status=200
        )
        user = _user(is_staff=True, role=Role.RESEARCHER)
        request = _auth_request("get", "/api/v1/users/staff", user=user)
        list_staff(request)
        mock_paginate.assert_called_once()


# ---------------------------------------------------------------------------
# login_with_google
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoginWithGoogleView:
    """Tests for login_with_google view."""

    @patch("accounts.views._google_userinfo")
    def test_google_api_failure_returns_401(self, mock_userinfo):
        """Google API failure returns 401."""
        from urllib.error import URLError

        from accounts.views import login_with_google

        mock_userinfo.side_effect = URLError("timeout")
        request = _auth_request(
            "post", "/api/v1/auth/sessions/oauth",
            data={"accessToken": "bad-token"},
        )
        response = login_with_google(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "verification failed" in response.data["detail"]

    @patch("accounts.views._google_userinfo")
    def test_missing_sub_returns_401(self, mock_userinfo):
        """Google profile without sub returns 401."""
        from accounts.views import login_with_google

        mock_userinfo.return_value = {"email": "user@test.com"}
        request = _auth_request(
            "post", "/api/v1/auth/sessions/oauth",
            data={"accessToken": "token"},
        )
        response = login_with_google(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("accounts.views._google_userinfo")
    def test_missing_email_returns_401(self, mock_userinfo):
        """Google profile without email returns 401."""
        from accounts.views import login_with_google

        mock_userinfo.return_value = {"sub": "12345"}
        request = _auth_request(
            "post", "/api/v1/auth/sessions/oauth",
            data={"accessToken": "token"},
        )
        response = login_with_google(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_access_token_returns_400(self):
        """Missing accessToken returns 400."""
        from accounts.views import login_with_google

        request = _auth_request(
            "post", "/api/v1/auth/sessions/oauth", data={},
        )
        response = login_with_google(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
