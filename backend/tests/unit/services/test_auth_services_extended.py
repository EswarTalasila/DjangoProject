"""Extended unit tests for authentication service helpers (_auth.py).

These are TRUE unit tests that mock all ORM/database calls and test
the service logic in isolation. They cover edge cases and uncovered
lines (110-115: link_or_create_oauth_account) as well as additional
branch paths in build_user_response, authenticate_user,
find_user_by_identifier, invalidate_user_sessions, and
blacklist_refresh_token.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from accounts.services._auth import (
    authenticate_user,
    blacklist_refresh_token,
    build_user_response,
    find_user_by_identifier,
    invalidate_user_sessions,
    link_or_create_oauth_account,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# build_user_response
# ---------------------------------------------------------------------------


class TestBuildUserResponse:
    """Tests for build_user_response payload construction."""

    @patch("accounts.services._auth.primary_role")
    def test_returns_all_expected_keys(self, mock_primary_role):
        """Verify the response dict contains exactly the required keys."""
        mock_primary_role.return_value = "TEACHER"
        user = Mock()
        user.email = "teacher@example.com"
        user.username = "teacher1"
        user.name = "Teacher One"
        user.id = 42

        result = build_user_response(user)

        assert result == {
            "email": "teacher@example.com",
            "username": "teacher1",
            "name": "Teacher One",
            "role": "TEACHER",
            "id": "42",
        }

    @patch("accounts.services._auth.primary_role")
    def test_email_none_when_user_has_no_email(self, mock_primary_role):
        """Users without an email get None in the email field."""
        mock_primary_role.return_value = "STUDENT"
        user = Mock()
        user.email = ""
        user.username = "student1"
        user.name = "Student One"
        user.id = 7

        result = build_user_response(user)

        assert result["email"] is None

    @patch("accounts.services._auth.primary_role")
    def test_email_none_when_explicitly_none(self, mock_primary_role):
        """Users with email explicitly set to None get None in the payload."""
        mock_primary_role.return_value = "STUDENT"
        user = Mock()
        user.email = None
        user.username = "student2"
        user.name = "Student Two"
        user.id = 8

        result = build_user_response(user)

        assert result["email"] is None

    @patch("accounts.services._auth.primary_role")
    def test_id_is_always_string(self, mock_primary_role):
        """The id field is always cast to string regardless of input type."""
        mock_primary_role.return_value = "RESEARCHER"
        user = Mock()
        user.email = "r@example.com"
        user.username = "researcher1"
        user.name = "Researcher"
        user.id = 999

        result = build_user_response(user)

        assert isinstance(result["id"], str)
        assert result["id"] == "999"

    @patch("accounts.services._auth.primary_role")
    def test_admin_role_for_staff_user(self, mock_primary_role):
        """Staff users resolve to ADMIN role via primary_role."""
        mock_primary_role.return_value = "ADMIN"
        user = Mock()
        user.email = "admin@example.com"
        user.username = "admin1"
        user.name = "Admin"
        user.id = 1

        result = build_user_response(user)

        assert result["role"] == "ADMIN"


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


class TestAuthenticateUser:
    """Tests for authenticate_user credential validation logic."""

    @patch("accounts.services._auth.normalize_username_identifier")
    def test_returns_none_for_empty_username_after_normalization(self, mock_normalize):
        """Empty string after normalization short-circuits to None."""
        mock_normalize.return_value = ""

        result = authenticate_user("   ", "password")

        assert result is None

    @patch("accounts.services._auth.find_user_by_identifier")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_returns_none_when_user_not_found(self, mock_normalize, mock_find):
        """Non-existent user identifier returns None."""
        mock_normalize.return_value = "unknown_user"
        mock_find.return_value = None

        result = authenticate_user("unknown_user", "password")

        assert result is None

    @patch("accounts.services._auth.authenticate")
    @patch("accounts.services._auth.find_user_by_identifier")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_delegates_to_django_authenticate_with_resolved_username(
        self, mock_normalize, mock_find, mock_authenticate
    ):
        """Found user's username is passed to Django's authenticate backend."""
        mock_normalize.return_value = "user@example.com"
        user = Mock()
        user.username = "actual_username"
        mock_find.return_value = user
        mock_authenticate.return_value = user

        result = authenticate_user("user@example.com", "correct_password")

        mock_authenticate.assert_called_once_with(
            username="actual_username", password="correct_password"
        )
        assert result is user

    @patch("accounts.services._auth.authenticate")
    @patch("accounts.services._auth.find_user_by_identifier")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_returns_none_when_password_wrong(self, mock_normalize, mock_find, mock_authenticate):
        """Wrong password causes Django authenticate to return None."""
        mock_normalize.return_value = "user1"
        user = Mock()
        user.username = "user1"
        mock_find.return_value = user
        mock_authenticate.return_value = None

        result = authenticate_user("user1", "wrong_password")

        assert result is None


# ---------------------------------------------------------------------------
# find_user_by_identifier
# ---------------------------------------------------------------------------


class TestFindUserByIdentifier:
    """Tests for find_user_by_identifier lookup logic."""

    @patch("accounts.services._auth.normalize_username_identifier")
    def test_returns_none_for_empty_identifier(self, mock_normalize):
        """Empty identifier after normalization returns None."""
        mock_normalize.return_value = ""

        result = find_user_by_identifier("")

        assert result is None

    @patch("accounts.services._auth.User.objects")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_finds_user_by_username_first(self, mock_normalize, mock_objects):
        """Username match takes precedence over email lookup."""
        mock_normalize.return_value = "jdoe"
        user = Mock()
        mock_objects.filter.return_value.first.return_value = user

        result = find_user_by_identifier("jdoe")

        mock_objects.filter.assert_called_once_with(username__iexact="jdoe")
        assert result is user

    @patch("accounts.services._auth.User.objects")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_falls_back_to_email_when_username_not_found(self, mock_normalize, mock_objects):
        """When username lookup returns None, falls back to email lookup."""
        mock_normalize.return_value = "user@example.com"
        email_user = Mock()
        mock_objects.filter.return_value.first.side_effect = [None, email_user]

        result = find_user_by_identifier("user@example.com")

        assert mock_objects.filter.call_count == 2
        assert result is email_user

    @patch("accounts.services._auth.User.objects")
    @patch("accounts.services._auth.normalize_username_identifier")
    def test_returns_none_when_neither_username_nor_email_matches(
        self, mock_normalize, mock_objects
    ):
        """Both username and email lookups returning None yields None."""
        mock_normalize.return_value = "nobody@example.com"
        mock_objects.filter.return_value.first.return_value = None

        result = find_user_by_identifier("nobody@example.com")

        assert result is None


# ---------------------------------------------------------------------------
# invalidate_user_sessions
# ---------------------------------------------------------------------------


class TestInvalidateUserSessions:
    """Tests for invalidate_user_sessions token blacklisting."""

    @patch("accounts.services._auth.BlacklistedToken.objects")
    @patch("accounts.services._auth.OutstandingToken.objects")
    def test_blacklists_all_outstanding_tokens(self, mock_outstanding, mock_blacklisted):
        """Every outstanding token is blacklisted and counted."""
        user = Mock()
        token1 = Mock()
        token2 = Mock()
        mock_outstanding.filter.return_value = [token1, token2]
        mock_blacklisted.get_or_create.side_effect = [
            (Mock(), True),
            (Mock(), True),
        ]

        result = invalidate_user_sessions(user)

        assert result == 2
        mock_outstanding.filter.assert_called_once_with(user=user)

    @patch("accounts.services._auth.BlacklistedToken.objects")
    @patch("accounts.services._auth.OutstandingToken.objects")
    def test_does_not_double_count_already_blacklisted(self, mock_outstanding, mock_blacklisted):
        """Already-blacklisted tokens are not counted again."""
        user = Mock()
        token1 = Mock()
        mock_outstanding.filter.return_value = [token1]
        mock_blacklisted.get_or_create.return_value = (Mock(), False)

        result = invalidate_user_sessions(user)

        assert result == 0

    @patch("accounts.services._auth.BlacklistedToken.objects")
    @patch("accounts.services._auth.OutstandingToken.objects")
    def test_returns_zero_for_no_outstanding_tokens(self, mock_outstanding, mock_blacklisted):
        """User with no outstanding tokens returns 0."""
        user = Mock()
        mock_outstanding.filter.return_value = []

        result = invalidate_user_sessions(user)

        assert result == 0

    @patch("accounts.services._auth.BlacklistedToken.objects")
    @patch("accounts.services._auth.OutstandingToken.objects")
    def test_mixed_new_and_existing_blacklisted(self, mock_outstanding, mock_blacklisted):
        """Only newly blacklisted tokens are counted in the result."""
        user = Mock()
        tokens = [Mock(), Mock(), Mock()]
        mock_outstanding.filter.return_value = tokens
        mock_blacklisted.get_or_create.side_effect = [
            (Mock(), True),
            (Mock(), False),
            (Mock(), True),
        ]

        result = invalidate_user_sessions(user)

        assert result == 2


# ---------------------------------------------------------------------------
# blacklist_refresh_token
# ---------------------------------------------------------------------------


class TestBlacklistRefreshToken:
    """Tests for blacklist_refresh_token logout flow."""

    @patch("accounts.services._auth.RefreshToken")
    def test_successful_blacklist_returns_true(self, mock_refresh_cls):
        """Valid token that blacklists successfully returns True."""
        mock_token = Mock()
        mock_refresh_cls.return_value = mock_token

        result = blacklist_refresh_token("valid-token-string")

        assert result is True
        mock_token.blacklist.assert_called_once()

    @patch("accounts.services._auth.RefreshToken")
    def test_token_error_returns_false(self, mock_refresh_cls):
        """TokenError during blacklisting returns False."""
        from rest_framework_simplejwt.exceptions import TokenError

        mock_refresh_cls.side_effect = TokenError("invalid")

        result = blacklist_refresh_token("bad-token")

        assert result is False

    @patch("accounts.services._auth.RefreshToken")
    def test_blacklist_call_raises_token_error_returns_false(self, mock_refresh_cls):
        """TokenError raised by blacklist() method also returns False."""
        from rest_framework_simplejwt.exceptions import TokenError

        mock_token = Mock()
        mock_token.blacklist.side_effect = TokenError("expired")
        mock_refresh_cls.return_value = mock_token

        result = blacklist_refresh_token("expired-token")

        assert result is False


# ---------------------------------------------------------------------------
# link_or_create_oauth_account (lines 110-115)
# ---------------------------------------------------------------------------


class TestLinkOrCreateOAuthAccount:
    """Tests for link_or_create_oauth_account covering uncovered lines 110-115."""

    @patch("accounts.services._auth.OAuthAccount.objects")
    def test_creates_new_oauth_account_link(self, mock_objects):
        """Creates a new OAuthAccount when no prior link exists."""
        user = Mock()
        account = Mock()
        mock_objects.update_or_create.return_value = (account, True)

        result = link_or_create_oauth_account(user, "google-sub-123", "user@gmail.com")

        mock_objects.update_or_create.assert_called_once_with(
            provider="GOOGLE",
            subject="google-sub-123",
            defaults={"user": user, "email": "user@gmail.com"},
        )
        assert result is account

    @patch("accounts.services._auth.OAuthAccount.objects")
    def test_updates_existing_oauth_account(self, mock_objects):
        """Updates an existing OAuthAccount when link already exists."""
        user = Mock()
        existing_account = Mock()
        mock_objects.update_or_create.return_value = (existing_account, False)

        result = link_or_create_oauth_account(user, "google-sub-456", "newemail@gmail.com")

        mock_objects.update_or_create.assert_called_once_with(
            provider="GOOGLE",
            subject="google-sub-456",
            defaults={"user": user, "email": "newemail@gmail.com"},
        )
        assert result is existing_account

    @patch("accounts.services._auth.OAuthAccount.objects")
    def test_always_uses_google_provider(self, mock_objects):
        """The provider is always set to OAuthProvider.GOOGLE."""
        user = Mock()
        mock_objects.update_or_create.return_value = (Mock(), True)

        link_or_create_oauth_account(user, "sub-789", "email@test.com")

        call_kwargs = mock_objects.update_or_create.call_args
        assert call_kwargs.kwargs["provider"] == "GOOGLE"

    @patch("accounts.services._auth.OAuthAccount.objects")
    def test_returns_account_regardless_of_created_flag(self, mock_objects):
        """The return value is always the account, whether created or updated."""
        user = Mock()
        account = Mock()
        mock_objects.update_or_create.return_value = (account, True)

        result1 = link_or_create_oauth_account(user, "sub-a", "a@test.com")

        mock_objects.update_or_create.return_value = (account, False)

        result2 = link_or_create_oauth_account(user, "sub-a", "a@test.com")

        assert result1 is account
        assert result2 is account
