"""Unit tests for config.env EnvSettings validation logic.

Tests focus on:
- Production-mode validation guards (validate_runtime_contract)
- Profile-driven property defaults (debug, cookies, etc.)
- Parsed list properties (allowed_hosts, cors_origins)

These tests do NOT touch the database and do NOT rely on the .env file.

Note: Fields with ``validation_alias`` (django_debug) cannot be
set via the constructor -- only via environment variables. Tests that need to
override those fields use ``monkeypatch.setenv`` to set the env var before
constructing the settings instance.
"""

from __future__ import annotations

import pytest

from config.env import EnvSettings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolate_runtime_security_env(monkeypatch):
    """Keep unit defaults independent from container runtime security env vars."""
    for key in (
        "DJANGO_SECURE_SSL_REDIRECT",
        "DJANGO_SESSION_COOKIE_SECURE",
        "DJANGO_CSRF_COOKIE_SECURE",
    ):
        monkeypatch.delenv(key, raising=False)



# ---------------------------------------------------------------------------
# Production Validator Helpers
# ---------------------------------------------------------------------------

# Baseline kwargs forming a *valid* production configuration.
# Individual tests override one field at a time to trigger specific errors.
VALID_PROD_BASE = dict(  # noqa: C408
    environment="production",
    django_secret_key="a-very-long-production-secret-key-that-is-safe-1234",
    django_allowed_hosts="app.example.com",
    django_cors_allowed_origins="https://app.example.com",
    django_csrf_trusted_origins="https://app.example.com",
    database_url="postgres://prod_user:strong_pw@db.example.com:5432/prod_db",
    google_client_id="real-client-id",
    google_client_secret="real-client-secret",
    admin_email="admin@real-domain.com",
    admin_password="super-secure-password-12",
)


def _make_prod(monkeypatch=None, **overrides):
    """Build an EnvSettings for production with targeted overrides.

    If ``monkeypatch`` is provided, aliased fields (DJANGO_DEBUG)
    are set as environment variables instead of passed to the constructor.
    """
    kwargs = {**VALID_PROD_BASE, **overrides}

    # Handle aliased fields through env vars
    if monkeypatch is not None:
        debug_val = kwargs.pop("django_debug", None)
        if debug_val is not None:
            monkeypatch.setenv("DJANGO_DEBUG", str(debug_val).lower())
        else:
            monkeypatch.delenv("DJANGO_DEBUG", raising=False)
    else:
        # Without monkeypatch, remove aliased fields -- they only work via env vars
        kwargs.pop("django_debug", None)

    return EnvSettings(**kwargs)


# ============================================================================
# Profile property tests (non-production)
# ============================================================================


class TestProfileProperties:
    """Tests for profile-driven computed properties."""

    def test_is_development_default(self):
        """Default environment is development."""
        s = EnvSettings(environment="development")
        assert s.is_development is True
        assert s.is_testing is False
        assert s.is_production is False

    def test_is_testing(self):
        """Testing environment flag is set correctly."""
        s = EnvSettings(environment="testing")
        assert s.is_testing is True

    def test_is_production(self):
        """Production environment flag is set correctly."""
        s = _make_prod()
        assert s.is_production is True

    def test_debug_defaults_true_in_development(self, monkeypatch):
        """Debug defaults to True in development when DJANGO_DEBUG is unset."""
        monkeypatch.delenv("DJANGO_DEBUG", raising=False)
        s = EnvSettings(environment="development")
        assert s.debug is True

    def test_debug_respects_override_in_development(self, monkeypatch):
        """Debug can be overridden to False in development."""
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        s = EnvSettings(environment="development")
        assert s.debug is False

    def test_debug_always_false_in_testing(self, monkeypatch):
        """Debug is always False in testing regardless of override."""
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        s = EnvSettings(environment="testing")
        assert s.debug is False

    def test_debug_always_false_in_production(self, monkeypatch):
        """Debug is always False in production (ignores the override)."""
        monkeypatch.delenv("DJANGO_DEBUG", raising=False)
        s = _make_prod()
        assert s.debug is False

    def test_api_docs_enabled_in_dev_and_test(self):
        """API docs are enabled in development and testing."""
        assert EnvSettings(environment="development").api_docs_enabled is True
        assert EnvSettings(environment="testing").api_docs_enabled is True

    def test_api_docs_disabled_in_production(self):
        """API docs are disabled in production."""
        s = _make_prod()
        assert s.api_docs_enabled is False

    def test_debug_toolbar_enabled_in_dev_with_default_debug(self, monkeypatch):
        """Debug toolbar is enabled when development env has default debug=True."""
        monkeypatch.delenv("DJANGO_DEBUG", raising=False)
        s = EnvSettings(environment="development")
        assert s.debug_toolbar_enabled is True

    def test_debug_toolbar_disabled_when_debug_off(self, monkeypatch):
        """Debug toolbar is disabled when debug is explicitly False."""
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        s = EnvSettings(environment="development")
        assert s.debug_toolbar_enabled is False

    def test_debug_toolbar_disabled_in_testing(self):
        """Debug toolbar is disabled in testing environment."""
        s = EnvSettings(environment="testing")
        assert s.debug_toolbar_enabled is False

    def test_ssl_redirect_only_in_production(self):
        """SSL redirect is enabled only in production."""
        s = _make_prod()
        assert s.ssl_redirect_enabled is True
        assert EnvSettings(environment="development").ssl_redirect_enabled is False

    def test_session_cookie_secure_in_testing_and_production(self):
        """Session cookie secure flag is set in testing and production."""
        assert EnvSettings(environment="testing").session_cookie_secure is True
        s = _make_prod()
        assert s.session_cookie_secure is True
        assert EnvSettings(environment="development").session_cookie_secure is False

    def test_csrf_cookie_secure_in_testing_and_production(self):
        """CSRF cookie secure flag is set in testing and production."""
        assert EnvSettings(environment="testing").csrf_cookie_secure is True
        s = _make_prod()
        assert s.csrf_cookie_secure is True
        assert EnvSettings(environment="development").csrf_cookie_secure is False


# ============================================================================
# Parsed list properties
# ============================================================================


class TestParsedListProperties:
    """Tests for allowed_hosts_list and cors_origins_list parsing."""

    def test_allowed_hosts_parsing(self):
        """Comma-separated hosts are split and trimmed."""
        s = EnvSettings(django_allowed_hosts="  example.com , app.example.com  ")
        assert s.allowed_hosts_list == ["example.com", "app.example.com"]

    def test_allowed_hosts_skips_empty(self):
        """Empty segments from trailing commas are filtered out."""
        s = EnvSettings(django_allowed_hosts="example.com,,")
        assert s.allowed_hosts_list == ["example.com"]

    def test_cors_origins_parsing(self):
        """Comma-separated origins are split and trimmed."""
        s = EnvSettings(django_cors_allowed_origins="http://a.com , http://b.com")
        assert s.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_cors_origins_skips_empty(self):
        """Empty segments from trailing commas are filtered out."""
        s = EnvSettings(django_cors_allowed_origins="http://a.com,,,")
        assert s.cors_origins_list == ["http://a.com"]


# ============================================================================
# Production validation: _validate_secret_key
# ============================================================================


class TestValidateSecretKey:
    """Tests for production secret key validation."""

    def test_default_key_rejected(self):
        """Default insecure key is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_SECRET_KEY"):
            _make_prod(django_secret_key="django-insecure-local-dev-only-change-in-production")

    def test_empty_key_rejected(self):
        """Empty secret key is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_SECRET_KEY"):
            _make_prod(django_secret_key="")

    def test_change_me_key_rejected(self):
        """'change-me-to-a-secure-random-string' is rejected."""
        with pytest.raises(ValueError, match="DJANGO_SECRET_KEY"):
            _make_prod(django_secret_key="change-me-to-a-secure-random-string")

    def test_strong_key_accepted(self):
        """A strong, unique key passes production validation."""
        s = _make_prod(django_secret_key="my-super-strong-unique-production-key-9876")
        assert s.django_secret_key == "my-super-strong-unique-production-key-9876"


# ============================================================================
# Production validation: _validate_debug_override
# ============================================================================


class TestValidateDebugOverride:
    """Tests for production debug override validation."""

    def test_debug_true_rejected(self, monkeypatch):
        """Explicit DJANGO_DEBUG=true is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_DEBUG"):
            _make_prod(monkeypatch=monkeypatch, django_debug=True)

    def test_debug_none_accepted(self, monkeypatch):
        """Unset debug (None) is accepted in production."""
        monkeypatch.delenv("DJANGO_DEBUG", raising=False)
        s = _make_prod()
        assert s.debug is False

    def test_debug_false_accepted(self, monkeypatch):
        """Explicit DJANGO_DEBUG=false is accepted in production."""
        s = _make_prod(monkeypatch=monkeypatch, django_debug=False)
        assert s.debug is False


# ============================================================================
# Production validation: _validate_admin_bootstrap
# ============================================================================


class TestValidateAdminBootstrap:
    """Tests for production admin credential validation."""

    def test_default_email_rejected(self):
        """Default admin email is rejected in production."""
        with pytest.raises(ValueError, match="ADMIN_EMAIL"):
            _make_prod(admin_email="admin@example.com")

    def test_admin_only_email_rejected(self):
        """Single-word 'admin' email is rejected in production."""
        with pytest.raises(ValueError, match="ADMIN_EMAIL"):
            _make_prod(admin_email="admin")

    def test_default_password_rejected(self):
        """Default 'change-me' password is rejected in production."""
        with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
            _make_prod(admin_password="change-me")

    def test_short_password_rejected(self):
        """Password shorter than 12 characters is rejected."""
        with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
            _make_prod(admin_password="short")

    def test_common_passwords_rejected(self):
        """Common weak passwords are rejected."""
        for pw in ("admin", "admin123", "password"):
            with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
                _make_prod(admin_password=pw)

    def test_strong_credentials_accepted(self):
        """Strong email and password pass validation."""
        s = _make_prod(admin_email="admin@real-domain.com", admin_password="super-secure-password-12")
        assert s.admin_email == "admin@real-domain.com"


# ============================================================================
# Production validation: _validate_allowed_hosts
# ============================================================================


class TestValidateAllowedHosts:
    """Tests for production allowed hosts validation."""

    def test_empty_hosts_rejected(self):
        """Empty hosts list is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_ALLOWED_HOSTS"):
            _make_prod(django_allowed_hosts="")

    def test_localhost_rejected(self):
        """localhost is rejected in production hosts."""
        with pytest.raises(ValueError, match="DJANGO_ALLOWED_HOSTS"):
            _make_prod(django_allowed_hosts="localhost")

    def test_127_0_0_1_rejected(self):
        """127.0.0.1 is rejected in production hosts."""
        with pytest.raises(ValueError, match="DJANGO_ALLOWED_HOSTS"):
            _make_prod(django_allowed_hosts="127.0.0.1")

    def test_mixed_with_localhost_rejected(self):
        """Valid host mixed with localhost is still rejected."""
        with pytest.raises(ValueError, match="DJANGO_ALLOWED_HOSTS"):
            _make_prod(django_allowed_hosts="app.example.com,localhost")

    def test_valid_hosts_accepted(self):
        """Valid production hosts pass validation."""
        s = _make_prod(django_allowed_hosts="app.example.com,api.example.com")
        assert s.allowed_hosts_list == ["app.example.com", "api.example.com"]


# ============================================================================
# Production validation: _validate_cors
# ============================================================================


class TestValidateCors:
    """Tests for production CORS origin validation."""

    def test_empty_cors_rejected(self):
        """Empty CORS origins are rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_CORS_ALLOWED_ORIGINS"):
            _make_prod(django_cors_allowed_origins="")

    def test_wildcard_rejected(self):
        """Wildcard origin is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_CORS_ALLOWED_ORIGINS"):
            _make_prod(django_cors_allowed_origins="*")

    def test_localhost_origin_rejected(self):
        """localhost origin is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_CORS_ALLOWED_ORIGINS"):
            _make_prod(django_cors_allowed_origins="http://localhost:3000")

    def test_127_origin_rejected(self):
        """127.0.0.1 origin is rejected in production."""
        with pytest.raises(ValueError, match="DJANGO_CORS_ALLOWED_ORIGINS"):
            _make_prod(django_cors_allowed_origins="http://127.0.0.1:3000")

    def test_valid_origins_accepted(self):
        """Valid production origins pass validation."""
        s = _make_prod(django_cors_allowed_origins="https://app.example.com")
        assert s.cors_origins_list == ["https://app.example.com"]


# ============================================================================
# Production validation: _validate_database_url
# ============================================================================


class TestValidateDatabaseUrl:
    """Tests for production database URL validation."""

    def test_default_url_rejected(self):
        """Default local database URL is rejected in production."""
        with pytest.raises(ValueError, match="DATABASE_URL"):
            _make_prod(database_url="postgres://eelab:change-me@localhost:5432/eelab")

    def test_change_me_in_url_rejected(self):
        """URL containing 'change-me' is rejected."""
        with pytest.raises(ValueError, match="DATABASE_URL"):
            _make_prod(database_url="postgres://user:change-me@db.example.com:5432/mydb")

    def test_localhost_in_url_rejected(self):
        """URL containing 'localhost' is rejected."""
        with pytest.raises(ValueError, match="DATABASE_URL"):
            _make_prod(database_url="postgres://user:pw@localhost:5432/mydb")

    def test_valid_url_accepted(self):
        """Valid production database URL passes validation."""
        s = _make_prod(database_url="postgres://prod_user:strong_pw@db.example.com:5432/prod_db")
        assert "prod_user" in s.database_url


# ============================================================================
# Production validation: _validate_oauth
# ============================================================================


class TestValidateOAuth:
    """Tests for production OAuth credential validation."""

    def test_empty_client_id_rejected(self):
        """Empty Google client ID is rejected in production."""
        with pytest.raises(ValueError, match="OAuth"):
            _make_prod(google_client_id="")

    def test_empty_client_secret_rejected(self):
        """Empty Google client secret is rejected in production."""
        with pytest.raises(ValueError, match="OAuth"):
            _make_prod(google_client_secret="")

    def test_valid_oauth_accepted(self):
        """Valid OAuth credentials pass validation."""
        s = _make_prod(google_client_id="real-id", google_client_secret="real-secret")
        assert s.google_client_id == "real-id"


# ============================================================================
# Non-production skips validation
# ============================================================================


class TestNonProductionSkipsValidation:
    """Verify that non-production environments skip all production checks."""

    def test_development_accepts_insecure_defaults(self, monkeypatch):
        """Development environment accepts insecure values without production validation."""
        monkeypatch.setenv("DJANGO_SECRET_KEY", "change-me-to-a-secure-random-string")
        monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
        monkeypatch.setenv("ADMIN_PASSWORD", "change-me")
        s = EnvSettings(environment="development")
        assert s.django_secret_key == "change-me-to-a-secure-random-string"
        assert s.admin_email == "admin@example.com"
        assert s.admin_password == "change-me"

#    TODO: Fix test
#    def test_testing_accepts_insecure_defaults(self, monkeypatch):
#        """Testing environment accepts all default/insecure values."""
#        monkeypatch.setenv("ADMIN_PASSWORD", "change-me")
#        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
#        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
#        s = EnvSettings(environment="testing")
#        assert s.admin_password == "change-me"
#        assert s.google_client_id == ""
#
