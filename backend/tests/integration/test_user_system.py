"""FR-04 black-box system tests for user management endpoints."""

from __future__ import annotations

import pytest

from accounts.models import Role, User, UserRole


@pytest.mark.integration
@pytest.mark.django_db
def test_ST_USER_UC_01_create_role_matrix(api_client, admin_user, teacher_user, researcher_user):
    """ST-USER-UC-01: create-user role matrix for admin/teacher/researcher."""
    api_client.force_authenticate(user=admin_user)
    admin_create = api_client.post(
        "/api/v1/users",
        {
            "name": "System Teacher",
            "role": "TEACHER",
            "email": "system-teacher@example.com",
            "password": "StartPass123!",
        },
        format="json",
    )
    assert admin_create.status_code == 201

    api_client.force_authenticate(user=teacher_user)
    teacher_create = api_client.post(
        "/api/v1/users",
        {
            "name": "System Student",
            "role": "STUDENT",
            "password": "StartPass123!",
        },
        format="json",
    )
    assert teacher_create.status_code == 201

    api_client.force_authenticate(user=researcher_user)
    researcher_create = api_client.post(
        "/api/v1/users",
        {
            "name": "Blocked Teacher",
            "role": "TEACHER",
            "email": "blocked-teacher@example.com",
            "password": "StartPass123!",
        },
        format="json",
    )
    assert researcher_create.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
def test_ST_USER_UC_02_edit_username_immutable(api_client, admin_user, teacher_user):
    """ST-USER-UC-02: edit enforces immutable usernames."""
    api_client.force_authenticate(user=admin_user)
    response = api_client.patch(
        f"/api/v1/users/{teacher_user.id}",
        {"username": "should-not-change"},
        format="json",
    )
    assert response.status_code == 400
    assert "immutable" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.django_db
def test_ST_USER_UC_03_delete_scope_and_not_found(api_client, admin_user, teacher_user):
    """ST-USER-UC-03: delete hides out-of-scope targets and handles missing IDs."""
    api_client.force_authenticate(user=teacher_user)
    out_of_scope = api_client.delete(f"/api/v1/users/{admin_user.id}")
    assert out_of_scope.status_code == 404
    assert out_of_scope.json()["detail"] == "User not found"

    api_client.force_authenticate(user=admin_user)
    missing = api_client.delete("/api/v1/users/99999999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "User not found"


@pytest.mark.integration
@pytest.mark.django_db
def test_ST_USER_UC_04_staff_list_gate_and_scope(api_client, admin_user, teacher_user):
    """ST-USER-UC-04: staff list gate and role scope are enforced."""
    researcher = User.objects.create_user(
        username="system-researcher",
        email="system-researcher@example.com",
        name="System Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)

    api_client.force_authenticate(user=admin_user)
    admin_response = api_client.get("/api/v1/users/staff")
    assert admin_response.status_code == 200
    for entry in admin_response.json()["results"]:
        assert entry["role"] in (Role.TEACHER, Role.RESEARCHER)

    api_client.force_authenticate(user=teacher_user)
    teacher_response = api_client.get("/api/v1/users/staff")
    assert teacher_response.status_code == 403
