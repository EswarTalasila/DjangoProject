"""Unit tests for authentication-focused service helpers."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import ResearcherProfile, Role, TeacherProfile, UserRole
from accounts.services import (
    authenticate_user,
    blacklist_refresh_token,
    build_user_response,
    check_identifier_throttle,
    clear_identifier_failures,
    find_user_by_identifier,
    identifier_allowed_for_user,
    invalidate_user_sessions,
    normalize_registration_code_input,
    normalize_username_identifier,
    password_strength_errors,
    register_identifier_failure,
)

User = get_user_model()


def _make_user(
    *, username: str, role: str, email: str | None = None, password: str = "StartPass123!"
):
    user = User.objects.create_user(
        username=username, email=email, name=username, password=password
    )
    UserRole.objects.create(user=user, role=role)
    if role == Role.TEACHER:
        TeacherProfile.objects.create(user=user)
    if role == Role.RESEARCHER:
        ResearcherProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
@pytest.mark.unit
def test_password_strength_errors_reports_expected_violations():
    """Weak password returns all missing policy dimensions."""

    errors = password_strength_errors("abc")
    assert "Password must be at least 8 characters." in errors
    assert "Password must include at least one uppercase letter." in errors
    assert "Password must include at least one number." in errors
    assert "Password must include at least one special character." in errors


@pytest.mark.django_db
@pytest.mark.unit
def test_normalize_identifier_helpers():
    """Identifier/code normalization trims and normalizes case."""

    assert normalize_username_identifier("  TEACHER@EXAMPLE.COM  ") == "teacher@example.com"
    assert normalize_registration_code_input("  reg-abc123 ") == "REG-ABC123"


@pytest.mark.django_db
@pytest.mark.unit
def test_find_user_by_identifier_username_and_email_paths():
    """Lookup works for username, email, and rejects empty."""

    user = _make_user(username="teacher-one", role=Role.TEACHER, email="teacher-one@example.com")

    assert find_user_by_identifier("") is None
    assert find_user_by_identifier("teacher-one").id == user.id
    assert find_user_by_identifier("teacher-one@example.com").id == user.id


@pytest.mark.django_db
@pytest.mark.unit
def test_identifier_allowed_for_user_student_username_only(admin_user):
    """Students may authenticate only by username; non-students may use email."""

    student = User.objects.create_user(
        username="student-one",
        email="student-one@example.com",
        name="Student One",
        password="StartPass123!",
    )
    UserRole.objects.create(user=student, role=Role.STUDENT)
    from accounts.models import StudentProfile

    StudentProfile.objects.create(user=student, created_by=admin_user, consent=False)

    teacher = _make_user(
        username="teacher-two",
        role=Role.TEACHER,
        email="teacher-two@example.com",
    )

    assert identifier_allowed_for_user("student-one", student) is True
    assert identifier_allowed_for_user("student-one@example.com", student) is False
    assert identifier_allowed_for_user("teacher-two", teacher) is True
    assert identifier_allowed_for_user("teacher-two@example.com", teacher) is True


@pytest.mark.django_db
@pytest.mark.unit
def test_authenticate_user_success_and_failure():
    """Authentication returns user on valid credentials and None otherwise."""

    user = _make_user(
        username="auth-user",
        role=Role.TEACHER,
        email="auth-user@example.com",
        password="StartPass123!",
    )

    assert authenticate_user("auth-user", "WrongPass123!") is None
    authed = authenticate_user("auth-user@example.com", "StartPass123!")
    assert authed is not None
    assert authed.id == user.id


@pytest.mark.django_db
@pytest.mark.unit
def test_build_user_response_refresh_optional():
    """Response payload includes role/id and optional refresh token."""

    user = _make_user(username="resp-user", role=Role.RESEARCHER, email="resp-user@example.com")

    with_refresh = build_user_response(user, "access", "refresh")
    no_refresh = build_user_response(user, "access")

    assert with_refresh["refreshToken"] == "refresh"
    assert no_refresh.get("refreshToken") is None
    assert with_refresh["role"] == Role.RESEARCHER


@pytest.mark.django_db
@pytest.mark.unit
def test_blacklist_refresh_token_invalid_token_returns_false():
    """Invalid refresh token strings fail gracefully."""

    assert blacklist_refresh_token("not-a-jwt") is False


@pytest.mark.django_db
@pytest.mark.unit
def test_invalidate_user_sessions_blacklists_outstanding_tokens():
    """Outstanding refresh tokens are blacklisted and counted once."""

    user = _make_user(username="session-user", role=Role.TEACHER, email="session@example.com")
    t1 = RefreshToken.for_user(user)
    t2 = RefreshToken.for_user(user)

    first = invalidate_user_sessions(user)
    second = invalidate_user_sessions(user)

    assert first >= 2
    assert second == 0
    assert str(t1) != str(t2)


@pytest.mark.django_db
@pytest.mark.unit
def test_identifier_throttle_lifecycle():
    """Throttle counter increments and clears by identifier scope."""

    identifier = "throttle-user@example.com"
    for _ in range(5):
        assert check_identifier_throttle("login", identifier) is True
        register_identifier_failure("login", identifier)

    assert check_identifier_throttle("login", identifier) is False
    clear_identifier_failures("login", identifier)
    assert check_identifier_throttle("login", identifier) is True


# --- Branch-coverage additions ---


@pytest.mark.django_db
@pytest.mark.unit
def test_identifier_allowed_for_user_empty_identifier_returns_false():
    """Empty identifier is rejected for any user."""

    teacher = _make_user(
        username="teacher-empty-id", role=Role.TEACHER, email="t-empty@example.com"
    )
    assert identifier_allowed_for_user("", teacher) is False
    assert identifier_allowed_for_user("   ", teacher) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_identifier_allowed_for_user_no_email_returns_false():
    """Non-student user without email rejects email-style identifier."""

    user = User.objects.create_user(
        username="no-email-user", email=None, name="No Email", password="StartPass123!"
    )
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)

    assert identifier_allowed_for_user("no-email-user", user) is True
    assert identifier_allowed_for_user("someone@example.com", user) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_password_strength_errors_missing_lowercase():
    """Password missing only lowercase is flagged."""

    errors = password_strength_errors("ALLUPPER123!")
    assert "Password must include at least one lowercase letter." in errors
    assert "Password must include at least one uppercase letter." not in errors


@pytest.mark.django_db
@pytest.mark.unit
def test_authenticate_user_empty_identifier_returns_none():
    """Empty identifier short-circuits to None."""

    assert authenticate_user("", "anypass") is None


@pytest.mark.django_db
@pytest.mark.unit
def test_authenticate_user_nonexistent_user_returns_none():
    """Identifier that resolves to no user returns None."""

    assert authenticate_user("no-such-user-12345", "anypass") is None
