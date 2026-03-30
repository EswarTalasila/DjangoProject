"""Unit tests for UserOutputSerializer.get_role() using primary_role() logic.

The serializer must return the highest-priority role matching the same
ordering as core.permissions.primary_role():
    ADMIN (is_staff) > RESEARCHER > TEACHER > STUDENT (fallback)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from accounts.models import Role
from accounts.serializers import UserOutputSerializer
from core.permissions import primary_role

pytestmark = pytest.mark.unit


def _mock_user(roles=None, is_staff=False):
    """Build a mock user with a roles queryset and is_staff flag."""
    user = MagicMock()
    user.id = 1
    user.name = "Test User"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_staff = is_staff
    user.is_authenticated = True

    qs = MagicMock()
    role_objects = [SimpleNamespace(role=r) for r in (roles or [])]
    qs.all.return_value = role_objects
    qs.values_list.return_value = [r for r in (roles or [])]
    user.roles = qs

    # Support primary_role()'s _role_set caching
    user._cached_role_set = None

    return user


class TestUserOutputSerializerPrimaryRole:
    """get_role() must agree with primary_role() from core.permissions."""

    def test_single_teacher_role(self):
        """User with only TEACHER role serializes as TEACHER."""
        user = _mock_user(roles=[Role.TEACHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "TEACHER"

    def test_single_student_role(self):
        """User with only STUDENT role serializes as STUDENT."""
        user = _mock_user(roles=[Role.STUDENT])
        data = UserOutputSerializer(user).data
        assert data["role"] == "STUDENT"

    def test_single_researcher_role(self):
        """User with only RESEARCHER role serializes as RESEARCHER."""
        user = _mock_user(roles=[Role.RESEARCHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "RESEARCHER"

    def test_multiple_roles_returns_highest_priority(self):
        """User with TEACHER+RESEARCHER returns RESEARCHER (highest)."""
        user = _mock_user(roles=[Role.TEACHER, Role.RESEARCHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "RESEARCHER"

    def test_multiple_roles_teacher_student_returns_teacher(self):
        """User with STUDENT+TEACHER returns TEACHER (higher priority)."""
        user = _mock_user(roles=[Role.STUDENT, Role.TEACHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "TEACHER"

    def test_all_three_roles_returns_researcher(self):
        """User with all three roles returns RESEARCHER (highest)."""
        user = _mock_user(roles=[Role.STUDENT, Role.TEACHER, Role.RESEARCHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "RESEARCHER"

    def test_no_roles_falls_back_to_student(self):
        """User with no roles falls back to STUDENT."""
        user = _mock_user(roles=[])
        data = UserOutputSerializer(user).data
        assert data["role"] == "STUDENT"

    def test_admin_user_returns_admin(self):
        """Staff user serializes role as ADMIN."""
        user = _mock_user(roles=[Role.RESEARCHER], is_staff=True)
        data = UserOutputSerializer(user).data
        assert data["role"] == "ADMIN"

    def test_matches_primary_role_function(self):
        """Serializer output matches primary_role() for multi-role user."""
        user = _mock_user(roles=[Role.STUDENT, Role.RESEARCHER])
        serialized_role = UserOutputSerializer(user).data["role"]
        expected = primary_role(user)
        assert serialized_role == expected
