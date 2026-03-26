"""Environment configuration and profile-driven runtime policy."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """Application environment settings with profile-aware behavior."""

    model_config = SettingsConfigDict(
        # Load from .env file if present (doesn't override actual env vars)
        env_file=".env",
        env_file_encoding="utf-8",
        # Case-insensitive environment variable names
        case_sensitive=False,
        # Don't fail if .env file doesn't exist
        env_ignore_empty=True,
        # Extra fields are ignored (allows unrelated env vars)
        extra="ignore",
        # Allow both field names and validation aliases in constructors
        populate_by_name=True,
    )

    # Runtime profile signal
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Runtime profile: development | testing | production",
    )

    # Django core settings
    django_secret_key: str = Field(
        default="django-insecure-local-dev-only-change-in-production",
        description="Django secret key for sessions and CSRF protection",
    )
    django_debug: bool | None = Field(
        default=None,
        validation_alias="DJANGO_DEBUG",
        description="Optional debug override (development only)",
    )
    django_secure_ssl_redirect: bool | None = Field(
        default=None,
        validation_alias="DJANGO_SECURE_SSL_REDIRECT",
        description="Optional SSL redirect override (defaults true in production).",
    )
    django_session_cookie_secure: bool | None = Field(
        default=None,
        validation_alias="DJANGO_SESSION_COOKIE_SECURE",
        description="Optional session cookie secure override (defaults true in production).",
    )
    django_csrf_cookie_secure: bool | None = Field(
        default=None,
        validation_alias="DJANGO_CSRF_COOKIE_SECURE",
        description="Optional CSRF cookie secure override (defaults true in production).",
    )
    django_allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts",
    )
    django_csrf_trusted_origins: str = Field(
        default="",
        description="Comma-separated CSRF trusted origins (e.g. https://example.com)",
    )

    # Database
    database_url: str = Field(
        default="postgres://eelab:change-me@localhost:5432/eelab",
        description="PostgreSQL connection URL",
    )

    # CORS
    django_cors_allowed_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Google OAuth (optional)
    google_client_id: str = Field(
        default="",
        description="Google OAuth client ID",
    )
    google_client_secret: str = Field(
        default="",
        description="Google OAuth client secret",
    )

    # Admin bootstrap settings
    admin_username: str = Field(
        default="Admin",
        description="Bootstrap admin display name",
    )
    admin_email: str = Field(
        default="admin@example.com",
        description="Bootstrap admin username/email",
    )
    admin_password: str = Field(
        default="change-me",
        description="Bootstrap admin password",
    )

    # OTel settings
    otel_enabled: bool | None = Field(
        default=None,
        validation_alias="OTEL_ENABLED",
        description="Optional tracing toggle. Defaults vary by environment profile.",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        description="OTLP collector endpoint URL",
    )
    otel_trace_file: str = Field(
        default="",
        description="Local trace file path (development/testing only)",
    )

    # Image upload settings (FR-15)
    img_allow_unscanned_uploads: bool = Field(
        default=False,
        validation_alias="IMG_ALLOW_UNSCANNED_UPLOADS",
        description="Allow uploads without scanner in production (auto-promote to READY).",
    )
    media_root: str = Field(
        default="",
        validation_alias="MEDIA_ROOT",
        description="Filesystem path for media storage. Defaults to BASE_DIR/media.",
    )

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def debug(self) -> bool:
        # Profile-driven defaults: dev=true, test=false, prod=false.
        if self.is_production or self.is_testing:
            return False
        if self.django_debug is None:
            return True
        return self.django_debug

    @property
    def api_docs_enabled(self) -> bool:
        return self.is_development or self.is_testing

    @property
    def debug_toolbar_enabled(self) -> bool:
        return self.is_development and self.debug

    @property
    def seed_on_startup(self) -> bool:
        return self.is_testing

    @property
    def manual_seed_allowed(self) -> bool:
        return not self.is_production

    @property
    def ssl_redirect_enabled(self) -> bool:
        if self.django_secure_ssl_redirect is not None:
            return bool(self.django_secure_ssl_redirect)
        return self.is_production

    @property
    def session_cookie_secure(self) -> bool:
        if self.django_session_cookie_secure is not None:
            return bool(self.django_session_cookie_secure)
        return self.is_testing or self.is_production

    @property
    def csrf_cookie_secure(self) -> bool:
        if self.django_csrf_cookie_secure is not None:
            return bool(self.django_csrf_cookie_secure)
        return self.is_testing or self.is_production

    @property
    def effective_otel_enabled(self) -> bool:
        # development: default true, configurable
        if self.is_development:
            return True if self.otel_enabled is None else self.otel_enabled
        # testing: default true for deterministic tracing in integration/e2e
        if self.is_testing:
            return True if self.otel_enabled is None else self.otel_enabled
        # production: opt-in only, default false
        return bool(self.otel_enabled)

    # Computed properties for convenience
    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse DJANGO_ALLOWED_HOSTS into a list."""
        return [h.strip() for h in self.django_allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse DJANGO_CORS_ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.django_cors_allowed_origins.split(",") if o.strip()]

    @property
    def csrf_trusted_origins_list(self) -> list[str]:
        """Parse DJANGO_CSRF_TRUSTED_ORIGINS into a list."""
        return [
            o.strip()
            for o in self.django_csrf_trusted_origins.split(",")
            if o.strip()
        ]

    @model_validator(mode="after")
    def validate_runtime_contract(self) -> "EnvSettings":
        """Fail fast for unsafe production configuration (ENV-UC-02, ENV-CN-02).

        Aggregates all violations in one pass per ENV-CN-02 before raising.
        """
        if not self.is_production:
            return self

        violations: list[str] = []
        for validator in [
            self._validate_debug_override,
            self._validate_secret_key,
            self._validate_admin_bootstrap,
            self._validate_allowed_hosts,
            self._validate_cors,
            self._validate_csrf_trusted_origins,
            self._validate_database_url,
            self._validate_oauth,
            self._validate_otel_export_policy,
        ]:
            try:
                validator()
            except ValueError as exc:
                violations.append(str(exc))

        if violations:
            report = "; ".join(violations)
            raise ValueError(
                f"Production startup blocked — {len(violations)} violation(s): {report}"
            )
        return self

    def _validate_secret_key(self) -> None:
        weak_values = {
            "",
            "change-me-to-a-secure-random-string",
            "django-insecure-local-dev-only-change-in-production",
            "local-dev-secret-change-in-prod",
        }
        if self.django_secret_key.strip() in weak_values:
            raise ValueError(
                "Invalid production DJANGO_SECRET_KEY: default/insecure value is not allowed."
            )

    def _validate_debug_override(self) -> None:
        if self.django_debug is True:
            raise ValueError("Invalid production DJANGO_DEBUG: debug mode cannot be enabled.")

    def _validate_admin_bootstrap(self) -> None:
        weak_admin_emails = {"admin@example.com", "admin"}
        weak_admin_passwords = {"change-me", "admin", "admin123", "password"}
        if self.admin_email.strip().lower() in weak_admin_emails:
            raise ValueError(
                "Invalid production ADMIN_EMAIL: default admin identity is not allowed."
            )
        if (
            self.admin_password.strip() in weak_admin_passwords
            or len(self.admin_password.strip()) < 12
        ):
            raise ValueError(
                "Invalid production ADMIN_PASSWORD: must be non-default and at least 12 chars."
            )

    def _validate_allowed_hosts(self) -> None:
        hosts = [h.lower() for h in self.allowed_hosts_list]
        if not hosts:
            raise ValueError("Invalid production DJANGO_ALLOWED_HOSTS: value cannot be empty.")
        forbidden_hosts = {"localhost", "127.0.0.1"}
        if any(host in forbidden_hosts for host in hosts):
            raise ValueError(
                "Invalid production DJANGO_ALLOWED_HOSTS: localhost entries are not allowed."
            )

    def _validate_cors(self) -> None:
        origins = [origin.lower() for origin in self.cors_origins_list]
        if not origins:
            raise ValueError(
                "Invalid production DJANGO_CORS_ALLOWED_ORIGINS: value cannot be empty."
            )
        for origin in origins:
            if "*" in origin or "localhost" in origin or "127.0.0.1" in origin:
                raise ValueError(
                    "Invalid production DJANGO_CORS_ALLOWED_ORIGINS: "
                    "wildcard/localhost origins are not allowed."
                )

    def _validate_csrf_trusted_origins(self) -> None:
        origins = self.csrf_trusted_origins_list
        if not origins:
            raise ValueError(
                "Invalid production DJANGO_CSRF_TRUSTED_ORIGINS: value cannot be empty."
            )
        for origin in origins:
            if "localhost" in origin.lower() or "127.0.0.1" in origin:
                raise ValueError(
                    "Invalid production DJANGO_CSRF_TRUSTED_ORIGINS: "
                    "localhost origins are not allowed."
                )

    def _validate_database_url(self) -> None:
        raw = self.database_url.lower()
        weak_tokens = ("eelab", "datadash", "localdev", "change-me", "localhost")
        if any(token in raw for token in weak_tokens):
            raise ValueError(
                "Invalid production DATABASE_URL: default/local credentials "
                "or host are not allowed."
            )

    def _validate_oauth(self) -> None:
        client_id = self.google_client_id.strip()
        client_secret = self.google_client_secret.strip()
        if not client_id or not client_secret:
            raise ValueError(
                "Invalid production OAuth config: GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET are required."
            )

    def _validate_otel_export_policy(self) -> None:
        if not self.effective_otel_enabled:
            return
        if not self.otel_exporter_otlp_endpoint.strip():
            raise ValueError(
                "Invalid production OTEL config: OTLP endpoint is required when OTEL is enabled."
            )
        if self.otel_trace_file.strip():
            raise ValueError(
                "Invalid production OTEL config: local trace file export is not allowed."
            )


@lru_cache
def get_env_settings() -> EnvSettings:
    """
    Get cached environment settings.

    Settings are loaded once and cached for the lifetime of the application.
    This ensures consistent configuration and avoids repeated env var parsing.
    """
    return EnvSettings()


# Convenience alias for importing: `from config.env import env`
env = get_env_settings()
