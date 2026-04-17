"""Unit tests for utility service helpers (_utils.py).

These are TRUE unit tests that mock all ORM/database calls and test
the service logic in isolation. They cover normalize functions, hash
functions, throttle helpers, password strength, username generation
(including line 263: candidate truncation), identifier_in_use, and
identifier_allowed_for_user.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from accounts.services._utils import (
    LOGIN_RATE_LIMIT_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    MANAGED_USERNAME_LENGTH,
    REGISTRATION_CODE_PREFIX_LENGTH,
    _compact_alnum,
    _generate_secret_token,
    _hash_secret_token,
    _managed_username_seed,
    _normalize_registration_name,
    _unique_username_from_base,
    check_identifier_throttle,
    clear_identifier_failures,
    generate_managed_username,
    generate_student_username,
    identifier_allowed_for_user,
    identifier_in_use,
    identifier_throttle_retry_after,
    normalize_registration_code_input,
    normalize_username_identifier,
    password_strength_errors,
    register_identifier_failure,
    registration_code_hash,
    registration_code_prefix,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# normalize_username_identifier
# ---------------------------------------------------------------------------


class TestNormalizeUsernameIdentifier:
    """Tests for normalize_username_identifier string normalization."""

    def test_lowercases_and_strips(self):
        """Input is lowercased and stripped of whitespace."""
        assert normalize_username_identifier("  TEACHER@EXAMPLE.COM  ") == "teacher@example.com"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_username_identifier("") == ""

    def test_whitespace_only(self):
        """Whitespace-only input returns empty string."""
        assert normalize_username_identifier("   ") == ""

    def test_non_string_input(self):
        """Non-string input is coerced to string."""
        assert normalize_username_identifier(None) == "none"

    def test_numeric_input(self):
        """Numeric input is coerced to string."""
        assert normalize_username_identifier(123) == "123"


# ---------------------------------------------------------------------------
# normalize_registration_code_input
# ---------------------------------------------------------------------------


class TestNormalizeRegistrationCodeInput:
    """Tests for normalize_registration_code_input code normalization."""

    def test_uppercases_and_strips(self):
        """Input is uppercased and stripped of whitespace."""
        assert normalize_registration_code_input("  reg-abc123 ") == "REG-ABC123"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_registration_code_input("") == ""

    def test_already_uppercase(self):
        """Already uppercase input remains unchanged."""
        assert normalize_registration_code_input("REG-XYZ") == "REG-XYZ"


# ---------------------------------------------------------------------------
# registration_code_hash
# ---------------------------------------------------------------------------


class TestRegistrationCodeHash:
    """Tests for registration_code_hash HMAC digest."""

    def test_empty_input_returns_empty(self):
        """Empty or whitespace code returns empty string."""
        assert registration_code_hash("") == ""
        assert registration_code_hash("   ") == ""

    @patch("accounts.services._utils.salted_hmac")
    def test_uses_default_secret_key(self, mock_hmac):
        """Default secret key is used when none provided."""
        mock_result = Mock()
        mock_result.hexdigest.return_value = "abc123"
        mock_hmac.return_value = mock_result

        result = registration_code_hash("CODE")

        assert result == "abc123"
        call_kwargs = mock_hmac.call_args
        assert call_kwargs.kwargs["algorithm"] == "sha256"

    @patch("accounts.services._utils.salted_hmac")
    def test_uses_custom_secret(self, mock_hmac):
        """Custom secret is used when provided."""
        mock_result = Mock()
        mock_result.hexdigest.return_value = "custom_hash"
        mock_hmac.return_value = mock_result

        result = registration_code_hash("CODE", secret="my-secret")

        assert result == "custom_hash"
        call_kwargs = mock_hmac.call_args
        assert call_kwargs.kwargs["secret"] == "my-secret"

    def test_deterministic_for_same_input(self):
        """Same input produces same hash."""
        h1 = registration_code_hash("REG-ABC")
        h2 = registration_code_hash("REG-ABC")
        assert h1 == h2

    def test_case_insensitive(self):
        """Code hashing is case-insensitive due to normalization."""
        h1 = registration_code_hash("reg-abc")
        h2 = registration_code_hash("REG-ABC")
        assert h1 == h2


# ---------------------------------------------------------------------------
# registration_code_prefix
# ---------------------------------------------------------------------------


class TestRegistrationCodePrefix:
    """Tests for registration_code_prefix preview generation."""

    def test_returns_first_n_chars(self):
        """Prefix is the first REGISTRATION_CODE_PREFIX_LENGTH characters."""
        result = registration_code_prefix("REG-ABCDEFGH1234")
        assert len(result) == REGISTRATION_CODE_PREFIX_LENGTH

    def test_short_input(self):
        """Short input returns the full input."""
        result = registration_code_prefix("AB")
        assert result == "AB"

    def test_normalized_to_uppercase(self):
        """Input is normalized to uppercase before slicing."""
        result = registration_code_prefix("reg-lower")
        assert result == "REG-LOWE"


# ---------------------------------------------------------------------------
# _hash_secret_token
# ---------------------------------------------------------------------------


class TestHashSecretToken:
    """Tests for _hash_secret_token SHA-256 hashing."""

    def test_returns_hex_digest(self):
        """Returns a 64-character hex digest."""
        result = _hash_secret_token("test-token")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        """Same input produces same hash."""
        assert _hash_secret_token("abc") == _hash_secret_token("abc")

    def test_different_input_different_hash(self):
        """Different inputs produce different hashes."""
        assert _hash_secret_token("abc") != _hash_secret_token("xyz")


# ---------------------------------------------------------------------------
# _generate_secret_token
# ---------------------------------------------------------------------------


class TestGenerateSecretToken:
    """Tests for _generate_secret_token prefixed token generation."""

    def test_has_prefix(self):
        """Token starts with the given prefix."""
        token = _generate_secret_token("REG")
        assert token.startswith("REG-")

    def test_custom_nbytes_length(self):
        """Custom nbytes changes the hex portion length."""
        token = _generate_secret_token("TEST", nbytes=4)
        assert token.startswith("TEST-")
        # 4 bytes = 8 hex chars
        hex_part = token.split("-", 1)[1]
        assert len(hex_part) == 8

    def test_uppercase_hex(self):
        """Hex portion is uppercase."""
        token = _generate_secret_token("REG")
        hex_part = token.split("-", 1)[1]
        assert hex_part == hex_part.upper()

    def test_unique_tokens(self):
        """Consecutive calls produce different tokens."""
        t1 = _generate_secret_token("REG")
        t2 = _generate_secret_token("REG")
        assert t1 != t2


# ---------------------------------------------------------------------------
# password_strength_errors
# ---------------------------------------------------------------------------


class TestPasswordStrengthErrors:
    """Tests for password_strength_errors policy validation."""

    def test_strong_password_returns_empty(self):
        """A strong password returns no errors."""
        assert password_strength_errors("StrongPass1!") == []

    def test_too_short(self):
        """Password shorter than 8 characters."""
        errors = password_strength_errors("Aa1!")
        assert any("8 characters" in e for e in errors)

    def test_missing_uppercase(self):
        """Password without uppercase letter."""
        errors = password_strength_errors("alllower123!")
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase(self):
        """Password without lowercase letter."""
        errors = password_strength_errors("ALLUPPER123!")
        assert any("lowercase" in e for e in errors)

    def test_missing_digit(self):
        """Password without any digit."""
        errors = password_strength_errors("NoDigitsHere!")
        assert any("number" in e for e in errors)

    def test_missing_special_char(self):
        """Password without special character."""
        errors = password_strength_errors("NoSpecial123")
        assert any("special" in e for e in errors)

    def test_all_violations(self):
        """Very weak password has all violations."""
        errors = password_strength_errors("abc")
        # "abc" has lowercase, so only 4 violations (short, no upper, no digit, no special)
        assert len(errors) == 4

    def test_all_five_violations(self):
        """Empty password triggers all five violation checks."""
        errors = password_strength_errors("")
        assert len(errors) == 5

    def test_exact_eight_chars_passes_length(self):
        """Exactly 8 characters passes the length check."""
        errors = password_strength_errors("Aa1!Bb2@")
        assert not any("8 characters" in e for e in errors)


# ---------------------------------------------------------------------------
# _compact_alnum
# ---------------------------------------------------------------------------


class TestCompactAlnum:
    """Tests for _compact_alnum character filtering."""

    def test_keeps_lowercase_alnum(self):
        """Keeps only lowercase alphanumeric characters."""
        assert _compact_alnum("Hello World! 123") == "helloworld123"

    def test_empty_string(self):
        """Empty string returns empty."""
        assert _compact_alnum("") == ""

    def test_all_special_chars(self):
        """All special characters returns empty."""
        assert _compact_alnum("!@#$%^&*()") == ""

    def test_mixed_case(self):
        """Mixed case is lowered."""
        assert _compact_alnum("AbCdEf") == "abcdef"


# ---------------------------------------------------------------------------
# _normalize_registration_name
# ---------------------------------------------------------------------------


class TestNormalizeRegistrationName:
    """Tests for _normalize_registration_name name resolution."""

    def test_first_and_last_build_full(self):
        """first + last builds full name when no full name provided."""
        first, last, full = _normalize_registration_name(first_name="Jane", last_name="Smith")
        assert first == "Jane"
        assert last == "Smith"
        assert full == "Jane Smith"

    def test_full_name_splits_to_first_and_last(self):
        """Full name splits into first and last when they are not provided."""
        first, last, full = _normalize_registration_name(name="John Doe")
        assert first == "John"
        assert last == "Doe"
        assert full == "John Doe"

    def test_single_word_full_name(self):
        """Single-word full name sets first but not last."""
        first, last, full = _normalize_registration_name(name="Plato")
        assert first == "Plato"
        assert last == ""
        assert full == "Plato"

    def test_all_none_returns_empty(self):
        """All None inputs return empty strings."""
        first, last, full = _normalize_registration_name()
        assert first == ""
        assert last == ""
        assert full == ""

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        first, last, _full = _normalize_registration_name(
            first_name="  Jane  ", last_name="  Smith  "
        )
        assert first == "Jane"
        assert last == "Smith"

    def test_multi_word_full_name_takes_first_and_last(self):
        """Multi-word full name extracts first and last elements."""
        first, last, full = _normalize_registration_name(name="Jean Luc Picard")
        assert first == "Jean"
        assert last == "Picard"
        assert full == "Jean Luc Picard"


# ---------------------------------------------------------------------------
# _managed_username_seed
# ---------------------------------------------------------------------------


class TestManagedUsernameSeed:
    """Tests for _managed_username_seed username base generation."""

    def test_first_initial_plus_last(self):
        """Standard case: first initial + last name."""
        assert _managed_username_seed("Jane", "Smith", "") == "jsmith"

    def test_no_last_name_uses_first(self):
        """When no last name, uses full first name."""
        assert _managed_username_seed("Plato", "", "") == "plato"

    def test_no_first_or_last_uses_name(self):
        """When no first or last, falls back to name."""
        assert _managed_username_seed("", "", "John Doe") == "jdoe"

    def test_single_word_name_fallback(self):
        """Single-word name fallback uses the whole word."""
        assert _managed_username_seed("", "", "Plato") == "plato"

    def test_all_empty_returns_user(self):
        """All empty inputs return 'user'."""
        assert _managed_username_seed("", "", "") == "user"

    def test_special_chars_stripped(self):
        """Special characters are stripped from names."""
        assert _managed_username_seed("J@ne", "Sm!th", "") == "jsmth"


# ---------------------------------------------------------------------------
# _unique_username_from_base
# ---------------------------------------------------------------------------


class TestUniqueUsernameFromBase:
    """Tests for _unique_username_from_base collision resolution."""

    @patch("accounts.services._utils.User.objects")
    def test_no_collision_returns_base(self, mock_objects):
        """Base username with no collision is returned as-is."""
        mock_objects.filter.return_value.exists.return_value = False

        result = _unique_username_from_base("testuser")

        assert result == "testuser"

    @patch("accounts.services._utils.User.objects")
    def test_collision_appends_numeric_suffix(self, mock_objects):
        """Colliding base gets numeric suffix appended."""
        mock_objects.filter.return_value.exists.side_effect = [True, False]

        result = _unique_username_from_base("testuser")

        assert result == "testuser1"

    @patch("accounts.services._utils.User.objects")
    def test_multiple_collisions(self, mock_objects):
        """Multiple collisions increment the suffix."""
        mock_objects.filter.return_value.exists.side_effect = [True, True, False]

        result = _unique_username_from_base("testuser")

        assert result == "testuser2"

    @patch("accounts.services._utils.User._meta")
    @patch("accounts.services._utils.User.objects")
    def test_empty_base_defaults_to_user(self, mock_objects, mock_meta):
        """Empty base string defaults to 'user'."""
        mock_field = Mock()
        mock_field.max_length = 150
        mock_meta.get_field.return_value = mock_field
        mock_objects.filter.return_value.exists.return_value = False

        result = _unique_username_from_base("")

        assert result == "user"


# ---------------------------------------------------------------------------
# generate_managed_username (line 263: candidate truncation)
# ---------------------------------------------------------------------------


class TestGenerateManagedUsername:
    """Tests for generate_managed_username fixed-width generation."""

    @patch("accounts.services._utils.identifier_in_use")
    def test_standard_generation(self, mock_in_use):
        """Standard first+last name generates correct format."""
        mock_in_use.return_value = False

        result = generate_managed_username(first_name="Jane", last_name="Smith")

        assert len(result) == MANAGED_USERNAME_LENGTH
        assert result == "jsmith00"

    @patch("accounts.services._utils.identifier_in_use")
    def test_collision_increments_index(self, mock_in_use):
        """Collision on index 0 increments to index 1."""
        mock_in_use.side_effect = [True, False]

        result = generate_managed_username(first_name="Jane", last_name="Smith")

        assert result == "jsmith01"

    @patch("accounts.services._utils.identifier_in_use")
    def test_empty_inputs_uses_user_seed(self, mock_in_use):
        """Empty inputs produce 'user' based seed."""
        mock_in_use.return_value = False

        result = generate_managed_username()

        assert result == "user0000"
        assert len(result) == MANAGED_USERNAME_LENGTH

    @patch("accounts.services._utils.identifier_in_use")
    def test_long_name_truncated(self, mock_in_use):
        """Long names are truncated to fit MANAGED_USERNAME_LENGTH."""
        mock_in_use.return_value = False

        result = generate_managed_username(
            first_name="Alexander", last_name="Hamiltonsworth"
        )

        assert len(result) == MANAGED_USERNAME_LENGTH

    @patch("accounts.services._utils.identifier_in_use")
    def test_name_only_parameter(self, mock_in_use):
        """Using name-only parameter works correctly."""
        mock_in_use.return_value = False

        result = generate_managed_username(name="John Doe")

        assert len(result) == MANAGED_USERNAME_LENGTH

    @patch("accounts.services._utils.identifier_in_use")
    def test_many_collisions_still_resolves(self, mock_in_use):
        """Even with many collisions, the generator keeps trying until unique."""
        # Simulate 10 collisions, then success
        mock_in_use.side_effect = [True] * 10 + [False]

        result = generate_managed_username(first_name="J", last_name="D")

        assert len(result) == MANAGED_USERNAME_LENGTH

    @patch("accounts.services._utils.identifier_in_use")
    def test_large_index_truncates_candidate(self, mock_in_use):
        """Large collision index may cause candidate to exceed length and be truncated (line 263)."""
        # Simulate enough collisions that the index suffix grows large
        # When index >= 10, index_text is "10" (2 chars), prefix_len = 8-2 = 6
        mock_in_use.side_effect = [True] * 100 + [False]

        result = generate_managed_username(first_name="Jane", last_name="Smith")

        assert len(result) <= MANAGED_USERNAME_LENGTH


# ---------------------------------------------------------------------------
# generate_student_username (backward compat alias)
# ---------------------------------------------------------------------------


class TestGenerateStudentUsername:
    """Tests for generate_student_username backward-compatible alias."""

    @patch("accounts.services._utils.identifier_in_use")
    def test_delegates_to_managed_username(self, mock_in_use):
        """Calls generate_managed_username with name parameter."""
        mock_in_use.return_value = False

        result = generate_student_username("Jane Smith")

        assert result == "jsmith00"


# ---------------------------------------------------------------------------
# identifier_allowed_for_user
# ---------------------------------------------------------------------------


class TestIdentifierAllowedForUser:
    """Tests for identifier_allowed_for_user login validation."""

    @patch("accounts.services._utils.primary_role")
    def test_empty_identifier_returns_false(self, mock_role):
        """Empty identifier is always rejected."""
        assert identifier_allowed_for_user("", Mock()) is False
        assert identifier_allowed_for_user("   ", Mock()) is False

    @patch("accounts.services._utils.primary_role")
    def test_student_can_use_username(self, mock_role):
        """Student can authenticate with their username."""
        mock_role.return_value = "STUDENT"
        user = Mock()
        user.username = "student1"

        assert identifier_allowed_for_user("student1", user) is True

    @patch("accounts.services._utils.primary_role")
    def test_student_cannot_use_email(self, mock_role):
        """Student cannot authenticate with email."""
        mock_role.return_value = "STUDENT"
        user = Mock()
        user.username = "student1"
        user.email = "student1@example.com"

        assert identifier_allowed_for_user("student1@example.com", user) is False

    @patch("accounts.services._utils.primary_role")
    def test_teacher_can_use_username(self, mock_role):
        """Teacher can authenticate with username."""
        mock_role.return_value = "TEACHER"
        user = Mock()
        user.username = "teacher1"
        user.email = "teacher1@example.com"

        assert identifier_allowed_for_user("teacher1", user) is True

    @patch("accounts.services._utils.primary_role")
    def test_teacher_can_use_email(self, mock_role):
        """Teacher can authenticate with email."""
        mock_role.return_value = "TEACHER"
        user = Mock()
        user.username = "teacher1"
        user.email = "teacher1@example.com"

        assert identifier_allowed_for_user("teacher1@example.com", user) is True

    @patch("accounts.services._utils.primary_role")
    def test_non_student_without_email_rejects_email_identifier(self, mock_role):
        """Non-student user without email rejects email-style identifier."""
        mock_role.return_value = "TEACHER"
        user = Mock()
        user.username = "teacher1"
        user.email = None

        assert identifier_allowed_for_user("someone@example.com", user) is False

    @patch("accounts.services._utils.primary_role")
    def test_case_insensitive_matching(self, mock_role):
        """Matching is case-insensitive."""
        mock_role.return_value = "RESEARCHER"
        user = Mock()
        user.username = "Researcher1"
        user.email = "Researcher1@Example.COM"

        assert identifier_allowed_for_user("researcher1", user) is True
        assert identifier_allowed_for_user("RESEARCHER1@EXAMPLE.COM", user) is True


# ---------------------------------------------------------------------------
# check_identifier_throttle / register_identifier_failure /
# clear_identifier_failures / identifier_throttle_retry_after
# ---------------------------------------------------------------------------


class TestThrottleHelpers:
    """Tests for rate-limiting utility functions."""

    @patch("accounts.services._utils.cache")
    def test_check_throttle_below_limit(self, mock_cache):
        """Below rate limit returns True (allowed)."""
        mock_cache.get.return_value = LOGIN_RATE_LIMIT_ATTEMPTS - 1

        assert check_identifier_throttle("login", "user@test.com") is True

    @patch("accounts.services._utils.cache")
    def test_check_throttle_at_limit(self, mock_cache):
        """At rate limit returns False (blocked)."""
        mock_cache.get.return_value = LOGIN_RATE_LIMIT_ATTEMPTS

        assert check_identifier_throttle("login", "user@test.com") is False

    @patch("accounts.services._utils.cache")
    def test_check_throttle_no_cache_entry(self, mock_cache):
        """No cache entry (None -> 0) returns True."""
        mock_cache.get.return_value = 0

        assert check_identifier_throttle("login", "user@test.com") is True

    @patch("accounts.services._utils.cache")
    def test_register_failure_increments(self, mock_cache):
        """register_identifier_failure increments the counter."""
        mock_cache.get.return_value = 2

        register_identifier_failure("login", "user@test.com")

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][1] == 3  # 2 + 1
        assert call_args[0][2] == LOGIN_RATE_LIMIT_WINDOW_SECONDS

    @patch("accounts.services._utils.cache")
    def test_clear_failures_deletes_key(self, mock_cache):
        """clear_identifier_failures deletes the cache key."""
        clear_identifier_failures("login", "user@test.com")

        mock_cache.delete.assert_called_once()

    @patch("accounts.services._utils.check_identifier_throttle")
    def test_retry_after_returns_zero_when_allowed(self, mock_check):
        """Returns 0 when identifier is still under limit."""
        mock_check.return_value = True

        assert identifier_throttle_retry_after("login", "user@test.com") == 0

    @patch("accounts.services._utils.check_identifier_throttle")
    def test_retry_after_returns_window_when_blocked(self, mock_check):
        """Returns configured window when blocked."""
        mock_check.return_value = False

        result = identifier_throttle_retry_after("login", "user@test.com")

        assert result == LOGIN_RATE_LIMIT_WINDOW_SECONDS


# ---------------------------------------------------------------------------
# identifier_in_use (line 263 in original, line 283 in adjusted context)
# ---------------------------------------------------------------------------


class TestIdentifierInUse:
    """Tests for identifier_in_use username/email collision check."""

    @patch("accounts.services._utils.User.objects")
    def test_empty_identifier_returns_false(self, mock_objects):
        """Empty identifier is never in use."""
        assert identifier_in_use("") is False
        assert identifier_in_use("   ") is False

    @patch("accounts.services._utils.User.objects")
    def test_identifier_found_returns_true(self, mock_objects):
        """Found identifier returns True."""
        mock_objects.filter.return_value.exists.return_value = True

        assert identifier_in_use("taken@example.com") is True

    @patch("accounts.services._utils.User.objects")
    def test_identifier_not_found_returns_false(self, mock_objects):
        """Not-found identifier returns False."""
        mock_objects.filter.return_value.exists.return_value = False

        assert identifier_in_use("available@example.com") is False

    @patch("accounts.services._utils.User.objects")
    def test_exclude_user_id_filters_out_user(self, mock_objects):
        """exclude_user_id adds exclusion to the queryset."""
        mock_qs = MagicMock()
        mock_objects.filter.return_value = mock_qs
        mock_qs.exclude.return_value.exists.return_value = False

        result = identifier_in_use("user@example.com", exclude_user_id=42)

        mock_qs.exclude.assert_called_once_with(id=42)
        assert result is False

    @patch("accounts.services._utils.User.objects")
    def test_exclude_user_id_none_does_not_exclude(self, mock_objects):
        """No exclusion when exclude_user_id is None."""
        mock_objects.filter.return_value.exists.return_value = True

        result = identifier_in_use("taken@example.com", exclude_user_id=None)

        assert result is True
        mock_objects.filter.return_value.exclude.assert_not_called()
