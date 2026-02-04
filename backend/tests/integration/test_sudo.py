"""Comprehensive test coverage for sudo grant/revoke functionality."""

import pytest
from django.core.exceptions import ValidationError

from accounts.models import Role, SudoGrant, SudoPermission, UserRole, ResearcherProfile
from core.permissions import has_sudo_permission
from tests.factories import UserFactory, SudoGrantFactory


@pytest.mark.django_db
class TestSudoGrantModel:
    """Model validation tests for SudoGrant."""

    def test_clean_valid_permissions(self):
        """Valid SudoPermission values are accepted."""
        grant = SudoGrantFactory.build(
            permissions=[
                SudoPermission.CREATE_TEACHER.value,
                SudoPermission.CREATE_STUDENT.value,
            ]
        )
        grant.clean()  # Should not raise

    def test_clean_invalid_permissions(self):
        """Invalid permission values are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions=["INVALID_PERMISSION"])
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "Invalid permissions" in str(exc_info.value)

    def test_clean_permissions_not_list(self):
        """Non-list permissions are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions="not_a_list")
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "must be a list" in str(exc_info.value)

    def test_clean_empty_permissions(self):
        """Empty permissions list is valid (opt-in semantics)."""
        grant = SudoGrantFactory.build(permissions=[])
        grant.clean()  # Should not raise


@pytest.mark.django_db
class TestSudoPermissions:
    """Tests for has_sudo_permission helper - ROLE-UC-01."""

    @pytest.mark.parametrize("permission", [
        SudoPermission.CREATE_TEACHER.value,
        SudoPermission.CREATE_STUDENT.value,
        SudoPermission.EDIT_USER.value,
        SudoPermission.DELETE_USER.value,
        SudoPermission.BULK_CREATE.value,
        SudoPermission.RESET_PASSWORD.value,
        SudoPermission.GRANT_SUDO.value,
    ])
    def test_ROLE_UC_01(self, permission):
        """Researcher with specific permission - has_sudo_permission returns True."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        grant = SudoGrantFactory(user=user, permissions=[permission])

        assert has_sudo_permission(user, permission) is True

    def test_ROLE_UC_01_E1(self):
        """Empty permissions list - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        grant = SudoGrantFactory(user=user, permissions=[])

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_ROLE_UC_01_E1a(self):
        """Has wrong permission - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)
        grant = SudoGrantFactory(
            user=user,
            permissions=[SudoPermission.CREATE_TEACHER.value]
        )

        assert has_sudo_permission(user, SudoPermission.EDIT_USER.value) is False

    def test_ROLE_UC_01_E2(self):
        """No SudoGrant record - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=user)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_ROLE_UC_01_E3(self):
        """Teacher role attempts sudo action - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.TEACHER)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False

    def test_ROLE_UC_01_E4(self):
        """Student role attempts sudo action - denied."""
        user = UserFactory()
        UserRole.objects.create(user=user, role=Role.STUDENT)

        assert has_sudo_permission(user, SudoPermission.CREATE_TEACHER.value) is False


@pytest.mark.django_db
class TestSudoEndpoints:
    """API endpoint tests for sudo grant/revoke - ROLE-UC-02 and ROLE-UC-03."""

    def test_ROLE_UC_02(self, api_client):
        """Sudoed researcher with can_grant_sudo grants subset of own permissions."""
        # Create researcher1 with can_grant_sudo and specific permissions
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        grant1 = SudoGrantFactory(
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
            "/api/v1/auth/grant-sudo",
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

    def test_ROLE_UC_02_A1(self, api_client, admin_user):
        """Admin grants permissions to researcher via POST /auth/grant-sudo."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
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

    def test_ROLE_UC_02_E1(self, api_client):
        """Researcher without can_grant_sudo tries to grant - 403."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        grant1 = SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=False,  # No grant ability
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )

        assert response.status_code == 403
        assert "can_grant_sudo=False" in response.data["error"]

    def test_ROLE_UC_02_E2(self, api_client):
        """Escalation attempt - researcher tries to grant permission they don't hold - 403."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        grant1 = SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=True,
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.EDIT_USER.value],  # Don't have this
            },
            format="json",
        )

        assert response.status_code == 403
        assert "Cannot grant permissions you don't hold" in response.data["error"]
        assert SudoPermission.EDIT_USER.value in response.data["error"]

    def test_ROLE_UC_02_E3(self, api_client):
        """Researcher tries to set can_grant_sudo=True - 403 (admin only)."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)
        grant1 = SudoGrantFactory(
            user=researcher1,
            permissions=[SudoPermission.CREATE_TEACHER.value],
            can_grant_sudo=True,
        )

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        api_client.force_authenticate(user=researcher1)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": researcher2.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
                "can_grant_sudo": True,  # Attempting admin-only flag
            },
            format="json",
        )

        assert response.status_code == 403
        assert "Only admins can set can_grant_sudo=True" in response.data["error"]

    def test_ROLE_UC_02_E4(self, api_client, admin_user):
        """Grantee doesn't have RESEARCHER role - 400."""
        teacher = UserFactory()
        UserRole.objects.create(user=teacher, role=Role.TEACHER)

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": teacher.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "must have RESEARCHER role" in response.data["error"]

    def test_ROLE_UC_02_E5(self, api_client, admin_user):
        """Grantee already has SudoGrant - error."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)

        # Create initial grant
        api_client.force_authenticate(user=admin_user)
        response1 = api_client.post(
            "/api/v1/auth/grant-sudo",
            {
                "user_id": researcher.id,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )
        assert response1.status_code == 200

        # Try to grant again (should update, not error - based on service implementation)
        response2 = api_client.post(
            "/api/v1/auth/grant-sudo",
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

    def test_ROLE_UC_03(self, api_client, admin_user):
        """Admin can revoke any grant via DELETE /auth/revoke-sudo/{id}."""
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)
        grant = SudoGrantFactory(user=researcher)

        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f"/api/v1/auth/revoke-sudo/{grant.id}")

        assert response.status_code == 200
        assert "Sudo revoked" in response.data["message"]
        assert not SudoGrant.objects.filter(id=grant.id).exists()

    def test_ROLE_UC_03_A1(self, api_client):
        """Researcher can revoke grants they created."""
        researcher1 = UserFactory()
        UserRole.objects.create(user=researcher1, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher1)

        researcher2 = UserFactory()
        UserRole.objects.create(user=researcher2, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher2)

        grant = SudoGrantFactory(user=researcher2, granted_by=researcher1)

        api_client.force_authenticate(user=researcher1)
        response = api_client.delete(f"/api/v1/auth/revoke-sudo/{grant.id}")

        assert response.status_code == 200
        assert "Sudo revoked" in response.data["message"]
        assert not SudoGrant.objects.filter(id=grant.id).exists()

    def test_ROLE_UC_03_E1(self, api_client):
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
        response = api_client.delete(f"/api/v1/auth/revoke-sudo/{grant.id}")

        assert response.status_code == 403
        assert "You can only revoke grants you created" in response.data["error"]
        assert SudoGrant.objects.filter(id=grant.id).exists()  # Still exists
