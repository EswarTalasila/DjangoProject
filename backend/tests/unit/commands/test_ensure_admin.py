"""Unit tests for ensure_admin management command."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_creates_admin_when_missing(monkeypatch):
    """Creates startup admin user when no matching account exists."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="new-admin@example.com",
            admin_password="StrongPass123!",
            admin_username="Boot Admin",
            is_production=False,
        ),
    )

    out = StringIO()
    call_command("ensure_admin", stdout=out)

    user = User.objects.get(username="new-admin@example.com")
    assert user.email == "new-admin@example.com"
    assert user.name == "Boot Admin"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert "Created admin user" in out.getvalue()


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_reconciles_existing_user(monkeypatch):
    """Existing user matching email/username is promoted/reconciled to admin."""

    user = User.objects.create_user(
        username="existing@example.com",
        email="old@example.com",
        name="Old Name",
        password="StrongPass123!",
    )
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["is_staff", "is_superuser"])

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="existing@example.com",
            admin_password="StrongPass123!",
            admin_username="New Admin Name",
            is_production=False,
        ),
    )

    out = StringIO()
    call_command("ensure_admin", stdout=out)

    user.refresh_from_db()
    assert user.email == "existing@example.com"
    assert user.name == "New Admin Name"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert "Reconciled admin user" in out.getvalue()


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_skips_when_existing_already_correct(monkeypatch):
    """No-op message emitted when admin already matches target config."""

    user = User.objects.create_user(
        username="ok@example.com",
        email="ok@example.com",
        name="Admin",
        password="StrongPass123!",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="ok@example.com",
            admin_password="StrongPass123!",
            admin_username="Admin",
            is_production=False,
        ),
    )

    out = StringIO()
    call_command("ensure_admin", stdout=out)
    assert "Admin user already exists" in out.getvalue()


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_production_requires_valid_email(monkeypatch):
    """Production bootstrap rejects invalid admin email values."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="not-an-email",
            admin_password="StrongPass123!",
            admin_username="Prod Admin",
            is_production=True,
        ),
    )

    with pytest.raises(CommandError, match="valid email address"):
        call_command("ensure_admin")


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_production_rejects_weak_password(monkeypatch):
    """Production bootstrap rejects weak/default passwords."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="prod-admin@example.com",
            admin_password="short",
            admin_username="Prod Admin",
            is_production=True,
        ),
    )

    with pytest.raises(CommandError, match="ADMIN_PASSWORD"):
        call_command("ensure_admin")


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_production_rejects_empty_email(monkeypatch):
    """Production bootstrap rejects empty admin email."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="",
            admin_password="StrongPass123!",
            admin_username="Prod Admin",
            is_production=True,
        ),
    )

    with pytest.raises(CommandError, match="ADMIN_EMAIL is required"):
        call_command("ensure_admin")


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_production_rejects_default_email(monkeypatch):
    """Production bootstrap rejects default/weak admin email."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="admin@example.com",
            admin_password="StrongAdminPass123!",
            admin_username="Prod Admin",
            is_production=True,
        ),
    )

    with pytest.raises(CommandError, match="Default ADMIN_EMAIL"):
        call_command("ensure_admin")


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_production_rejects_empty_password(monkeypatch):
    """Production bootstrap rejects empty admin password."""

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="real-admin@example.com",
            admin_password="",
            admin_username="Prod Admin",
            is_production=True,
        ),
    )

    with pytest.raises(CommandError, match="ADMIN_PASSWORD is required"):
        call_command("ensure_admin")


@pytest.mark.django_db
@pytest.mark.unit
def test_ensure_admin_reconciles_only_email_mismatch(monkeypatch):
    """User found by username but email differs triggers reconciliation."""

    user = User.objects.create_user(
        username="email-mismatch@example.com",
        email="wrong@example.com",
        name="Admin",
        password="StrongPass123!",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])

    monkeypatch.setattr(
        "accounts.management.commands.ensure_admin.env",
        SimpleNamespace(
            admin_email="email-mismatch@example.com",
            admin_password="StrongPass123!",
            admin_username="Admin",
            is_production=False,
        ),
    )

    out = StringIO()
    call_command("ensure_admin", stdout=out)

    user.refresh_from_db()
    assert user.email == "email-mismatch@example.com"
    assert "Reconciled admin user" in out.getvalue()
