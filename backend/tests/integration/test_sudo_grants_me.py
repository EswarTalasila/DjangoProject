"""Integration tests for GET /api/v1/sudo-grants/me capability endpoint."""

from __future__ import annotations

import pytest

from accounts.models import SudoGrant, SudoPermission


@pytest.mark.django_db
class TestSudoGrantsMe:
    """Capability lookup for current authenticated user."""

    def test_admin_receives_full_capability(self, api_client, admin_user):
        """Admin should always resolve as full capability in the response."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.get("/api/v1/sudo-grants/me")

        assert response.status_code == 200
        body = response.json()
        assert body["isStaff"] is True
        assert body["hasSudo"] is True
        assert body["canGrantSudo"] is True
        assert SudoPermission.CREATE_RESEARCHER_CODES.value in body["permissions"]

    def test_researcher_without_grant_gets_empty_permissions(self, api_client, researcher_user):
        """Researcher without grant should return empty permissions."""
        api_client.force_authenticate(user=researcher_user)

        response = api_client.get("/api/v1/sudo-grants/me")

        assert response.status_code == 200
        assert response.json() == {
            "hasSudo": False,
            "canGrantSudo": False,
            "permissions": [],
            "isStaff": False,
        }

    def test_researcher_with_grant_receives_permissions(self, api_client, admin_user, researcher_user):
        """Researcher with grant should see current sudo permissions for UI gating."""
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            can_grant_sudo=False,
            permissions=[SudoPermission.CREATE_RESEARCHER_CODES.value],
        )
        api_client.force_authenticate(user=researcher_user)

        response = api_client.get("/api/v1/sudo-grants/me")

        assert response.status_code == 200
        body = response.json()
        assert body["isStaff"] is False
        assert body["hasSudo"] is True
        assert body["canGrantSudo"] is False
        assert body["permissions"] == [SudoPermission.CREATE_RESEARCHER_CODES.value]
