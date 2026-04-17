"""Pytest fixtures for backend tests."""

import pytest

from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import ResearcherProfile, Role, StudentProfile, TeacherProfile, UserRole
from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Clear DRF throttle cache between tests to prevent cross-test rate limiting."""
    cache.clear()


@pytest.fixture
def api_client():
    """Test that api client."""
    return APIClient()


@pytest.fixture
def admin_user():
    """Test that admin user."""
    user = UserFactory()
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def teacher_user():
    """Test that teacher user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def researcher_user():
    """Test that researcher user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.RESEARCHER)
    ResearcherProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_user(admin_user):
    """Test that student user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.STUDENT)
    StudentProfile.objects.create(user=user, created_by=admin_user, consent=False)
    return user


def pytest_itemcollected(item):
    """Show first docstring line alongside test ID in verbose output."""
    doc = getattr(item.function, "__doc__", None)
    if doc:
        first_line = doc.strip().split("\n")[0].strip()
        if first_line:
            item._nodeid = f"{item.nodeid} - {first_line}"
