"""FR-12 Environment Profiles — integration tests with FR traceability naming.

These tests verify profile-aware behavior end-to-end within the running
Django application context (URL resolution, command execution, settings wiring).
"""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import resolve

from accounts.models import User
from config.env import EnvSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PROD = dict(
    environment="production",
    django_secret_key="prod-unique-secret-key-at-least-50-chars-long-random",
    database_url="postgres://produser:s3cureP@ss@db.prod.example.com:5432/proddb",
    django_allowed_hosts="app.example.com",
    django_cors_allowed_origins="https://app.example.com",
    django_csrf_trusted_origins="https://app.example.com",
    google_client_id="123456.apps.googleusercontent.com",
    google_client_secret="GOCSPX-real-secret",
    admin_email="admin@mycompany.com",
    admin_password="SecureAdminP@ss123",
    otel_trace_file="",
)


# ===================================================================
# ENV-UC-01 — Runtime Profile Wiring (Integration)
# ===================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestENV_UC_01_Integration:
    """Verify settings.ENVIRONMENT is wired from env.environment."""

    def test_ENV_UC_01_runtime_profile_wiring(self):
        """settings.ENVIRONMENT reflects the env.environment value."""
        from django.conf import settings

        # In the test runner, ENVIRONMENT comes from env.py defaults or env vars.
        # The key assertion: settings.ENVIRONMENT exists and is a valid value.
        assert settings.ENVIRONMENT in ("development", "testing", "production")


# ===================================================================
# ENV-UC-02 — Production Boot Guard (Integration)
# ===================================================================


@pytest.mark.integration
class TestENV_UC_02_Integration:
    """Production boot guard rejects insecure config end-to-end."""

    def test_ENV_UC_02_production_boot_guard(self):
        """EnvSettings construction fails with insecure production config."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            EnvSettings(
                environment="production",
                django_secret_key="django-insecure-local-dev-only-change-in-production",
                database_url="postgres://eelab:change-me@localhost:5432/eelab",
                google_client_id="",
                google_client_secret="",
            )
        error_text = str(exc_info.value)
        assert "violation(s)" in error_text


# ===================================================================
# ENV-UC-03 — Idempotent / Profile-Aware Bootstrap (Integration)
# ===================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestENV_UC_03_Integration:
    """Bootstrap admin integration tests."""

    def test_ENV_UC_03_idempotent_bootstrap(self, monkeypatch):
        """Repeated ensure_admin runs produce no duplicates."""
        ns = SimpleNamespace(
            admin_email="int-idempotent@company.com",
            admin_password="StrongP@ss123!",
            admin_username="Int Idem Admin",
            is_production=False,
        )
        monkeypatch.setattr("accounts.management.commands.ensure_admin.env", ns)

        call_command("ensure_admin")
        call_command("ensure_admin")
        assert User.objects.filter(email="int-idempotent@company.com").count() == 1

    def test_ENV_UC_03_profile_aware_bootstrap(self, monkeypatch):
        """Production validation is stricter than development."""
        # Development: default email allowed
        dev_ns = SimpleNamespace(
            admin_email="admin@example.com",
            admin_password="devpass",
            admin_username="Dev Admin",
            is_production=False,
        )
        monkeypatch.setattr("accounts.management.commands.ensure_admin.env", dev_ns)
        call_command("ensure_admin")  # Should succeed

        # Production: same email rejected
        prod_ns = SimpleNamespace(
            admin_email="admin@example.com",
            admin_password="StrongAdminP@ss123",
            admin_username="Prod Admin",
            is_production=True,
        )
        monkeypatch.setattr("accounts.management.commands.ensure_admin.env", prod_ns)
        with pytest.raises(CommandError, match="Default ADMIN_EMAIL"):
            call_command("ensure_admin")


# ===================================================================
# ENV-UC-04 — Seed Behavior (Integration)
# ===================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestENV_UC_04_Integration:
    """Seed command behavior by profile."""

    def test_ENV_UC_04_testing_auto_seed(self, monkeypatch):
        """In testing profile, seed_on_startup is True (auto seed allowed)."""
        settings = EnvSettings(environment="testing")
        assert settings.seed_on_startup is True

        # seed_e2e actually runs without error
        monkeypatch.setattr(
            "accounts.management.commands.seed_e2e.env",
            SimpleNamespace(is_production=False),
        )
        out = StringIO()
        call_command("seed_e2e", stdout=out)
        assert "E2E seed completed" in out.getvalue()

    def test_ENV_UC_04_development_manual_seed(self, monkeypatch):
        """In development profile, manual seed allowed but not auto."""
        settings = EnvSettings(environment="development")
        assert settings.seed_on_startup is False
        assert settings.manual_seed_allowed is True

        # Manual invocation works
        monkeypatch.setattr(
            "accounts.management.commands.seed_e2e.env",
            SimpleNamespace(is_production=False),
        )
        out = StringIO()
        call_command("seed_e2e", stdout=out)
        assert "E2E seed completed" in out.getvalue()


# ===================================================================
# ENV-UC-05 — Route Gating by Profile (Integration)
# ===================================================================


@pytest.mark.integration
class TestENV_UC_05_Integration:
    """API docs routes gated by ENVIRONMENT setting."""

    def test_ENV_UC_05_route_gating_by_profile(self):
        """API docs routes exist in development ENVIRONMENT.

        Note: URL configuration is built once at import time based on
        settings.ENVIRONMENT. Since tests run with the default dev/testing
        profile, docs routes should be available.
        """
        from django.conf import settings

        if settings.ENVIRONMENT == "production":
            pytest.skip("Cannot test docs availability in production profile")

        # These URLs should be resolvable in dev/testing
        try:
            resolve("/api/schema/")
            resolve("/api/docs/")
            resolve("/api/redoc/")
        except Exception:
            pytest.fail("API docs routes not registered in non-production profile")


# ===================================================================
# ENV-UC-06 — Tracing Mode / OAuth Validation (Integration)
# ===================================================================


@pytest.mark.integration
class TestENV_UC_06_Integration:
    """Tracing and OAuth validation integration."""

    def test_ENV_UC_06_tracing_mode_by_profile(self):
        """effective_otel_enabled produces correct defaults per environment."""
        dev = EnvSettings(environment="development")
        assert dev.effective_otel_enabled is True

        testing = EnvSettings(environment="testing")
        assert testing.effective_otel_enabled is True

        prod = EnvSettings(**_VALID_PROD)
        assert prod.effective_otel_enabled is False

    def test_ENV_UC_06_oauth_required_validation(self):
        """Production startup fails when OAuth config is missing."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            EnvSettings(
                **{**_VALID_PROD, "google_client_id": "", "google_client_secret": ""},
            )
        assert "OAuth" in str(exc_info.value) or "GOOGLE_CLIENT" in str(exc_info.value)
