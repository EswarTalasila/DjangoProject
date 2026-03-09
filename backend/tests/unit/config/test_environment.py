"""FR-12 Environment Profiles — unit tests with FR traceability naming.

Covers ENV-UC-01 through ENV-UC-06 and ENV-CN-01 through ENV-CN-12.
"""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pydantic import ValidationError

from accounts.models import User
from config.env import EnvSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_otel_enabled_env(monkeypatch):
    """Prevent ambient OTEL_ENABLED env vars from changing unit-test defaults."""
    monkeypatch.delenv("OTEL_ENABLED", raising=False)

# Minimal valid production config — all validators pass.
# otel_trace_file="" explicitly overrides any container env var.
_VALID_PROD = dict(
    environment="production",
    django_secret_key="prod-unique-secret-key-at-least-50-chars-long-random",
    database_url="postgres://produser:s3cureP@ss@db.prod.example.com:5432/proddb",
    django_allowed_hosts="app.example.com",
    django_cors_allowed_origins="https://app.example.com",
    google_client_id="123456.apps.googleusercontent.com",
    google_client_secret="GOCSPX-real-secret",
    admin_email="admin@mycompany.com",
    admin_password="SecureAdminP@ss123",
    otel_trace_file="",
)


def _build(**overrides) -> EnvSettings:
    """Construct an EnvSettings instance without reading real env vars."""
    kwargs = {**_VALID_PROD, **overrides}
    return EnvSettings(**kwargs)


def _build_raises(**overrides) -> ValidationError:
    """Expect construction to raise ValidationError; return it."""
    with pytest.raises(ValidationError) as exc_info:
        _build(**overrides)
    return exc_info.value


# ===================================================================
# ENV-UC-01 — Configure Runtime Profile
# ===================================================================


@pytest.mark.unit
class TestENV_UC_01:
    """ENV-UC-01: Configure Runtime Profile."""

    def test_ENV_UC_01_default_profile_is_development(self):
        """Default ENVIRONMENT is 'development' when unset."""
        field = EnvSettings.model_fields["environment"]
        assert field.default == "development"

    @pytest.mark.parametrize("profile", ["development", "testing", "production"])
    def test_ENV_UC_01_accepts_valid_profiles(self, profile):
        """All three valid profiles are accepted."""
        if profile == "production":
            settings = _build(environment=profile)
        else:
            settings = EnvSettings(environment=profile)
        assert settings.environment == profile

    def test_ENV_UC_01_E1_rejects_invalid_profile(self):
        """Invalid ENVIRONMENT value rejected with clear error (ENV-UC-01-E1)."""
        with pytest.raises(ValidationError) as exc_info:
            EnvSettings(environment="staging")
        assert "environment" in str(exc_info.value).lower()


# ===================================================================
# ENV-CN-01 — Single Environment Signal
# ===================================================================


@pytest.mark.unit
class TestENV_CN_01:
    """ENV-CN-01: ENVIRONMENT is the single authoritative runtime profile."""

    def test_ENV_CN_01_environment_controls_profile_properties(self):
        """Profile convenience booleans derive from ENVIRONMENT only."""
        dev = EnvSettings(environment="development")
        assert dev.is_development is True
        assert dev.is_testing is False
        assert dev.is_production is False

        test = EnvSettings(environment="testing")
        assert test.is_development is False
        assert test.is_testing is True

        prod = _build(environment="production")
        assert prod.is_production is True
        assert prod.is_development is False


# ===================================================================
# ENV-UC-02 — Validate Production Configuration (Fail Fast)
# ===================================================================


@pytest.mark.unit
class TestENV_UC_02:
    """ENV-UC-02: Production fail-fast validation."""

    def test_ENV_UC_02_production_passes_with_valid_config(self):
        """Full valid production config passes all checks."""
        settings = _build()
        assert settings.is_production is True

    def test_ENV_UC_02_E1_weak_secret_key(self):
        """Weak/default secret key blocks production (ENV-UC-02-E1)."""
        err = _build_raises(
            django_secret_key="django-insecure-local-dev-only-change-in-production"
        )
        assert "DJANGO_SECRET_KEY" in str(err)

    def test_ENV_UC_02_E1_debug_enabled(self):
        """DEBUG override in production is blocked (ENV-UC-02-E1)."""
        err = _build_raises(django_debug=True)
        assert "DJANGO_DEBUG" in str(err)

    def test_ENV_UC_02_E1_unsafe_db_defaults(self):
        """Default/local DATABASE_URL blocked in production (ENV-UC-02-E1)."""
        err = _build_raises(
            database_url="postgres://datadash:change-me@localhost:5432/datadash"
        )
        assert "DATABASE_URL" in str(err)

    def test_ENV_UC_02_E1_missing_oauth(self):
        """Missing OAuth config blocks production (ENV-UC-02-E1)."""
        err = _build_raises(google_client_id="", google_client_secret="")
        assert "OAuth" in str(err) or "GOOGLE_CLIENT" in str(err)

    def test_ENV_UC_02_E2_aggregates_all_violations(self):
        """Multiple violations aggregated in one error report (ENV-UC-02-E2)."""
        err = _build_raises(
            django_secret_key="django-insecure-local-dev-only-change-in-production",
            django_debug=True,
            database_url="postgres://datadash:change-me@localhost:5432/datadash",
            google_client_id="",
            google_client_secret="",
            admin_email="admin@example.com",
            admin_password="change-me",
            django_allowed_hosts="localhost",
            django_cors_allowed_origins="http://localhost:3000",
        )
        error_text = str(err)
        # Aggregated report must mention multiple violations
        assert "violation(s)" in error_text
        # Should contain evidence of multiple distinct checks
        assert "DJANGO_SECRET_KEY" in error_text
        assert "DJANGO_DEBUG" in error_text
        assert "DATABASE_URL" in error_text

    def test_ENV_UC_02_dev_testing_skip_validation(self):
        """Development and testing profiles skip production checks."""
        dev = EnvSettings(
            environment="development",
            django_secret_key="django-insecure-local-dev-only-change-in-production",
        )
        assert dev.is_development is True  # No error raised

        test = EnvSettings(
            environment="testing",
            django_secret_key="django-insecure-local-dev-only-change-in-production",
        )
        assert test.is_testing is True  # No error raised


# ===================================================================
# ENV-CN-02 — Production Fail-Fast Validation (aggregation)
# ===================================================================


@pytest.mark.unit
class TestENV_CN_02:
    """ENV-CN-02: Aggregated violation detection in one pass."""

    def test_ENV_CN_02_all_violations_aggregated_in_one_pass(self):
        """All production violations collected before raising single error."""
        err = _build_raises(
            django_secret_key="",
            django_debug=True,
            google_client_id="",
            google_client_secret="",
        )
        error_text = str(err)
        # Must mention count
        assert "violation(s)" in error_text
        # At least 3 distinct violations (secret key, debug, OAuth)
        assert "DJANGO_SECRET_KEY" in error_text
        assert "DJANGO_DEBUG" in error_text
        assert "OAuth" in error_text or "GOOGLE_CLIENT" in error_text


# ===================================================================
# ENV-CN-10 — OAuth Configuration Required
# ===================================================================


@pytest.mark.unit
class TestENV_CN_10:
    """ENV-CN-10: OAuth values required in production."""

    def test_ENV_CN_10_missing_client_id_blocks_production(self):
        """Missing GOOGLE_CLIENT_ID fails production startup."""
        err = _build_raises(google_client_id="")
        assert "OAuth" in str(err) or "GOOGLE_CLIENT_ID" in str(err)

    def test_ENV_CN_10_missing_client_secret_blocks_production(self):
        """Missing GOOGLE_CLIENT_SECRET fails production startup."""
        err = _build_raises(google_client_secret="")
        assert "OAuth" in str(err) or "GOOGLE_CLIENT_SECRET" in str(err)


# ===================================================================
# ENV-UC-03 — Bootstrap Admin in All Profiles
# ===================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestENV_UC_03:
    """ENV-UC-03: Bootstrap admin creation with profile-aware validation."""

    def test_ENV_UC_03_ADMIN_creates_admin_with_django_flags(self, monkeypatch):
        """Admin created with is_staff=True, is_superuser=True."""
        monkeypatch.setattr(
            "accounts.management.commands.ensure_admin.env",
            SimpleNamespace(
                admin_email="uc03-admin@example.com",
                admin_password="StrongAdminPass!",
                admin_username="UC03 Admin",
                is_production=False,
            ),
        )
        out = StringIO()
        call_command("ensure_admin", stdout=out)
        user = User.objects.get(username="uc03-admin@example.com")
        assert user.is_staff is True
        assert user.is_superuser is True
        assert "Created admin user" in out.getvalue()

    def test_ENV_UC_03_E1_production_default_credentials_rejected(self, monkeypatch):
        """Production rejects default/placeholder email (ENV-UC-03-E1)."""
        monkeypatch.setattr(
            "accounts.management.commands.ensure_admin.env",
            SimpleNamespace(
                admin_email="admin@example.com",
                admin_password="StrongAdminP@ss123",
                admin_username="Prod Admin",
                is_production=True,
            ),
        )
        with pytest.raises(CommandError, match="Default ADMIN_EMAIL"):
            call_command("ensure_admin")

    def test_ENV_UC_03_E2_password_policy_failure(self, monkeypatch):
        """Production rejects weak/short password (ENV-UC-03-E2)."""
        monkeypatch.setattr(
            "accounts.management.commands.ensure_admin.env",
            SimpleNamespace(
                admin_email="prod-admin@company.com",
                admin_password="short",
                admin_username="Prod Admin",
                is_production=True,
            ),
        )
        with pytest.raises(CommandError, match="ADMIN_PASSWORD"):
            call_command("ensure_admin")


# ===================================================================
# ENV-CN-04 — Bootstrap Admin Password Policy
# ===================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestENV_CN_04:
    """ENV-CN-04: Production bootstrap password meets strict policy."""

    def test_ENV_CN_04_production_password_denylist(self, monkeypatch):
        """Denylist passwords (change-me, admin, admin123, password) rejected."""
        for weak_pw in ["change-me", "admin", "admin123", "password"]:
            monkeypatch.setattr(
                "accounts.management.commands.ensure_admin.env",
                SimpleNamespace(
                    admin_email="cn04-admin@company.com",
                    admin_password=weak_pw,
                    admin_username="CN04 Admin",
                    is_production=True,
                ),
            )
            with pytest.raises(CommandError, match="ADMIN_PASSWORD"):
                call_command("ensure_admin")

    def test_ENV_CN_04_production_password_minimum_length(self, monkeypatch):
        """Production password must be >= 12 chars."""
        monkeypatch.setattr(
            "accounts.management.commands.ensure_admin.env",
            SimpleNamespace(
                admin_email="cn04-admin@company.com",
                admin_password="OnlyEleven1",  # 11 chars
                admin_username="CN04 Admin",
                is_production=True,
            ),
        )
        with pytest.raises(CommandError, match="12 characters"):
            call_command("ensure_admin")


# ===================================================================
# ENV-CN-05 — Idempotent Bootstrap
# ===================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestENV_CN_05:
    """ENV-CN-05: ensure_admin is safe to run repeatedly."""

    def test_ENV_CN_05_idempotent_ensure_admin(self, monkeypatch):
        """Repeated runs do not create duplicate admin users."""
        ns = SimpleNamespace(
            admin_email="cn05-admin@company.com",
            admin_password="StrongP@ss123!",
            admin_username="Idempotent Admin",
            is_production=False,
        )
        monkeypatch.setattr("accounts.management.commands.ensure_admin.env", ns)

        call_command("ensure_admin")
        count_after_first = User.objects.filter(email="cn05-admin@company.com").count()

        call_command("ensure_admin")
        count_after_second = User.objects.filter(email="cn05-admin@company.com").count()

        assert count_after_first == 1
        assert count_after_second == 1


# ===================================================================
# ENV-UC-04 — Control Seed Data by Profile
# ===================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestENV_UC_04:
    """ENV-UC-04: Seed command gated by profile."""

    def test_ENV_UC_04_ADMIN_seed_runs_in_dev(self, monkeypatch):
        """Seed runs without error in development profile."""
        monkeypatch.setattr(
            "accounts.management.commands.seed_e2e.env",
            SimpleNamespace(is_production=False),
        )
        out = StringIO()
        call_command("seed_e2e", stdout=out)
        assert "E2E seed completed" in out.getvalue()

    def test_ENV_UC_04_E1_production_seed_blocked(self, monkeypatch):
        """Production profile blocks seed_e2e (ENV-UC-04-E1)."""
        monkeypatch.setattr(
            "accounts.management.commands.seed_e2e.env",
            SimpleNamespace(is_production=True),
        )
        with pytest.raises(CommandError, match="blocked in production"):
            call_command("seed_e2e")


# ===================================================================
# ENV-CN-06 — Production Secret Encryption
# ===================================================================


@pytest.mark.unit
class TestENV_CN_06:
    """ENV-CN-06: Weak/default secrets blocked in production."""

    def test_ENV_CN_06_weak_secret_blocked_in_production(self):
        """Default secret key values rejected in production."""
        for weak_key in [
            "",
            "change-me-to-a-secure-random-string",
            "django-insecure-local-dev-only-change-in-production",
            "local-dev-secret-change-in-prod",
        ]:
            err = _build_raises(django_secret_key=weak_key)
            assert "DJANGO_SECRET_KEY" in str(err)


# ===================================================================
# ENV-UC-05 — Gate API Docs and Debug Tooling by Profile
# ===================================================================


@pytest.mark.unit
class TestENV_UC_05:
    """ENV-UC-05: API docs/debug gated by profile."""

    def test_ENV_UC_05_api_docs_enabled_in_development(self):
        """api_docs_enabled is True for development."""
        settings = EnvSettings(environment="development")
        assert settings.api_docs_enabled is True

    def test_ENV_UC_05_api_docs_enabled_in_testing(self):
        """api_docs_enabled is True for testing."""
        settings = EnvSettings(environment="testing")
        assert settings.api_docs_enabled is True

    def test_ENV_UC_05_E1_api_docs_disabled_in_production(self):
        """api_docs_enabled is False for production (ENV-UC-05-E1)."""
        settings = _build(environment="production")
        assert settings.api_docs_enabled is False

    def test_ENV_UC_05_debug_toolbar_only_in_development(self):
        """debug_toolbar_enabled only True in development with debug on."""
        dev = EnvSettings(environment="development")
        assert dev.debug_toolbar_enabled is True  # dev defaults debug=True

        test = EnvSettings(environment="testing")
        assert test.debug_toolbar_enabled is False

        prod = _build(environment="production")
        assert prod.debug_toolbar_enabled is False


# ===================================================================
# ENV-CN-07 — Deployment Guard by Profile
# ===================================================================


@pytest.mark.unit
class TestENV_CN_07:
    """ENV-CN-07: Seed and docs gated by profile."""

    def test_ENV_CN_07_seed_testing_auto(self):
        """Testing profile: seed_on_startup is True."""
        settings = EnvSettings(environment="testing")
        assert settings.seed_on_startup is True

    def test_ENV_CN_07_seed_dev_manual_only(self):
        """Development profile: manual seed allowed, no auto seed."""
        settings = EnvSettings(environment="development")
        assert settings.seed_on_startup is False
        assert settings.manual_seed_allowed is True

    def test_ENV_CN_07_seed_production_blocked(self):
        """Production profile: seed blocked entirely."""
        settings = _build(environment="production")
        assert settings.seed_on_startup is False
        assert settings.manual_seed_allowed is False


# ===================================================================
# ENV-UC-06 — Manage Secrets and Tracing by Profile
# ===================================================================


@pytest.mark.unit
class TestENV_UC_06:
    """ENV-UC-06: Secret, OAuth, and tracing policy by profile."""

    def test_ENV_UC_06_ADMIN_tracing_defaults_by_profile(self):
        """Tracing defaults: dev=on, testing=on, production=off."""
        dev = EnvSettings(environment="development")
        assert dev.effective_otel_enabled is True

        test = EnvSettings(environment="testing")
        assert test.effective_otel_enabled is True

        prod = _build(environment="production")
        assert prod.effective_otel_enabled is False

    def test_ENV_UC_06_E1_missing_oauth_blocks_production(self):
        """Missing OAuth config blocks production (ENV-UC-06-E1)."""
        err = _build_raises(google_client_id="", google_client_secret="")
        assert "OAuth" in str(err) or "GOOGLE_CLIENT" in str(err)

    def test_ENV_UC_06_E2_otel_trace_file_in_production(self):
        """OTEL_TRACE_FILE rejected in production when OTEL enabled (ENV-UC-06-E2)."""
        err = _build_raises(
            otel_enabled=True,
            otel_exporter_otlp_endpoint="https://otel.example.com",
            otel_trace_file="/tmp/traces.jsonl",
        )
        assert "OTEL" in str(err) and "trace file" in str(err).lower()

    def test_ENV_UC_06_E2_otel_enabled_without_endpoint(self):
        """OTEL enabled without OTLP endpoint rejected in production."""
        err = _build_raises(
            otel_enabled=True,
            otel_exporter_otlp_endpoint="",
        )
        assert "OTLP endpoint" in str(err)


# ===================================================================
# ENV-CN-08 — Session/Transport Security by Environment
# ===================================================================


@pytest.mark.unit
class TestENV_CN_08:
    """ENV-CN-08: Production enforces secure cookie/transport settings."""

    def test_ENV_CN_08_production_session_security(self):
        """Production: session_cookie_secure and csrf_cookie_secure are True."""
        prod = _build(environment="production")
        assert prod.session_cookie_secure is True
        assert prod.csrf_cookie_secure is True
        assert prod.ssl_redirect_enabled is True

    def test_ENV_CN_08_development_relaxed(self):
        """Development: relaxed cookie/transport defaults."""
        dev = EnvSettings(environment="development")
        assert dev.session_cookie_secure is False
        assert dev.csrf_cookie_secure is False
        assert dev.ssl_redirect_enabled is False

    def test_ENV_CN_08_testing_secure_cookies(self):
        """Testing: secure cookies but no SSL redirect."""
        test = EnvSettings(environment="testing")
        assert test.session_cookie_secure is True
        assert test.csrf_cookie_secure is True
        assert test.ssl_redirect_enabled is False


# ===================================================================
# ENV-CN-09 — Credential Exposure Guard
# ===================================================================


@pytest.mark.unit
class TestENV_CN_09:
    """ENV-CN-09: Production rejects placeholder/default secrets."""

    def test_ENV_CN_09_default_admin_email_blocked(self):
        """Default admin email rejected in production validation."""
        err = _build_raises(admin_email="admin@example.com")
        assert "ADMIN_EMAIL" in str(err)

    def test_ENV_CN_09_default_admin_password_blocked(self):
        """Default admin password rejected in production validation."""
        err = _build_raises(admin_password="change-me")
        assert "ADMIN_PASSWORD" in str(err)

    def test_ENV_CN_09_short_admin_password_blocked(self):
        """Admin password < 12 chars rejected in production."""
        err = _build_raises(admin_password="Short1!")
        assert "ADMIN_PASSWORD" in str(err)


# ===================================================================
# ENV-CN-11 — Profile-Aware Tracing Policy
# ===================================================================


@pytest.mark.unit
class TestENV_CN_11:
    """ENV-CN-11: Tracing enablement policy per profile."""

    def test_ENV_CN_11_testing_tracing_default_on(self):
        """Testing profile enables tracing by default."""
        settings = EnvSettings(environment="testing")
        assert settings.effective_otel_enabled is True

    def test_ENV_CN_11_testing_tracing_can_be_disabled(self):
        """Testing profile can opt out of tracing."""
        settings = EnvSettings(environment="testing", otel_enabled=False)
        assert settings.effective_otel_enabled is False

    def test_ENV_CN_11_development_tracing_configurable(self):
        """Development: default on, configurable off."""
        default_on = EnvSettings(environment="development")
        assert default_on.effective_otel_enabled is True

        opt_out = EnvSettings(environment="development", otel_enabled=False)
        assert opt_out.effective_otel_enabled is False

    def test_ENV_CN_11_production_tracing_opt_in(self):
        """Production: default off, opt-in only."""
        default_off = _build(environment="production")
        assert default_off.effective_otel_enabled is False

        opt_in = _build(
            environment="production",
            otel_enabled=True,
            otel_exporter_otlp_endpoint="https://otel.example.com",
        )
        assert opt_in.effective_otel_enabled is True


# ===================================================================
# ENV-CN-03 — Development Workflow Preservation
# ===================================================================


@pytest.mark.unit
class TestENV_CN_03:
    """ENV-CN-03: Development profile uses fast local defaults."""

    def test_ENV_CN_03_dev_defaults_no_prod_overrides_needed(self):
        """Development starts cleanly with default values — no production hardening."""
        settings = EnvSettings(environment="development")
        assert settings.debug is True
        assert settings.is_development is True
        # No ValidationError raised — dev doesn't require strong secrets


# ENV-CN-12 compose checks are covered by test_infrastructure_contracts.py
# (TestINFRA_CN_02) which properly loads compose files via fixture.
