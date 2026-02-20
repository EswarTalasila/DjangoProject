"""SUDO traceability aliases and gap-filling tests."""

from __future__ import annotations

import pytest

from accounts.models import ResearcherProfile, Role, SudoPermission, UserRole
from tests.factories import SudoGrantFactory, UserFactory
from tests.integration import test_accounts_error_paths as account_error_tests
from tests.integration import test_accounts_routes as account_route_tests
from tests.integration import test_admin_api as admin_tests
from tests.integration import test_researcher_api as researcher_tests
from tests.security import test_authz_security as authz_security_tests
from tests.unit.constraints import test_sudo_constraints as sudo_constraint_tests
from tests.unit.services import test_permission_services as permission_tests


@pytest.mark.django_db
class TestSudoTraceability:
    """Backfill FR-03 expected test IDs to concrete test behavior."""

    # --- SUDO CNs ---

    def test_SUDO_CN_05(self):
        """SUDO-CN-05: can_grant_sudo is admin-only."""
        permission_tests.test_can_grant_permissions_cannot_grant_sudo_flag()

    def test_SUDO_CN_06(self, api_client, admin_user):
        """SUDO-CN-06: invalid permission values are rejected."""
        sudo_constraint_tests.TestSudoConstraints().test_SUDO_CN_02_E1()

    def test_SUDO_CN_08(self):
        """SUDO-CN-08: grant updates existing record semantics."""
        permission_tests.test_grant_sudo_to_researcher_create_and_update_paths()

    # --- SUDO-UC-01 Grant sudo ---

    def test_SUDO_UC_01(self, api_client, admin_user):
        """SUDO-UC-01 aggregate grant flow."""
        admin_tests.TestAdminSudo().test_ADMIN_UC_20(api_client, admin_user)

    def test_SUDO_UC_01_ADMIN(self, api_client, admin_user):
        """SUDO-UC-01 admin variant."""
        admin_tests.TestAdminSudo().test_ADMIN_UC_20(api_client, admin_user)

    def test_SUDO_UC_01_RESEARCHER(self, api_client):
        """SUDO-UC-01 researcher variant."""
        researcher_tests.TestResearcherSudoDelegation().test_RESEARCHER_UC_21(api_client)

    def test_SUDO_UC_01_E1(self, api_client, admin_user):
        """SUDO-UC-01-E1 non-researcher grantee rejected."""
        admin_tests.TestAdminSudo().test_ADMIN_UC_20_E1(api_client, admin_user)

    def test_SUDO_UC_01_E2(self, api_client):
        """SUDO-UC-01-E2 escalation attempt rejected."""
        researcher_tests.TestResearcherSudoDelegation().test_RESEARCHER_UC_21_E2(api_client)

    def test_SUDO_UC_01_E3(self, api_client):
        """SUDO-UC-01-E3 researcher cannot set can_grant_sudo."""
        researcher_tests.TestResearcherSudoDelegation().test_RESEARCHER_UC_21_E3(api_client)

    def test_SUDO_UC_01_E4(self, api_client, teacher_user, researcher_user):
        """SUDO-UC-01-E4 unauthorized granter rejected."""
        authz_security_tests.TestAuthorizationSecurity().test_non_admin_cannot_grant_sudo(
            api_client, teacher_user, researcher_user
        )

    def test_SUDO_UC_01_E5(self, api_client, admin_user):
        """Missing required fields are rejected."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/sudo-grants",
            {"permissions": [SudoPermission.CREATE_TEACHER.value]},
            format="json",
        )
        assert response.status_code == 400

    def test_SUDO_UC_01_E6(self, api_client, admin_user):
        """Unknown user_id is rejected."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/sudo-grants",
            {
                "user_id": 999999,
                "permissions": [SudoPermission.CREATE_TEACHER.value],
            },
            format="json",
        )
        assert response.status_code == 404

    def test_SUDO_UC_01_E7(self, api_client, admin_user):
        """Invalid permission value payload is rejected."""
        sudo_constraint_tests.TestSudoConstraints().test_SUDO_CN_02_E1()

    def test_SUDO_UC_01_E8(self, api_client, teacher_user, researcher_user):
        """SUDO-UC-01-E8 role without grant authority rejected."""
        authz_security_tests.TestAuthorizationSecurity().test_non_admin_cannot_grant_sudo(
            api_client, teacher_user, researcher_user
        )

    # --- SUDO-UC-02 Revoke sudo ---

    def test_SUDO_UC_02(self, api_client, admin_user):
        """SUDO-UC-02 aggregate revoke flow."""
        admin_tests.TestAdminSudo().test_ADMIN_UC_21(api_client, admin_user)

    def test_SUDO_UC_02_ADMIN(self, api_client, admin_user):
        """SUDO-UC-02 admin variant."""
        admin_tests.TestAdminSudo().test_ADMIN_UC_21(api_client, admin_user)

    def test_SUDO_UC_02_RESEARCHER(self, api_client):
        """SUDO-UC-02 researcher variant."""
        researcher_tests.TestResearcherSudoDelegation().test_RESEARCHER_UC_22(api_client)

    def test_SUDO_UC_02_E1(self, api_client, admin_user):
        """Unknown grant id is rejected."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete("/api/v1/sudo-grants/999999")
        assert response.status_code == 404

    def test_SUDO_UC_02_E2(self, api_client):
        """SUDO-UC-02-E2 non-owner researcher cannot revoke."""
        researcher_tests.TestResearcherSudoDelegation().test_RESEARCHER_UC_22_E1(api_client)

    def test_SUDO_UC_02_E3(self, api_client, teacher_user):
        """Non-researcher/non-admin cannot revoke grants."""
        grantee = UserFactory()
        UserRole.objects.create(user=grantee, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=grantee)
        grant = SudoGrantFactory(user=grantee)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/sudo-grants/{grant.id}")
        assert response.status_code == 403

    # --- SUDO-UC-03 Create user with sudo scopes ---

    def test_SUDO_UC_03(self, api_client, admin_user):
        """SUDO-UC-03 aggregate create-user flow."""
        account_route_tests.TestAccountRoutes().test_USER_UC_01(api_client, admin_user)

    def test_SUDO_UC_03_ADMIN(self, api_client, admin_user):
        """SUDO-UC-03 admin variant."""
        account_route_tests.TestAccountRoutes().test_USER_UC_01(api_client, admin_user)

    def test_SUDO_UC_03_RESEARCHER(self):
        """SUDO-UC-03 researcher can create teacher with sudo scope."""
        permission_tests.test_can_create_user_researcher_with_create_teacher_sudo()

    def test_SUDO_UC_03_RESEARCHER_CREATE_STUDENT(self):
        """SUDO-UC-03 researcher CREATE_STUDENT scope."""
        permission_tests.test_can_create_user_researcher_with_create_student_sudo()

    def test_SUDO_UC_03_RESEARCHER_CREATE_TEACHER(self):
        """SUDO-UC-03 researcher CREATE_TEACHER scope."""
        permission_tests.test_can_create_user_researcher_with_create_teacher_sudo()

    def test_SUDO_UC_03_TEACHER(self):
        """SUDO-UC-03 teacher role matrix behavior."""
        permission_tests.test_can_create_user_role_matrix()

    def test_SUDO_UC_03_E1(self, api_client, teacher_user):
        """SUDO-UC-03-E1 insufficient permission on create-user."""
        account_route_tests.TestAccountRoutes().test_USER_UC_01_E2(api_client, teacher_user)

    # --- SUDO-UC-04 Edit user with sudo scopes ---

    def test_SUDO_UC_04(self, admin_user):
        """SUDO-UC-04 aggregate edit scope behavior."""
        permission_tests.test_can_edit_and_delete_user_teacher_scope(admin_user)

    def test_SUDO_UC_04_ADMIN(self, api_client, admin_user):
        """SUDO-UC-04 admin variant."""
        account_error_tests.TestAccountErrorPaths().test_edit_user_name_update(
            api_client, admin_user
        )

    def test_SUDO_UC_04_RESEARCHER_EDIT_USER(self, admin_user):
        """SUDO-UC-04 researcher EDIT_USER scope."""
        permission_tests.test_can_edit_user_researcher_with_sudo(admin_user)

    def test_SUDO_UC_04_TEACHER(self, admin_user):
        """SUDO-UC-04 teacher-owned student edit path."""
        permission_tests.test_can_edit_and_delete_user_teacher_scope(admin_user)

    def test_SUDO_UC_04_E1(self, api_client, teacher_user, admin_user):
        """SUDO-UC-04-E1 edit denied outside allowed scope."""
        account_route_tests.TestAccountRoutes().test_USER_UC_03_E2(
            api_client, teacher_user, admin_user
        )

    def test_SUDO_UC_04_E2(self):
        """SUDO-UC-04-E2 staff target edit blocked."""
        permission_tests.test_can_edit_user_staff_target_always_false()

    # --- SUDO-UC-05 Delete user with sudo scopes ---

    def test_SUDO_UC_05(self, admin_user):
        """SUDO-UC-05 aggregate delete scope behavior."""
        permission_tests.test_can_edit_and_delete_user_teacher_scope(admin_user)

    def test_SUDO_UC_05_ADMIN(self):
        """Admin can delete teacher/researcher accounts."""
        admin = permission_tests._mk_user(
            username="fr3-admin-delete", role=Role.RESEARCHER, staff=True
        )
        teacher = permission_tests._mk_user(username="fr3-delete-teacher", role=Role.TEACHER)
        assert permission_tests.can_delete_user(admin, teacher) is True

    def test_SUDO_UC_05_RESEARCHER_DELETE_USER(self):
        """SUDO-UC-05 researcher DELETE_USER scope."""
        permission_tests.test_can_delete_user_researcher_with_sudo()

    def test_SUDO_UC_05_TEACHER(self, admin_user):
        """SUDO-UC-05 teacher-owned student delete path."""
        permission_tests.test_can_edit_and_delete_user_teacher_scope(admin_user)

    def test_SUDO_UC_05_E1(self, admin_user):
        """SUDO-UC-05-E1 insufficient permission on delete."""
        permission_tests.test_can_delete_user_student_requester_returns_false(admin_user)

    # --- SUDO-UC-06 Bulk user creation with sudo scopes ---

    def test_SUDO_UC_06(self, api_client, admin_user):
        """SUDO-UC-06 aggregate bulk create flow."""
        account_route_tests.TestAccountRoutes().test_USER_UC_02_ADMIN(api_client, admin_user)

    def test_SUDO_UC_06_ADMIN(self, api_client, admin_user):
        """SUDO-UC-06 admin variant."""
        account_route_tests.TestAccountRoutes().test_USER_UC_02_ADMIN(api_client, admin_user)

    def test_SUDO_UC_06_E1(self, api_client):
        """SUDO-UC-06-E1 missing BULK_CREATE permission."""
        account_error_tests.TestAccountErrorPaths().test_bulk_create_requires_sudo_for_researcher(
            api_client
        )

    def test_SUDO_UC_06_RESEARCHER_BULK_CREATE(self, api_client):
        """Researcher with BULK_CREATE permission can bulk-create users."""
        admin = UserFactory()
        admin.is_staff = True
        admin.save(update_fields=["is_staff"])
        researcher = UserFactory()
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher)
        SudoGrantFactory(
            user=researcher,
            granted_by=admin,
            permissions=[
                SudoPermission.BULK_CREATE.value,
                SudoPermission.CREATE_TEACHER.value,
            ],
        )

        api_client.force_authenticate(user=researcher)
        response = api_client.post(
            "/api/v1/user-batches",
            [
                {
                    "email": "fr3-bulk-teacher@example.com",
                    "name": "FR3 Bulk Teacher",
                    "role": "ROLE_TEACHER",
                }
            ],
            format="json",
        )
        assert response.status_code == 201
        assert response.json() == 1
