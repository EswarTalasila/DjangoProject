"""Pytest fixtures for backend tests."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, StudentProfile, TeacherProfile, UserRole
from tests.factories import UserFactory


@pytest.fixture
def api_client():
    """Test that api client."""
    return APIClient()


@pytest.fixture
def admin_user():
    """Test that admin user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.ADMIN)
    return user


@pytest.fixture
def teacher_user():
    """Test that teacher user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_user(admin_user):
    """Test that student user."""
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.STUDENT)
    StudentProfile.objects.create(user=user, created_by=admin_user, consent=False)
    return user
