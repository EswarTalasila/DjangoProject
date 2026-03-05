"""Unit tests for sudo grant/revoke service helpers (_sudo.py).

These are TRUE unit tests that mock all ORM/database calls and test
the service logic in isolation. They cover _can_grant_permissions,
grant_sudo_to_researcher, and revoke_sudo_grant including uncovered
lines 141-142 (creator-revocation path).
"""

from __future__ import annotations

from unittest.mock import Mock, PropertyMock, patch

import pytest

from accounts.services._sudo import (
    _can_grant_permissions,
    grant_sudo_to_researcher,
    revoke_sudo_grant,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# _can_grant_permissions
# ---------------------------------------------------------------------------


class TestCanGrantPermissions:
    """Tests for _can_grant_permissions authorization checks."""

    def test_admin_can_grant_any_permissions(self):
        """Admin (is_staff=True) can grant any permissions."""
        granter = Mock()
        granter.is_staff = True

        allowed, message = _can_grant_permissions(granter, ["CREATE_TEACHER", "EDIT_USER"], True)

        assert allowed is True
        assert message == ""

    def test_admin_can_grant_with_can_grant_sudo(self):
        """Admin can set can_grant_sudo=True."""
        granter = Mock()
        granter.is_staff = True

        allowed, _message = _can_grant_permissions(granter, ["CREATE_STUDENT"], True)

        assert allowed is True

    def test_no_sudo_grant_returns_false(self):
        """Researcher without SudoGrant cannot grant permissions."""
        granter = Mock()
        granter.is_staff = False
        from accounts.models import SudoGrant

        type(granter).sudo_grant = PropertyMock(side_effect=SudoGrant.DoesNotExist)

        allowed, message = _can_grant_permissions(granter, ["CREATE_STUDENT"], False)

        assert allowed is False
        assert "does not have sudo" in message

    def test_granter_without_can_grant_sudo_flag(self):
        """Researcher with can_grant_sudo=False cannot grant permissions."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = False
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(granter, ["CREATE_STUDENT"], False)

        assert allowed is False
        assert "can_grant_sudo=False" in message

    def test_non_admin_cannot_set_can_grant_sudo_true(self):
        """Non-admin researcher cannot set can_grant_sudo=True."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["CREATE_STUDENT"]
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(granter, ["CREATE_STUDENT"], True)

        assert allowed is False
        assert "Only admins" in message

    def test_non_delegable_permissions_blocked(self):
        """Non-delegable permissions cannot be granted by non-admin."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["ISSUE_RESEARCHER_REG_CODE"]
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(
            granter, ["ISSUE_RESEARCHER_REG_CODE"], False
        )

        assert allowed is False
        assert "non-delegable" in message

    def test_subset_check_blocks_unheld_permissions(self):
        """Granter cannot grant permissions they do not hold."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["CREATE_STUDENT"]
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(granter, ["DELETE_USER"], False)

        assert allowed is False
        assert "don't hold" in message

    def test_granter_can_grant_held_permissions(self):
        """Granter can grant permissions they hold."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["CREATE_STUDENT", "CREATE_TEACHER"]
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(
            granter, ["CREATE_STUDENT", "CREATE_TEACHER"], False
        )

        assert allowed is True
        assert message == ""

    def test_mixed_held_and_unheld_permissions(self):
        """Grant attempt with some unheld permissions is denied."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["CREATE_STUDENT"]
        granter.sudo_grant = grant

        allowed, message = _can_grant_permissions(
            granter, ["CREATE_STUDENT", "DELETE_USER"], False
        )

        assert allowed is False
        assert "DELETE_USER" in message

    def test_empty_permissions_list_succeeds(self):
        """Granting empty permissions list succeeds."""
        granter = Mock()
        granter.is_staff = False
        grant = Mock()
        grant.can_grant_sudo = True
        grant.permissions = ["CREATE_STUDENT"]
        granter.sudo_grant = grant

        allowed, _message = _can_grant_permissions(granter, [], False)

        assert allowed is True


# ---------------------------------------------------------------------------
# grant_sudo_to_researcher
# ---------------------------------------------------------------------------


class TestGrantSudoToResearcher:
    """Tests for grant_sudo_to_researcher creation/update logic."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_grantee_must_be_researcher(self, mock_role, mock_can_grant):
        """ValueError raised when grantee is not a researcher."""
        mock_role.return_value = "TEACHER"

        with pytest.raises(ValueError, match="RESEARCHER role"):
            grant_sudo_to_researcher(Mock(), Mock(), ["CREATE_STUDENT"])

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_unauthorized_granter_raises_permission_error(self, mock_role, mock_can_grant):
        """PermissionError raised when granter is not authorized."""
        mock_role.return_value = "RESEARCHER"
        mock_can_grant.return_value = (False, "Not authorized")

        with pytest.raises(PermissionError, match="Not authorized"):
            grant_sudo_to_researcher(Mock(), Mock(), ["CREATE_STUDENT"])

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_creates_new_grant_when_none_exists(self, mock_role, mock_can_grant):
        """Creates a new SudoGrant when grantee has no existing grant."""
        mock_role.return_value = "RESEARCHER"
        mock_can_grant.return_value = (True, "")
        grantee = Mock()
        granter = Mock()
        from accounts.models import SudoGrant

        type(grantee).sudo_grant = PropertyMock(side_effect=SudoGrant.DoesNotExist)

        # Patch SudoGrant constructor but preserve the real DoesNotExist
        new_grant = Mock()
        with patch.object(SudoGrant, "__init__", return_value=None), \
             patch("accounts.services._sudo.SudoGrant") as mock_sg_cls:
            mock_sg_cls.DoesNotExist = SudoGrant.DoesNotExist
            mock_sg_cls.return_value = new_grant

            result = grant_sudo_to_researcher(granter, grantee, ["CREATE_STUDENT"], False)

        new_grant.full_clean.assert_called_once()
        new_grant.save.assert_called_once()
        assert result is new_grant

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_updates_existing_grant(self, mock_role, mock_can_grant):
        """Updates existing SudoGrant instead of creating a new one."""
        mock_role.return_value = "RESEARCHER"
        mock_can_grant.return_value = (True, "")
        grantee = Mock()
        granter = Mock()
        existing_grant = Mock()
        grantee.sudo_grant = existing_grant

        result = grant_sudo_to_researcher(granter, grantee, ["EDIT_USER"], False)

        assert existing_grant.permissions == ["EDIT_USER"]
        assert existing_grant.can_grant_sudo is False
        assert existing_grant.granted_by is granter
        existing_grant.full_clean.assert_called_once()
        existing_grant.save.assert_called_once()
        assert result is existing_grant

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_admin_can_grant_with_can_grant_sudo(self, mock_role, mock_can_grant):
        """Admin can set can_grant_sudo=True on the grant."""
        mock_role.return_value = "RESEARCHER"
        mock_can_grant.return_value = (True, "")
        grantee = Mock()
        granter = Mock()
        existing_grant = Mock()
        grantee.sudo_grant = existing_grant

        grant_sudo_to_researcher(granter, grantee, ["CREATE_STUDENT"], True)

        assert existing_grant.can_grant_sudo is True

    @patch("accounts.services._sudo._can_grant_permissions")
    @patch("accounts.services._sudo.primary_role")
    def test_full_clean_validates_permissions(self, mock_role, mock_can_grant):
        """full_clean is called before save to validate enum values."""
        from django.core.exceptions import ValidationError

        mock_role.return_value = "RESEARCHER"
        mock_can_grant.return_value = (True, "")
        grantee = Mock()
        existing_grant = Mock()
        existing_grant.full_clean.side_effect = ValidationError({"permissions": "invalid"})
        grantee.sudo_grant = existing_grant

        with pytest.raises(ValidationError):
            grant_sudo_to_researcher(Mock(), grantee, ["INVALID_PERM"], False)


# ---------------------------------------------------------------------------
# revoke_sudo_grant (lines 141-142: creator-revocation path)
# ---------------------------------------------------------------------------


class TestRevokeSudoGrant:
    """Tests for revoke_sudo_grant authorization and deletion."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_grant_not_found_raises_value_error(self, mock_objects):
        """Non-existent grant ID raises ValueError."""
        from accounts.models import SudoGrant

        mock_objects.get.side_effect = SudoGrant.DoesNotExist

        with pytest.raises(ValueError, match="not found"):
            revoke_sudo_grant(Mock(), 999)

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_admin_can_revoke_any_grant(self, mock_objects):
        """Admin (is_staff=True) can revoke any grant."""
        grant = Mock()
        mock_objects.get.return_value = grant
        revoker = Mock()
        revoker.is_staff = True

        revoke_sudo_grant(revoker, 1)

        grant.delete.assert_called_once()

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_creator_can_revoke_own_grant(self, mock_objects):
        """Researcher who created the grant can revoke it (lines 140-142)."""
        grant = Mock()
        grant.granted_by_id = 42
        mock_objects.get.return_value = grant
        revoker = Mock()
        revoker.is_staff = False
        revoker.id = 42

        revoke_sudo_grant(revoker, 1)

        grant.delete.assert_called_once()

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_non_creator_non_admin_raises_permission_error(self, mock_objects):
        """Non-creator, non-admin researcher cannot revoke a grant."""
        grant = Mock()
        grant.granted_by_id = 42
        mock_objects.get.return_value = grant
        revoker = Mock()
        revoker.is_staff = False
        revoker.id = 99

        with pytest.raises(PermissionError, match="only revoke grants you created"):
            revoke_sudo_grant(revoker, 1)

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_admin_revoke_does_not_check_creator(self, mock_objects):
        """Admin revoke path returns before checking creator match."""
        grant = Mock()
        grant.granted_by_id = 42
        mock_objects.get.return_value = grant
        revoker = Mock()
        revoker.is_staff = True
        revoker.id = 99

        # Admin can revoke even though they are not the creator
        revoke_sudo_grant(revoker, 1)

        grant.delete.assert_called_once()

    @patch("accounts.services._sudo.SudoGrant.objects")
    def test_creator_revoke_checks_id_match(self, mock_objects):
        """Creator revocation path matches on granted_by_id == revoker.id."""
        grant = Mock()
        grant.granted_by_id = 10
        mock_objects.get.return_value = grant
        revoker = Mock()
        revoker.is_staff = False
        revoker.id = 10

        revoke_sudo_grant(revoker, 5)

        grant.delete.assert_called_once()
