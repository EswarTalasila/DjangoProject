"""
Environment configuration using pydantic-settings.

This module provides type-safe, validated configuration loaded from environment
variables. The app fails fast on startup if required config is missing or invalid.

Usage:
    from config.env import env

    if env.debug:
        print("Debug mode enabled")

    database_url = env.database_url
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """
    Application environment settings.

    All settings are loaded from environment variables. Variable names are
    case-insensitive and use the prefixes defined below.

    Required variables (no defaults):
        - DJANGO_SECRET_KEY: Secret key for Django sessions and CSRF

    Optional variables (have sensible defaults for development):
        - DJANGO_DEBUG: Enable debug mode (default: true)
        - DJANGO_ALLOWED_HOSTS: Comma-separated allowed hosts
        - DATABASE_URL: PostgreSQL connection string
        - DJANGO_CORS_ALLOWED_ORIGINS: Comma-separated CORS origins
        - GOOGLE_CLIENT_ID: Google OAuth client ID
        - GOOGLE_CLIENT_SECRET: Google OAuth client secret
    """

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
    )

    # Django core settings
    django_secret_key: str = Field(
        default="django-insecure-local-dev-only-change-in-production",
        description="Django secret key for sessions and CSRF protection",
    )
    django_debug: bool = Field(
        default=True,
        description="Enable Django debug mode (disable in production)",
    )
    django_allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts",
    )

    # Database
    database_url: str = Field(
        default="postgres://datadash:localdev@localhost:5432/datadash",
        description="PostgreSQL connection URL",
    )

    # CORS
    django_cors_allowed_origins: str = Field(
        default="http://localhost:4200",
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

    # Computed properties for convenience
    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse DJANGO_ALLOWED_HOSTS into a list."""
        return [h.strip() for h in self.django_allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse DJANGO_CORS_ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.django_cors_allowed_origins.split(",") if o.strip()]


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
