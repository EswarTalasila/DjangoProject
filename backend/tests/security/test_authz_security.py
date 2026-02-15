"""Security-focused authorization tests."""

import pytest

from accounts.models import SudoPermission


@pytest.mark.django_db
@pytest.mark.security
class TestAuthorizationSecurity:
    """Validate role and authentication guards on sensitive auth endpoints."""

    def test_create_user_requires_authentication(self, api_client):
        """Anonymous clients cannot create teacher/researcher accounts."""
        response = api_client.post(
            "/api/v1/auth/createuser",
            {
                "username": "blocked@example.com",
                "password": "testpass123",
                "name": "Blocked User",
                "role": "ROLE_TEACHER",
            },
            format="json",
        )

        assert response.status_code == 401

    def test_non_admin_cannot_grant_sudo(self, api_client, teacher_user, researcher_user):
        """Teacher role cannot assign elevated sudo grants."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": researcher_user.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
                "can_grant_sudo": True,
            },
            format="json",
        )

        assert response.status_code == 403
