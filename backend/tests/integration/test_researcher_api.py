"""
Integration tests for RESEARCHER domain use cases.

Tests for researcher-specific operations including sudo permission checks and delegation.

UC Ranges:
  01-09: Authentication & Session
  10-19: User Management
  20-29: Sudo / Elevated Permissions
"""

import pytest

from accounts.models import ResearcherProfile, Role, SudoGrant, SudoPermission, UserRole
from core.permissions import has_sudo_permission
from tests.factories import SudoGrantFactory, UserFactory


@pytest.mark.django_db
class TestResearcherSudoPermissions:
    """
    Tests for researcher sudo permission checking.

    RESEARCHER-UC-20: Check sudo permission (has_sudo_permission helper)
    """

    # =========================================================================
    # RESEARCHER-UC-20: Check sudo permission
    # =========================================================================

    @pytest.mark.parametrize(
        "permission",
        [
            SudoPermission.CREATE_TEACHER.value,
            SudoPermission.CREATE_STUDENT.value,
            SudoPermission.EDIT_USER.value,
            SudoPermission.DELETE_USER.value,
            SudoPermission.BULK_CREATE.value,
            SudoPermission.RESET_PASSWORD.value,
            SudoPermission.GRANT_SUDO.value,
        ],
    )
    def test_RESEARCHER_UC_20(self, permission):
        """Researcher with specific permission - has_sudo_permission returns True."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        SudoGrantFactory(user=user, permissions=[permission])

        assert has_sudo_permission(user, permission) is True

    def test_RESEARCHER_UC_20_E1(self):
        """Empty permissions list - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        SudoGrantFactory(user=user, permissions=[])

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_RESEARCHER_UC_20_E1a(self):
        """Has wrong permission - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        SudoGrantFactory(user=user, permissions=[SudoPermission.CREATE_TEACHER.value])

        assert has_sudo_permission(user, SudoPermission.EDIT_USER.value) is False

    def test_RESEARCHER_UC_20_E2(self):
        """No SudoGrant record - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_RESEARCHER_UC_20_E3(self):
        """Teacher role attempts sudo action - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.TEACHER)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_RESEARCHER_UC_20_E4(self):
        """Student role attempts sudo action - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.STUDENT)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False


@pytest.mark.django_db
class TestResearcherSudoDelegation:
    """
    Tests for researcher sudo delegation operations.

    RESEARCHER-UC-21: Delegate sudo to another researcher
    RESEARCHER-UC-22: Revoke grants researcher created
    """

    # =========================================================================
    # RESEARCHER-UC-21: Delegate sudo to another researcher
    # =========================================================================

    def test_RESEARCHER_UC_21(self, api_client):
        """Sudoed researcher with can_grant_sudo grants subset of own permissions."""
        # Create researcher1 with can_grant_sudo and specific permissions
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        SudoGrantFactory(
            user=researcher1,
            permissions=[
                SudoPermission.CREATE_TEACHER.value,
                SudoPermission.CREATE_STUDENT.value,
            ],
            can_grant_sudo=True,
        )

        # Create researcher2 (grantee)
        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        # Researcher1 grants subset to researcher2
        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
                "can_grant_sudo": False,
            },
            format="json",
        )

        assert response.status_code == 200
        assert "grant_id" in response.data

        # Verify database state
        grant = SudoGrant.objects.get(id=response.data["grant_id"])
        assert grant.user == researcher2
        assert grant.permissions == [SudoPermission.CREATE_TEACHER.value]
        assert grant.can_grant_sudo is False
        assert grant.granted_by == researcher1

    def test_RESEARCHER_UC_21_E1(self, api_client):
        """Researcher without can_grant_sudo tries to grant - 403."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=False,  # No grant ability
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )

        assert response.status_code == 403
        assert "can_grant_sudo=False" in response.data["error"]

    def test_RESEARCHER_UC_21_E2(self, api_client):
        """Escalation attempt - researcher tries to grant permission they don't hold - 403."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=True,
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.EDIT_USER.value],  # Don't have this
            },
            format="json",
        )

        assert response.status_code == 403
        assert "Cannot grant permissions you don't hold" in response.data["error"]
        assert SudoPermission.EDIT_USER.value in response.data["error"]

    def test_RESEARCHER_UC_21_E3(self, api_client):
        """Researcher tries to set can_grant_sudo=True - 403 (admin only)."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=True,
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
                "can_grant_sudo": True,  # Attempting admin-only flag
            },
            format="json",
        )

        assert response.status_code == 403
        assert "Only admins can set can_grant_sudo=True" in response.data["error"]

    def test_RESEARCHER_UC_21_E4(self, api_client):
        """Researcher tries to delegate to non-researcher - 400."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=True,
        )

        teacher = UserFactory()
        UserRole.objects.create(user=teacher, role=Role.TEACHER)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": teacher.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "must have RESEARCHER role" in response.data["error"]

    def test_RESEARCHER_UC_21_E5(self, api_client, admin_user):
        """Grantee already has SudoGrant - updates existing."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)

        # Create initial grant
        api_client.force_authenticate(user=admin_user)
        response1 = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )
        assert response1.status_code == 200

        # Try to grant again (should update, not error)
        response2 = api_client.post(
            "/api/v1/users/sudo",
            {
                "user_id": researcher.id,
                "permissions": [SudoPermission.EDIT_USER.value],
            },
            format="json",
        )

        # Service updates existing grant
        assert response2.status_code == 200
        researcher.refresh_from_db()
        assert researcher.sudo_grant.permissions == [SudoPermission.EDIT_USER.value]

    # =========================================================================
    # RESEARCHER-UC-22: Revoke grants researcher created
    # =========================================================================

    def test_RESEARCHER_UC_22(self, api_client):
        """Researcher can revoke grants they created."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        grant = SudoGrantFactory(user=researcher2, granted_by=researcher1)

        api_client.force_authenticate(user=researcher1)
        response = api_client.delete(f"/api/v1/users/sudo/{grant.id}")

        assert response.status_code == 200
        assert "Sudo revoked" in response.data["message"]
        assert not SudoGrant.objects.filter(id=grant.id).exists()

    def test_RESEARCHER_UC_22_E1(self, api_client):
        """Researcher cannot revoke grants they didn't create - 403."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        researcher3 = UserFactory()
        UserRole.objects.create(user=researcher3, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher3)

        # Researcher1 grants to researcher3
        grant = SudoGrantFactory(user=researcher3, granted_by=researcher1)

        # Researcher2 (not the granter) tries to revoke
        api_client.force_authenticate(user=researcher2)
        response = api_client.delete(f"/api/v1/users/sudo/{grant.id}")

        assert response.status_code == 403
        assert "You can only revoke grants you created" in response.data["error"]
        assert SudoGrant.objects.filter(id=grant.id).exists()  # Still exists
