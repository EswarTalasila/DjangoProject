"""Pure unit tests for core.permissions (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _role_set
# ---------------------------------------------------------------------------

class TestRoleSet:

    def test_returns_empty_set_for_none_user(self):
        """_role_set returns an empty set when user is None."""
        from core.permissions import _role_set

        assert _role_set(None) == set()

    def test_returns_empty_set_for_unauthenticated_user(self):
        """_role_set returns an empty set when user is not authenticated."""
        from core.permissions import _role_set

        user = SimpleNamespace(is_authenticated=False)
        assert _role_set(user) == set()

    def test_returns_roles_from_queryset(self):
        """_role_set queries and returns the user's role names as a set."""
        from core.permissions import _role_set

        user = MagicMock()
        user.is_authenticated = True
        user._cached_role_set = None
        user.roles.values_list.return_value = ["TEACHER", "RESEARCHER"]

        result = _role_set(user)

        assert result == {"TEACHER", "RESEARCHER"}

    def test_uses_cached_roles(self):
        """_role_set returns cached roles without querying the database."""
        from core.permissions import _role_set

        user = MagicMock()
        user.is_authenticated = True
        user._cached_role_set = {"STUDENT"}

        result = _role_set(user)

        assert result == {"STUDENT"}
        user.roles.values_list.assert_not_called()


# ---------------------------------------------------------------------------
# primary_role
# ---------------------------------------------------------------------------

class TestPrimaryRole:

    def test_admin_user_returns_admin(self):
        """primary_role returns ADMIN for staff users."""
        from core.permissions import primary_role

        user = MagicMock()
        user.is_staff = True

        assert primary_role(user) == "ADMIN"

    @patch("core.permissions._role_set", return_value={"RESEARCHER", "TEACHER"})
    def test_researcher_is_highest(self, mock_roles):
        """primary_role returns RESEARCHER when user has both RESEARCHER and TEACHER roles."""
        from core.permissions import primary_role

        user = MagicMock()
        user.is_staff = False

        assert primary_role(user) == "RESEARCHER"

    @patch("core.permissions._role_set", return_value={"TEACHER", "STUDENT"})
    def test_teacher_over_student(self, mock_roles):
        """primary_role returns TEACHER when user has both TEACHER and STUDENT roles."""
        from core.permissions import primary_role

        user = MagicMock()
        user.is_staff = False

        assert primary_role(user) == "TEACHER"

    @patch("core.permissions._role_set", return_value={"STUDENT"})
    def test_student_role(self, mock_roles):
        """primary_role returns STUDENT when user only has the STUDENT role."""
        from core.permissions import primary_role

        user = MagicMock()
        user.is_staff = False

        assert primary_role(user) == "STUDENT"

    @patch("core.permissions._role_set", return_value=set())
    def test_fallback_to_student(self, mock_roles):
        """primary_role falls back to STUDENT when user has no roles."""
        from core.permissions import primary_role

        user = MagicMock()
        user.is_staff = False

        assert primary_role(user) == "STUDENT"


# ---------------------------------------------------------------------------
# has_role
# ---------------------------------------------------------------------------

class TestHasRole:

    @patch("core.permissions._role_set", return_value={"TEACHER"})
    def test_has_role_true(self, mock_roles):
        """has_role returns True when user has the specified role."""
        from core.permissions import has_role

        assert has_role(MagicMock(), "TEACHER") is True

    @patch("core.permissions._role_set", return_value={"TEACHER"})
    def test_has_role_false(self, mock_roles):
        """has_role returns False when user lacks the specified role."""
        from core.permissions import has_role

        assert has_role(MagicMock(), "RESEARCHER") is False


# ---------------------------------------------------------------------------
# has_any_role
# ---------------------------------------------------------------------------

class TestHasAnyRole:

    @patch("core.permissions._role_set", return_value={"STUDENT"})
    def test_has_any_role_true(self, mock_roles):
        """has_any_role returns True when user has at least one of the listed roles."""
        from core.permissions import has_any_role

        assert has_any_role(MagicMock(), ["STUDENT", "TEACHER"]) is True

    @patch("core.permissions._role_set", return_value={"STUDENT"})
    def test_has_any_role_false(self, mock_roles):
        """has_any_role returns False when user has none of the listed roles."""
        from core.permissions import has_any_role

        assert has_any_role(MagicMock(), ["TEACHER", "RESEARCHER"]) is False


# ---------------------------------------------------------------------------
# has_sudo_permission
# ---------------------------------------------------------------------------

class TestHasSudoPermission:

    def test_returns_true_when_has_permission(self):
        """has_sudo_permission returns True when permission is in the user's sudo grant."""
        from core.permissions import has_sudo_permission

        user = MagicMock()
        user.sudo_grant.permissions = ["CREATE_TEACHER", "EDIT_USER"]

        assert has_sudo_permission(user, "CREATE_TEACHER") is True

    def test_returns_false_when_missing_permission(self):
        """has_sudo_permission returns False when permission is not in the sudo grant."""
        from core.permissions import has_sudo_permission

        user = MagicMock()
        user.sudo_grant.permissions = ["CREATE_TEACHER"]

        assert has_sudo_permission(user, "DELETE_USER") is False

    def test_returns_false_when_no_sudo_grant(self):
        """has_sudo_permission returns False when user has no sudo grant at all."""
        from core.permissions import has_sudo_permission

        user = MagicMock()
        type(user).sudo_grant = property(lambda self: (_ for _ in ()).throw(AttributeError))

        assert has_sudo_permission(user, "CREATE_TEACHER") is False


# ---------------------------------------------------------------------------
# Permission classes
# ---------------------------------------------------------------------------

class TestIsAdmin:

    def test_allows_staff(self):
        """IsAdmin grants permission to staff users."""
        from core.permissions import IsAdmin

        request = MagicMock()
        request.user.is_staff = True

        assert IsAdmin().has_permission(request, None) is True

    def test_denies_non_staff(self):
        """IsAdmin denies permission to non-staff users."""
        from core.permissions import IsAdmin

        request = MagicMock()
        request.user.is_staff = False

        assert IsAdmin().has_permission(request, None) is False


class TestIsResearcher:

    @patch("core.permissions.has_role", return_value=True)
    def test_allows_researcher(self, mock_has_role):
        """IsResearcher grants permission to users with the RESEARCHER role."""
        from core.permissions import IsResearcher

        request = MagicMock()
        assert IsResearcher().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=False)
    def test_denies_non_researcher(self, mock_has_role):
        """IsResearcher denies permission to users without the RESEARCHER role."""
        from core.permissions import IsResearcher

        request = MagicMock()
        assert IsResearcher().has_permission(request, None) is False


class TestIsResearcherOrAdmin:

    def test_allows_admin(self):
        """IsResearcherOrAdmin grants permission to admin users."""
        from core.permissions import IsResearcherOrAdmin

        request = MagicMock()
        request.user.is_staff = True

        assert IsResearcherOrAdmin().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=True)
    def test_allows_researcher(self, mock_has_role):
        """IsResearcherOrAdmin grants permission to researchers who are not admin."""
        from core.permissions import IsResearcherOrAdmin

        request = MagicMock()
        request.user.is_staff = False

        assert IsResearcherOrAdmin().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=False)
    def test_denies_non_researcher_non_admin(self, mock_has_role):
        """IsResearcherOrAdmin denies permission to non-researcher, non-admin users."""
        from core.permissions import IsResearcherOrAdmin

        request = MagicMock()
        request.user.is_staff = False

        assert IsResearcherOrAdmin().has_permission(request, None) is False


class TestIsTeacher:

    @patch("core.permissions.has_role", return_value=True)
    def test_allows_teacher(self, mock_has_role):
        """IsTeacher grants permission to users with the TEACHER role."""
        from core.permissions import IsTeacher

        request = MagicMock()
        assert IsTeacher().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=False)
    def test_denies_non_teacher(self, mock_has_role):
        """IsTeacher denies permission to users without the TEACHER role."""
        from core.permissions import IsTeacher

        request = MagicMock()
        assert IsTeacher().has_permission(request, None) is False


class TestIsTeacherOrAdmin:

    def test_allows_admin(self):
        """IsTeacherOrAdmin grants permission to admin users."""
        from core.permissions import IsTeacherOrAdmin

        request = MagicMock()
        request.user.is_staff = True

        assert IsTeacherOrAdmin().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=True)
    def test_allows_teacher(self, mock_has_role):
        """IsTeacherOrAdmin grants permission to teachers who are not admin."""
        from core.permissions import IsTeacherOrAdmin

        request = MagicMock()
        request.user.is_staff = False

        assert IsTeacherOrAdmin().has_permission(request, None) is True


class TestIsTeacherOrAbove:

    def test_allows_admin(self):
        """IsTeacherOrAbove grants permission to admin users."""
        from core.permissions import IsTeacherOrAbove

        request = MagicMock()
        request.user.is_staff = True

        assert IsTeacherOrAbove().has_permission(request, None) is True

    @patch("core.permissions.has_role")
    def test_allows_researcher(self, mock_has_role):
        """IsTeacherOrAbove grants permission to researchers."""
        from core.permissions import IsTeacherOrAbove

        mock_has_role.side_effect = lambda user, role: role == "RESEARCHER"
        request = MagicMock()
        request.user.is_staff = False

        assert IsTeacherOrAbove().has_permission(request, None) is True

    @patch("core.permissions.has_role")
    def test_allows_teacher(self, mock_has_role):
        """IsTeacherOrAbove grants permission to teachers."""
        from core.permissions import IsTeacherOrAbove

        mock_has_role.side_effect = lambda user, role: role == "TEACHER"
        request = MagicMock()
        request.user.is_staff = False

        assert IsTeacherOrAbove().has_permission(request, None) is True

    @patch("core.permissions.has_role", return_value=False)
    def test_denies_student(self, mock_has_role):
        """IsTeacherOrAbove denies permission to students."""
        from core.permissions import IsTeacherOrAbove

        request = MagicMock()
        request.user.is_staff = False

        assert IsTeacherOrAbove().has_permission(request, None) is False
