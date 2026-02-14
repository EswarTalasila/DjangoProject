"""Unit tests for UserManager create_user/create_superuser behavior."""

from __future__ import annotations

import pytest

from accounts.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_requires_username_and_name():
    """create_user validates required username and name fields."""

    with pytest.raises(ValueError, match="username is required"):
        User.objects.create_user(username="", name="Name", password="StartPass123!")

    with pytest.raises(ValueError, match="name is required"):
        User.objects.create_user(username="user-a", name="", password="StartPass123!")


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_normalizes_identifiers_and_hashes_password():
    """create_user normalizes username/email and hashes provided password."""

    user = User.objects.create_user(
        username="  CASED@EXAMPLE.COM  ",
        email="  CASED@EXAMPLE.COM  ",
        name="Cased",
        password="StartPass123!",
    )

    assert user.username == "cased@example.com"
    assert user.email == "cased@example.com"
    assert user.check_password("StartPass123!")


@pytest.mark.django_db
@pytest.mark.unit
def test_create_superuser_enforces_staff_and_superuser_flags():
    """create_superuser rejects explicit false values for required admin flags."""

    with pytest.raises(ValueError, match="is_staff"):
        User.objects.create_superuser(
            username="admin-a@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=False,
        )

    with pytest.raises(ValueError, match="is_superuser"):
        User.objects.create_superuser(
            username="admin-b@example.com",
            name="Admin",
            password="StartPass123!",
            is_superuser=False,
        )
