"""Unit tests for seed_e2e management command."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import Role, User


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_blocked_in_production(monkeypatch):
    """Seed command is blocked when runtime is production."""

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=True),
    )

    with pytest.raises(CommandError, match="blocked in production"):
        call_command("seed_e2e")


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_creates_baseline_users(monkeypatch):
    """Creates admin, teacher, and student users with expected roles/profiles."""

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )
    monkeypatch.setenv("E2E_ADMIN_USERNAME", "seed-admin@example.com")
    monkeypatch.setenv("E2E_ADMIN_PASSWORD", "SeedAdminPass123!")
    monkeypatch.setenv("E2E_TEACHER_USERNAME", "seed-teacher@example.com")
    monkeypatch.setenv("E2E_TEACHER_PASSWORD", "SeedTeacherPass123!")
    monkeypatch.setenv("E2E_STUDENT_USERNAME", "seed-student@example.com")
    monkeypatch.setenv("E2E_STUDENT_PASSWORD", "SeedStudentPass123!")

    out = StringIO()
    call_command("seed_e2e", stdout=out)

    admin = User.objects.get(username="seed-admin@example.com")
    teacher = User.objects.get(username="seed-teacher@example.com")
    student = User.objects.get(username="seed-student@example.com")

    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert teacher.roles.filter(role=Role.TEACHER).exists()
    assert teacher.teacher_profile is not None
    assert student.roles.filter(role=Role.STUDENT).exists()
    assert student.student_profile is not None
    assert "E2E seed completed" in out.getvalue()


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_idempotent(monkeypatch):
    """Repeated runs do not duplicate users."""

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )

    call_command("seed_e2e")
    count_after_first = User.objects.count()
    call_command("seed_e2e")
    count_after_second = User.objects.count()

    assert count_after_second == count_after_first


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_force_password_updates_existing(monkeypatch):
    """--force-password updates existing account passwords."""

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )
    monkeypatch.setenv("E2E_TEACHER_USERNAME", "force-teacher@example.com")
    monkeypatch.setenv("E2E_TEACHER_PASSWORD", "NewForcePass123!")

    user = User.objects.create_user(
        username="force-teacher@example.com",
        name="Teacher",
        password="OldPass123!",
    )

    call_command("seed_e2e", "--force-password")
    user.refresh_from_db()

    assert user.check_password("NewForcePass123!")


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_ensure_admin_updates_name_and_staff(monkeypatch):
    """Existing admin user with wrong name/staff flags gets reconciled."""

    user = User.objects.create_user(
        username="admin-update@example.com",
        name="Old Name",
        password="AdminPass123!",
    )
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["is_staff", "is_superuser"])

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )
    monkeypatch.setenv("E2E_ADMIN_USERNAME", "admin-update@example.com")
    monkeypatch.setenv("E2E_ADMIN_PASSWORD", "AdminPass123!")
    monkeypatch.setenv("E2E_ADMIN_NAME", "New Admin Name")

    out = StringIO()
    call_command("seed_e2e", stdout=out)

    user.refresh_from_db()
    assert user.name == "New Admin Name"
    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_ensure_user_updates_name(monkeypatch):
    """Existing role user with different name gets name updated."""

    user = User.objects.create_user(
        username="teacher-name-update@example.com",
        name="Old Teacher",
        password="TeacherPass123!",
    )

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )
    monkeypatch.setenv("E2E_TEACHER_USERNAME", "teacher-name-update@example.com")
    monkeypatch.setenv("E2E_TEACHER_PASSWORD", "TeacherPass123!")

    out = StringIO()
    call_command("seed_e2e", stdout=out)

    user.refresh_from_db()
    assert user.name == "Teacher"
    assert "Updated" in out.getvalue()


@pytest.mark.django_db
@pytest.mark.integration
def test_seed_e2e_no_force_password_skips_password_update(monkeypatch):
    """Without --force-password, existing user password is not changed."""

    user = User.objects.create_user(
        username="no-force@example.com",
        name="Teacher",
        password="OldPass123!",
    )

    monkeypatch.setattr(
        "accounts.management.commands.seed_e2e.env",
        SimpleNamespace(is_production=False),
    )
    monkeypatch.setenv("E2E_TEACHER_USERNAME", "no-force@example.com")
    monkeypatch.setenv("E2E_TEACHER_PASSWORD", "NewPass123!")

    call_command("seed_e2e")

    user.refresh_from_db()
    assert user.check_password("OldPass123!") is True
    assert user.check_password("NewPass123!") is False
