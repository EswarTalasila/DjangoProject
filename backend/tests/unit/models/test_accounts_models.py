"""Pure unit tests for accounts.models (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# User model __str__
# ---------------------------------------------------------------------------

class TestUserStr:

    def test_user_str(self):
        """User.__str__ returns 'name <username>' format."""
        from accounts.models import User

        user = User.__new__(User)
        user.name = "John Doe"
        user.username = "johndoe"

        assert str(user) == "John Doe <johndoe>"


# ---------------------------------------------------------------------------
# UserManager.create_superuser
# ---------------------------------------------------------------------------

class TestCreateSuperuser:

    @patch("accounts.models.UserManager.create_user")
    def test_raises_when_is_staff_false(self, mock_create):
        """create_superuser raises ValueError when is_staff is False."""
        from accounts.models import UserManager

        manager = UserManager()

        with pytest.raises(ValueError, match="is_staff=True"):
            manager.create_superuser("admin", "Admin", "pass", is_staff=False)

    @patch("accounts.models.UserManager.create_user")
    def test_raises_when_is_superuser_false(self, mock_create):
        """create_superuser raises ValueError when is_superuser is False."""
        from accounts.models import UserManager

        manager = UserManager()

        with pytest.raises(ValueError, match="is_superuser=True"):
            manager.create_superuser("admin", "Admin", "pass", is_superuser=False)

    @patch("accounts.models.UserManager.create_user")
    def test_sets_defaults_and_calls_create_user(self, mock_create):
        """create_superuser sets is_staff, is_superuser, and is_active then delegates to create_user."""
        from accounts.models import UserManager

        manager = UserManager()
        mock_create.return_value = MagicMock()

        manager.create_superuser("admin", "Admin", "pass")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["is_staff"] is True
        assert call_kwargs["is_superuser"] is True
        assert call_kwargs["is_active"] is True
        assert call_kwargs["email"] == "admin"


# ---------------------------------------------------------------------------
# SudoGrant
# ---------------------------------------------------------------------------

class TestSudoGrant:

    def test_clean_rejects_non_list_permissions(self):
        """SudoGrant.clean raises ValidationError when permissions is not a list."""
        from accounts.models import SudoGrant

        grant = SudoGrant.__new__(SudoGrant)
        grant.permissions = "not a list"

        with pytest.raises(ValidationError, match="must be a list"):
            grant.clean()

    def test_clean_rejects_invalid_permissions(self):
        """SudoGrant.clean raises ValidationError for unrecognized permission names."""
        from accounts.models import SudoGrant

        grant = SudoGrant.__new__(SudoGrant)
        grant.permissions = ["INVALID_PERM"]

        with pytest.raises(ValidationError, match="Invalid permissions"):
            grant.clean()

    def test_clean_accepts_valid_permissions(self):
        """SudoGrant.clean passes for a list of valid permission names."""
        from accounts.models import SudoGrant

        grant = SudoGrant.__new__(SudoGrant)
        grant.permissions = ["CREATE_TEACHER", "EDIT_USER"]

        grant.clean()  # should not raise


# ---------------------------------------------------------------------------
# RegistrationCode
# ---------------------------------------------------------------------------

class TestRegistrationCode:

    def test_str_representation(self):
        """RegistrationCode.__str__ returns 'code_type:code_prefix' format."""
        from accounts.models import RegistrationCode

        code = RegistrationCode.__new__(RegistrationCode)
        code.code_type = "STUDENT"
        code.code_prefix = "ABC"

        assert str(code) == "STUDENT:ABC"

    def test_clean_rejects_max_uses_below_one(self):
        """RegistrationCode.clean raises ValidationError when max_uses is less than 1."""
        from accounts.models import RegistrationCode

        code = RegistrationCode.__new__(RegistrationCode)
        code.max_uses = 0
        code.times_used = 0

        with pytest.raises(ValidationError, match="max_uses must be >= 1"):
            code.clean()

    def test_clean_rejects_negative_times_used(self):
        """RegistrationCode.clean raises ValidationError when times_used is negative."""
        from accounts.models import RegistrationCode

        code = RegistrationCode.__new__(RegistrationCode)
        code.max_uses = 5
        code.times_used = -1

        with pytest.raises(ValidationError, match="times_used must be >= 0"):
            code.clean()

    def test_clean_rejects_times_used_exceeding_max(self):
        """RegistrationCode.clean raises ValidationError when times_used exceeds max_uses."""
        from accounts.models import RegistrationCode

        code = RegistrationCode.__new__(RegistrationCode)
        code.max_uses = 3
        code.times_used = 4

        with pytest.raises(ValidationError, match="times_used cannot exceed max_uses"):
            code.clean()

    def test_clean_accepts_valid_code(self):
        """RegistrationCode.clean passes when max_uses and times_used are valid."""
        from accounts.models import RegistrationCode

        code = RegistrationCode.__new__(RegistrationCode)
        code.max_uses = 5
        code.times_used = 3
        code.code_type = "TEACHER"
        code.course_id = None

        code.clean()  # should not raise


# ---------------------------------------------------------------------------
# OAuthAccount __str__
# ---------------------------------------------------------------------------

class TestOAuthAccountStr:

    def test_str_representation(self):
        """OAuthAccount.__str__ returns 'provider:subject' format."""
        from accounts.models import OAuthAccount

        account = OAuthAccount.__new__(OAuthAccount)
        account.provider = "GOOGLE"
        account.subject = "123456"

        assert str(account) == "GOOGLE:123456"
