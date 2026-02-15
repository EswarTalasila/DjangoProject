"""
Integration tests for ADMIN domain use cases.

Tests for admin-specific operations including sudo management.

UC Ranges:
  01-09: Authentication & Session
  10-19: User Management
  20-29: Sudo / Elevated Permissions
"""

import pytest

from accounts.models import ResearcherProfile, Role, SudoGrant, SudoPermission, UserRole
from tests.factories import SudoGrantFactory, UserFactory


@pytest.mark.django_db
class TestAdminSudo:
    """
    Tests for admin sudo management operations.

    ADMIN-UC-20: Admin grants sudo to researcher
    ADMIN-UC-21: Admin revokes sudo grant
    """

    # =========================================================================
    # ADMIN-UC-20: Admin grants sudo to researcher
    # =========================================================================

    def test_ADMIN_UC_20(self, api_client, admin_user):
        """Admin grants permissions to researcher via POST /sudo-grants."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/sudo-grants",
            {
                "user_id": researcher.id,
                "permissions": [
                    SudoPermission.CREATE_TEACHER.value,
                    SudoPermission.EDIT_USER.value,
                ],
                "can_grant_sudo": True,
            },
            format="json",
        )

        assert response.status_code == 200
        assert "grant_id" in response.data

        # Verify database state
        grant = SudoGrant.objects.get(id=response.data["grant_id"])
        assert grant.user == researcher
        assert set(grant.permissions) == {
            SudoPermission.CREATE_TEACHER.value,
            SudoPermission.EDIT_USER.value,
        }
        assert grant.can_grant_sudo is True
        assert grant.granted_by == admin_user

    def test_ADMIN_UC_20_E1(self, api_client, admin_user):
        """Grantee doesn't have RESEARCHER role - 400."""
        teacher = UserFactory()
        UserRole.objects.create(user=teacher, role=Role.TEACHER)

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/sudo-grants",
            {
                "user_id": teacher.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "must have RESEARCHER role" in response.data["error"]

    # =========================================================================
    # ADMIN-UC-21: Admin revokes sudo grant
    # =========================================================================

    def test_ADMIN_UC_21(self, api_client, admin_user):
        """Admin can revoke any grant via DELETE /sudo-grants/{id}."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)
        grant = SudoGrantFactory(user=researcher)

        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f"/api/v1/sudo-grants/{grant.id}")

        assert response.status_code == 200
        assert "Sudo revoked" in response.data["message"]
        assert not SudoGrant.objects.filter(id=grant.id).exists()
