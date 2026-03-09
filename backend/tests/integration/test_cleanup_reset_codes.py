"""Unit tests for cleanup_reset_codes management command."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
@pytest.mark.integration
def test_cleanup_reset_codes_command_prints_summary(monkeypatch):
    """Command prints service summary output with success style."""

    monkeypatch.setattr(
        "accounts.management.commands.cleanup_reset_codes.cleanup_temporary_reset_codes",
        lambda: {"codesDeleted": 3, "requestsExpired": 2},
    )

    out = StringIO()
    call_command("cleanup_reset_codes", stdout=out)
    output = out.getvalue()

    assert "Cleanup complete" in output
    assert "codes_deleted=3" in output
    assert "requests_expired=2" in output
