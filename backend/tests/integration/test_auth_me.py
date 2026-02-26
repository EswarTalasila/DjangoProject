"""Integration tests for authenticated profile endpoint."""

import pytest


@pytest.mark.integration
@pytest.mark.django_db
def test_auth_me_requires_authentication(api_client):
    """GET /auth/me returns 401 without access token."""
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.django_db
def test_auth_me_returns_teacher_profile(api_client, teacher_user):
    """GET /auth/me returns normalized role payload for authenticated teacher."""
    api_client.force_authenticate(user=teacher_user)

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(teacher_user.id)
    assert body["username"] == teacher_user.username
    assert body["role"] == "TEACHER"
    assert body["isStaff"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_auth_me_returns_student_profile(api_client, student_user):
    """GET /auth/me returns STUDENT role for student users."""
    api_client.force_authenticate(user=student_user)

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(student_user.id)
    assert body["username"] == student_user.username
    assert body["role"] == "STUDENT"
    assert body["isStaff"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_auth_me_returns_researcher_profile(api_client, researcher_user):
    """GET /auth/me returns RESEARCHER role for researcher users."""
    api_client.force_authenticate(user=researcher_user)

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(researcher_user.id)
    assert body["username"] == researcher_user.username
    assert body["role"] == "RESEARCHER"
    assert body["isStaff"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_auth_me_returns_admin_role(api_client, admin_user):
    """GET /auth/me returns ADMIN role for staff users."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "ADMIN"
    assert body["isStaff"] is True
