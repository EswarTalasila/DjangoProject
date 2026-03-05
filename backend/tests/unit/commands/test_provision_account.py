"""Unit tests for provision_account management command.

Tests mock service-layer dependencies and all ORM access to verify command
logic: production blocking, role dispatch, dependency provisioning, and
output formatting. No database access is required.
"""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

CMD = "accounts.management.commands.provision_account"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_user(*, username="mock.user", email="", name="Mock User", is_staff=False):
    """Build a mock user object matching the fields the command accesses."""
    user = MagicMock()
    user.username = username
    user.email = email
    user.name = name
    user.is_staff = is_staff
    return user


# ---------------------------------------------------------------------------
# Production guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_production_blocked(monkeypatch):
    """Command is blocked in production environment."""
    monkeypatch.setattr(
        f"{CMD}.env",
        SimpleNamespace(is_production=True),
    )
    with pytest.raises(CommandError, match="blocked in production"):
        call_command("provision_account", "--role", "all")


# ---------------------------------------------------------------------------
# Role argument parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invalid_role_rejected():
    """Invalid role argument is rejected by argparse."""
    with pytest.raises(CommandError, match="invalid choice"):
        call_command("provision_account", "--role", "invalid_role")


# ---------------------------------------------------------------------------
# Skip when already exists
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_researcher_skipped_when_existing(mock_user_model, monkeypatch):
    """Existing researcher account is skipped with 'already provisioned' message."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "researcher", stdout=out)
    assert "already provisioned" in out.getvalue()


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_teacher_skipped_when_existing(mock_user_model, monkeypatch):
    """Existing teacher account is skipped."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="morgan.blake", email="teacher@example.com",
        name="Morgan Blake",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "teacher", stdout=out)
    assert "already provisioned" in out.getvalue()


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_student_skipped_when_existing(mock_user_model, monkeypatch):
    """Existing student account is skipped (lookup by name)."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="alex.torres", email="", name="Alex Torres",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "student", stdout=out)
    assert "already provisioned" in out.getvalue()


# ---------------------------------------------------------------------------
# Provisioning dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch(f"{CMD}.redeem_non_student_local_invite")
@patch(f"{CMD}.create_registration_codes")
@patch(f"{CMD}.User")
def test_researcher_provisioned(mock_user_model, mock_create_codes, mock_redeem, monkeypatch):
    """Researcher provisioning generates code and redeems invite."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))

    # _find_existing returns None (no existing user)
    mock_user_model.objects.filter.return_value.first.return_value = None
    # _get_admin returns an admin user
    admin = _mock_user(username="admin@example.com", name="Admin", is_staff=True)
    mock_user_model.objects.filter.return_value.first.side_effect = [
        None,   # _find_existing for researcher -> no existing
        admin,  # _get_admin -> admin user
    ]

    mock_code = MagicMock()
    mock_code.plaintext_code = "RESEARCH-CODE"
    mock_create_codes.return_value = [mock_code]

    provisioned_user = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    mock_redeem.return_value = provisioned_user

    out = StringIO()
    call_command("provision_account", "--role", "researcher", stdout=out)

    mock_create_codes.assert_called_once()
    mock_redeem.assert_called_once()
    output = out.getvalue()
    assert "provisioned" in output
    assert "robin.carter" in output


@pytest.mark.unit
@patch(f"{CMD}.redeem_non_student_local_invite")
@patch(f"{CMD}.create_registration_codes")
@patch(f"{CMD}.User")
def test_teacher_provision_ensures_researcher_first(
    mock_user_model, mock_create_codes, mock_redeem, monkeypatch
):
    """Teacher provisioning ensures researcher exists first."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))

    admin = _mock_user(username="admin@example.com", name="Admin", is_staff=True)
    researcher = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    teacher = _mock_user(
        username="morgan.blake", email="teacher@example.com",
        name="Morgan Blake",
    )

    # The command calls User.objects.filter(...) with both Q objects (positional)
    # and keyword args. We need a side_effect that handles both patterns.
    # For researcher: _ensure_provisioned calls _find_existing (returns None),
    # then _provision calls _find_existing again (returns None), then after
    # redeem, _get_user returns the researcher.
    # For teacher: _find_existing returns None (first), then after redeem
    # returns the teacher.
    state = {"researcher_miss_count": 0, "teacher_miss_count": 0}

    def _filter_side_effect(*args, **kwargs):
        """Return a mock queryset whose .first() returns the right user."""
        qs = MagicMock()
        # is_staff=True -> admin lookup
        if kwargs.get("is_staff") is True:
            qs.first.return_value = admin
            return qs
        # Determine which email is being looked up (Q object or kwargs)
        lookup_email = None
        if args:
            q_str = str(args[0])
            if "researcher@example.com" in q_str:
                lookup_email = "researcher@example.com"
            elif "teacher@example.com" in q_str:
                lookup_email = "teacher@example.com"
        if not lookup_email:
            lookup_email = kwargs.get("email__iexact")

        if lookup_email == "researcher@example.com":
            # Return None for the first 2 lookups (_ensure_provisioned +
            # _provision's _find_existing), then return researcher for
            # _get_user and beyond.
            state["researcher_miss_count"] += 1
            if state["researcher_miss_count"] <= 2:
                qs.first.return_value = None
            else:
                qs.first.return_value = researcher
            return qs
        if lookup_email == "teacher@example.com":
            state["teacher_miss_count"] += 1
            if state["teacher_miss_count"] <= 1:
                qs.first.return_value = None
            else:
                qs.first.return_value = teacher
            return qs
        qs.first.return_value = None
        return qs

    mock_user_model.objects.filter.side_effect = _filter_side_effect

    mock_code = MagicMock()
    mock_code.plaintext_code = "SOME-CODE"
    mock_create_codes.return_value = [mock_code]

    redeem_counter = {"count": 0}

    def _redeem(payload):
        redeem_counter["count"] += 1
        if redeem_counter["count"] == 1:
            return researcher
        return teacher

    mock_redeem.side_effect = _redeem

    out = StringIO()
    call_command("provision_account", "--role", "teacher", stdout=out)

    # Called twice: once for researcher dependency, once for teacher.
    assert mock_redeem.call_count == 2


@pytest.mark.unit
@patch(f"{CMD}.create_course")
@patch(f"{CMD}.redeem_student_invite")
@patch(f"{CMD}.redeem_non_student_local_invite")
@patch(f"{CMD}.create_registration_codes")
@patch(f"{CMD}.User")
def test_student_provision_ensures_teacher_first(
    mock_user_model, mock_create_codes, mock_redeem_non_student, mock_redeem_student,
    mock_create_course, monkeypatch,
):
    """Student provisioning ensures teacher (and researcher) exist first."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))

    admin = _mock_user(username="admin@example.com", name="Admin", is_staff=True)
    researcher = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    teacher = _mock_user(
        username="morgan.blake", email="teacher@example.com",
        name="Morgan Blake",
    )
    student = _mock_user(
        username="alex.torres", email="", name="Alex Torres",
    )

    state = {"researcher_seen": False, "teacher_seen": False}

    def _filter_side_effect(*args, **kwargs):
        qs = MagicMock()
        if kwargs.get("is_staff") is True:
            qs.first.return_value = admin
            return qs
        # Q object lookup (positional arg) for email__iexact
        if args:
            q_str = str(args[0])
            if "researcher@example.com" in q_str:
                if not state["researcher_seen"]:
                    state["researcher_seen"] = True
                    qs.first.return_value = None
                else:
                    qs.first.return_value = researcher
                return qs
            if "teacher@example.com" in q_str:
                if not state["teacher_seen"]:
                    state["teacher_seen"] = True
                    qs.first.return_value = None
                else:
                    qs.first.return_value = teacher
                return qs
        # Keyword-based lookups
        email = kwargs.get("email__iexact")
        if email == "researcher@example.com":
            if not state["researcher_seen"]:
                state["researcher_seen"] = True
                qs.first.return_value = None
            else:
                qs.first.return_value = researcher
            return qs
        if email == "teacher@example.com":
            if not state["teacher_seen"]:
                state["teacher_seen"] = True
                qs.first.return_value = None
            else:
                qs.first.return_value = teacher
            return qs
        # name= lookup for student
        name = kwargs.get("name")
        if name == "Alex Torres":
            qs.first.return_value = None
            return qs
        qs.first.return_value = None
        return qs

    mock_user_model.objects.filter.side_effect = _filter_side_effect

    mock_code = MagicMock()
    mock_code.plaintext_code = "SOME-CODE"
    mock_create_codes.return_value = [mock_code]

    redeem_counter = {"count": 0}

    def _redeem_non_student(payload):
        redeem_counter["count"] += 1
        if redeem_counter["count"] == 1:
            return researcher
        return teacher

    mock_redeem_non_student.side_effect = _redeem_non_student

    mock_course = MagicMock()
    mock_course.id = 1
    mock_create_course.return_value = mock_course

    # Course is imported locally inside _ensure_course from courses.models
    with patch("courses.models.Course") as mock_course_model:
        mock_course_model.objects.filter.return_value.first.return_value = None

        mock_enrollment = MagicMock()
        mock_redeem_student.return_value = (student, mock_enrollment)

        out = StringIO()
        call_command("provision_account", "--role", "student", stdout=out)

    mock_redeem_student.assert_called_once()
    output = out.getvalue()
    assert "alex.torres" in output.lower() or "Alex" in output


# ---------------------------------------------------------------------------
# No admin user
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_no_admin_raises_command_error(mock_user_model, monkeypatch):
    """Missing admin user raises CommandError."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    # _find_existing returns None, _get_admin also returns None
    mock_user_model.objects.filter.return_value.first.return_value = None
    with pytest.raises(CommandError, match="No admin user found"):
        call_command("provision_account", "--role", "researcher")


# ---------------------------------------------------------------------------
# _print_account output formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_print_account_includes_credentials(mock_user_model, monkeypatch):
    """Output includes username, password, and name fields."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "researcher", stdout=out)
    output = out.getvalue()
    assert "username:" in output
    assert "password:" in output
    assert "first name:" in output
    assert "last name:" in output


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_print_account_includes_email_when_present(mock_user_model, monkeypatch):
    """Output includes email line when user has an email."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="robin.carter", email="researcher@example.com",
        name="Robin Carter",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "researcher", stdout=out)
    assert "email:" in out.getvalue()


@pytest.mark.unit
@patch(f"{CMD}.User")
def test_print_account_omits_email_when_absent(mock_user_model, monkeypatch):
    """Output omits email line when user has no email."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    existing = _mock_user(
        username="alex.torres", email="", name="Alex Torres",
    )
    mock_user_model.objects.filter.return_value.first.return_value = existing
    out = StringIO()
    call_command("provision_account", "--role", "student", stdout=out)
    assert "email:" not in out.getvalue()


# ---------------------------------------------------------------------------
# "all" role provisions all three
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch(f"{CMD}.Command._provision")
def test_all_role_provisions_each(mock_provision, monkeypatch):
    """--role all calls _provision for researcher, teacher, and student."""
    monkeypatch.setattr(f"{CMD}.env", SimpleNamespace(is_production=False))
    call_command("provision_account", "--role", "all")
    assert mock_provision.call_count == 3
    roles_provisioned = [call.args[0] for call in mock_provision.call_args_list]
    assert roles_provisioned == ["researcher", "teacher", "student"]
