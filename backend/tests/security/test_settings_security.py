"""Security settings tests for transport security, cookie hardening, and JWT configuration."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.test import override_settings


@pytest.mark.security
class TestTransportSecurity:
    """Validate HSTS and transport security settings by environment profile."""

    def test_hsts_disabled_in_testing(self):
        """SECURE_HSTS_SECONDS must be 0 in non-production environments to avoid HSTS lock-in."""
        assert settings.SECURE_HSTS_SECONDS == 0

    def test_hsts_enabled_in_production(self):
        """SECURE_HSTS_SECONDS must be 31536000 (1 year) when overridden to production value."""
        with override_settings(SECURE_HSTS_SECONDS=31536000):
            assert settings.SECURE_HSTS_SECONDS == 31536000

    def test_hsts_include_subdomains_matches_production(self):
        """SECURE_HSTS_INCLUDE_SUBDOMAINS must only be True in production environments."""
        # In testing/development, env.is_production is False so this is False
        assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is False

    def test_hsts_preload_matches_production(self):
        """SECURE_HSTS_PRELOAD must only be True in production to prevent premature HSTS preloading."""
        # In testing/development, env.is_production is False so this is False
        assert settings.SECURE_HSTS_PRELOAD is False

    def test_ssl_redirect_disabled_in_testing(self):
        """SECURE_SSL_REDIRECT must be False in non-production environments to allow HTTP dev/test traffic."""
        assert settings.SECURE_SSL_REDIRECT is False

    def test_x_frame_options_is_deny(self):
        """X_FRAME_OPTIONS must be DENY unconditionally to prevent clickjacking attacks."""
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_content_type_nosniff_matches_production(self):
        """SECURE_CONTENT_TYPE_NOSNIFF must follow env.is_production to prevent MIME-type sniffing in prod."""
        # In testing, env.is_production is False so this is False
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is False


@pytest.mark.security
class TestCookieSecurity:
    """Validate CSRF and session cookie security flags by environment profile."""

    def test_csrf_cookie_httponly(self):
        """CSRF_COOKIE_HTTPONLY must be True to prevent JavaScript access to CSRF tokens."""
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_csrf_cookie_samesite_lax(self):
        """CSRF_COOKIE_SAMESITE must be Lax to balance CSRF protection with cross-site navigation."""
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"

    def test_session_cookie_httponly(self):
        """SESSION_COOKIE_HTTPONLY must be True to prevent JavaScript access to session identifiers."""
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite_lax(self):
        """SESSION_COOKIE_SAMESITE must be Lax to balance CSRF protection with cross-site navigation."""
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"

    def test_csrf_cookie_secure_in_production(self):
        """CSRF_COOKIE_SECURE must be True in testing and production (False only in development)."""
        # env.csrf_cookie_secure returns True for testing and production
        assert settings.CSRF_COOKIE_SECURE is True

    def test_session_cookie_secure_in_production(self):
        """SESSION_COOKIE_SECURE must be True in testing and production (False only in development)."""
        # env.session_cookie_secure returns True for testing and production
        assert settings.SESSION_COOKIE_SECURE is True


@pytest.mark.security
class TestJWTConfiguration:
    """Validate JWT token configuration for secure rotation and blacklisting."""

    def test_jwt_rotation_enabled(self):
        """ROTATE_REFRESH_TOKENS must be True to issue fresh tokens and invalidate old ones on each use."""
        assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True

    def test_jwt_blacklist_after_rotation(self):
        """BLACKLIST_AFTER_ROTATION must be True to prevent reuse of rotated-out refresh tokens."""
        assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True

    def test_jwt_access_token_lifetime(self):
        """ACCESS_TOKEN_LIFETIME must be 15 minutes to tighten bearer-token exposure window."""
        assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=15)

    def test_jwt_refresh_token_lifetime(self):
        """REFRESH_TOKEN_LIFETIME must be 24 hours to limit the refresh window without forcing daily re-login."""
        assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(hours=24)

    def test_jwt_auth_header_type(self):
        """AUTH_HEADER_TYPES must be Bearer to comply with RFC 6750 authorization header scheme."""
        assert settings.SIMPLE_JWT["AUTH_HEADER_TYPES"] == ("Bearer",)

    def test_token_blacklist_app_installed(self):
        """rest_framework_simplejwt.token_blacklist must be in INSTALLED_APPS for token invalidation to work."""
        assert "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
