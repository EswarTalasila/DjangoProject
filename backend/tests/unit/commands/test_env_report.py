"""Unit tests for env_report diagnostics command."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.management.base import CommandError

from core.management.commands import env_report

pytestmark = pytest.mark.unit



def _mock_env(**overrides):
    base = {
        "environment": "testing",
        "django_secret_key": "change-me-to-a-secure-random-string",
        "admin_email": "admin@example.com",
        "admin_password": "change-me",
        "database_url": "postgres://eelab:change-me@database:5432/eelab",
        "google_client_id": "",
        "google_client_secret": "",
        "django_debug": True,
        "allowed_hosts_list": ["localhost", "127.0.0.1"],
        "cors_origins_list": ["http://localhost:3000", "*"],
        "effective_otel_enabled": True,
        "otel_exporter_otlp_endpoint": "",
        "otel_trace_file": "Docs/diagrams/otel/traces.jsonl",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_collect_findings_for_production_includes_strict_errors(monkeypatch):
    """Production profile emits ERROR findings for hardened-policy violations."""
    monkeypatch.setattr(env_report, "env", _mock_env(environment="production"))
    command = env_report.Command()

    findings = command._collect_findings("production")
    by_code = {finding.code: finding for finding in findings}

    assert by_code["ENV-S001"].level == "ERROR"
    assert by_code["ENV-A001"].level == "ERROR"
    assert by_code["ENV-A002"].level == "ERROR"
    assert by_code["ENV-D001"].level == "ERROR"
    assert by_code["ENV-O001"].level == "ERROR"
    assert by_code["ENV-N001"].level == "ERROR"
    assert by_code["ENV-N002"].level == "ERROR"
    assert by_code["ENV-T001"].level == "ERROR"
    assert by_code["ENV-T002"].level == "ERROR"


def test_collect_findings_for_testing_emits_expected_warnings(monkeypatch):
    """Non-production profiles emit warnings rather than hard errors."""
    monkeypatch.setattr(env_report, "env", _mock_env(environment="testing"))
    command = env_report.Command()

    findings = command._collect_findings("testing")
    codes = {finding.code for finding in findings}

    assert "ENV-W002" in codes  # explicit DJANGO_DEBUG override warning
    assert all(finding.level == "WARN" for finding in findings)


def test_handle_strict_raises_when_error_findings_exist(monkeypatch):
    """--strict fails command execution when ERROR findings are present."""
    command = env_report.Command()
    monkeypatch.setattr(
        command,
        "_collect_findings",
        lambda profile: [
            env_report.Finding(
                code="ENV-T001",
                level="ERROR",
                message="OTEL endpoint missing",
                hint="Set endpoint",
            )
        ],
    )

    with pytest.raises(CommandError, match="environment check failed with 1 error"):
        command.handle(profile="production", strict=True)


def test_handle_non_strict_outputs_warn_status(monkeypatch, capsys):
    """Non-strict runs print warnings but do not raise."""
    command = env_report.Command()
    monkeypatch.setattr(
        command,
        "_collect_findings",
        lambda profile: [
            env_report.Finding(
                code="ENV-W001",
                level="WARN",
                message="profile mismatch",
                hint="match runtime",
            )
        ],
    )

    command.handle(profile="testing", strict=False)
    captured = capsys.readouterr().out

    assert "[env-check] profile=testing status=warn" in captured
    assert "WARN ENV-W001: profile mismatch" in captured
