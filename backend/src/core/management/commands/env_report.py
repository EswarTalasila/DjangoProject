"""Concise environment diagnostics for runtime profiles."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError

from config.env import env


@dataclass
class Finding:
    code: str
    level: str
    message: str
    hint: str


class Command(BaseCommand):
    """Print concise environment diagnostics with actionable hints."""

    help = "Show profile-aware env warnings/errors with fix hints."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=["development", "testing", "production"],
            default=env.environment,
            help="Profile context for diagnostics.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit non-zero when ERROR findings exist.",
        )

    def handle(self, *args, **options):
        profile = options["profile"]
        strict = options["strict"]

        findings = self._collect_findings(profile)
        error_count = sum(1 for finding in findings if finding.level == "ERROR")
        warn_count = sum(1 for finding in findings if finding.level == "WARN")

        if error_count:
            status = "error"
        elif warn_count:
            status = "warn"
        else:
            status = "ok"

        self.stdout.write(f"[env-check] profile={profile} status={status}")

        for finding in findings:
            self.stdout.write(f"{finding.level} {finding.code}: {finding.message}")
            self.stdout.write(f"  hint: {finding.hint}")

        if strict and error_count:
            raise CommandError(f"environment check failed with {error_count} error(s).")

    def _collect_findings(self, profile: str) -> list[Finding]:
        findings: list[Finding] = []

        weak_secret_keys = {
            "",
            "change-me-to-a-secure-random-string",
            "django-insecure-local-dev-only-change-in-production",
            "local-dev-secret-change-in-prod",
        }
        weak_admin_emails = {"admin@example.com", "admin"}
        weak_admin_passwords = {"change-me", "admin", "admin123", "password"}
        weak_db_tokens = ("change-me", "localdev")

        def add_finding(
            *,
            condition: bool,
            code: str,
            message: str,
            hint: str,
            strict_in_production: bool = False,
        ) -> None:
            if not condition:
                return
            level = "ERROR" if profile == "production" and strict_in_production else "WARN"
            findings.append(Finding(code=code, level=level, message=message, hint=hint))

        add_finding(
            condition=env.environment != profile,
            code="ENV-W001",
            message=(
                f"runtime profile is '{env.environment}' but report was requested for '{profile}'."
            ),
            hint="Run profile check with matching ENVIRONMENT value.",
        )

        add_finding(
            condition=env.django_secret_key.strip() in weak_secret_keys,
            code="ENV-S001",
            message="DJANGO_SECRET_KEY is a default/insecure value.",
            hint="Set DJANGO_SECRET_KEY in .env to a unique random secret.",
            strict_in_production=True,
        )
        add_finding(
            condition=env.admin_email.strip().lower() in weak_admin_emails,
            code="ENV-A001",
            message="ADMIN_EMAIL is using a default identity.",
            hint="Set ADMIN_EMAIL to a non-default admin address in .env.",
            strict_in_production=True,
        )
        add_finding(
            condition=env.admin_password.strip() in weak_admin_passwords
            or len(env.admin_password.strip()) < 12,
            code="ENV-A002",
            message="ADMIN_PASSWORD is weak or default.",
            hint="Set ADMIN_PASSWORD to a strong non-default password (>=12 chars).",
            strict_in_production=True,
        )
        add_finding(
            condition=any(token in env.database_url.lower() for token in weak_db_tokens),
            code="ENV-D001",
            message="DATABASE_URL appears to use default credentials.",
            hint="Set DATABASE_URL with non-default credentials for your target profile.",
            strict_in_production=True,
        )
        add_finding(
            condition=not env.google_client_id.strip() or not env.google_client_secret.strip(),
            code="ENV-O001",
            message="Google OAuth backend credentials are missing.",
            hint="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.",
            strict_in_production=True,
        )
        add_finding(
            condition=profile != "development" and env.django_debug is not None,
            code="ENV-W002",
            message=(
                "DJANGO_DEBUG override is set but profile defaults control "
                "debug outside development."
            ),
            hint="Remove DJANGO_DEBUG from .env for testing/production profiles.",
        )

        if profile == "production":
            hosts = [host.lower() for host in env.allowed_hosts_list]
            origins = [origin.lower() for origin in env.cors_origins_list]
            add_finding(
                condition=any(host in {"localhost", "127.0.0.1"} for host in hosts),
                code="ENV-N001",
                message="DJANGO_ALLOWED_HOSTS includes localhost in production.",
                hint="Set DJANGO_ALLOWED_HOSTS to production hostnames only.",
                strict_in_production=True,
            )
            add_finding(
                condition=any(
                    "*" in origin or "localhost" in origin or "127.0.0.1" in origin
                    for origin in origins
                ),
                code="ENV-N002",
                message="DJANGO_CORS_ALLOWED_ORIGINS includes unsafe localhost/wildcard values.",
                hint="Set explicit trusted production origins only.",
                strict_in_production=True,
            )
        return findings
