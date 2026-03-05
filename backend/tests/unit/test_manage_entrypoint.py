"""Unit tests for Django manage.py entrypoint."""

from __future__ import annotations

import os

import pytest

import manage

pytestmark = pytest.mark.unit



def test_manage_main_sets_default_settings_and_executes(monkeypatch):
    """main() sets DJANGO_SETTINGS_MODULE and delegates to Django CLI executor."""
    captured = {}
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr(manage.sys, "argv", ["manage.py", "check"])
    monkeypatch.setattr(
        "django.core.management.execute_from_command_line",
        lambda argv: captured.update(argv=argv),
    )

    manage.main()

    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings"
    assert captured["argv"] == ["manage.py", "check"]
