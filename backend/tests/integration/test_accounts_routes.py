"""Integration tests for accounts routes."""

import pytest

from accounts.models import Role, User, UserRole


@pytest.mark.django_db
class TestAccountRoutes:
    def test_register_creates_student_only(self, api_client):
        """Test that register creates student only, ignoring any role parameter."""
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "username": "student@example.com",
                "password": "testpass123",
                "name": "Student Name",
                "role": "ROLE_TEACHER",  # Should be ignored, always creates student
            },
            format="json",
        )
        assert response.status_code == 200
        user = User.objects.get(username="student@example.com")
        role = user.roles.values_list("role", flat=True).first()
        assert role == Role.STUDENT

    def test_login_success_returns_token(self, api_client):
        """Test that login success returns token."""
        api_client.post(
            "/api/v1/auth/register",
            {
                "username": "login@example.com",
                "password": "testpass123",
                "name": "Login User",
            },
            format="json",
        )
        response = api_client.post(
            "/api/v1/auth/login",
            {"username": "login@example.com", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert "accessToken" in payload
        assert payload["role"] == Role.STUDENT

    def test_check_email_existing_user(self, api_client, admin_user):
        """Test that check email existing user."""
        User.objects.create_user(username="check@example.com", name="Check User", password=None)
        response = api_client.post("/api/v1/auth/check-email", {"email": "check@example.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["needsPassword"] is True

    def test_admin_can_create_teacher(self, api_client, admin_user):
        """Test that admin can create teacher."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "username": "teacher@example.com",
            "password": "testpass123",
            "name": "Teacher Name",
            "role": "ROLE_TEACHER",
        }
        response = api_client.post("/api/v1/auth/createuser", payload, format="json")
        assert response.status_code == 200
        created = User.objects.get(username="teacher@example.com")
        assert created.teacher_profile is not None

    def test_teacher_cannot_create_researcher(self, api_client, teacher_user):
        """Test that teacher cannot create researcher (only admin can)."""
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "username": "researcher@example.com",
            "password": "testpass123",
            "name": "Researcher",
            "role": "ROLE_RESEARCHER",
        }
        response = api_client.post("/api/v1/auth/createuser", payload, format="json")
        assert response.status_code == 403

    def test_edit_user_requires_authorization(self, api_client, teacher_user, admin_user):
        """Test that teacher cannot edit admin user."""
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "name": "Admin Updated",
            "username": admin_user.username,
        }
        response = api_client.post(f"/api/v1/auth/edituser/{admin_user.id}", payload, format="json")
        assert response.status_code == 403

    def test_list_staff_returns_teachers_and_researchers(
        self, api_client, admin_user, teacher_user
    ):
        """Test that list staff returns users with TEACHER or RESEARCHER roles."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/v1/auth/staff")
        assert response.status_code == 200
        # Endpoint returns TEACHER and RESEARCHER roles only (not staff-only admins)
        usernames = {entry["username"] for entry in response.json()}
        assert teacher_user.username in usernames

    def test_bulk_create_users_returns_count(self, api_client, admin_user):
        """Test that bulk create users returns count."""
        api_client.force_authenticate(user=admin_user)
        payload = [
            {"username": "bulk1@example.com", "name": "Bulk One", "role": "ROLE_TEACHER"},
            {"username": "bulk2@example.com", "name": "Bulk Two", "role": "ROLE_TEACHER"},
        ]
        response = api_client.post("/api/v1/auth/create/bulk", payload, format="json")
        assert response.status_code == 200
        assert response.json() == 2

    def test_reset_password_requires_permission(self, api_client, teacher_user, admin_user):
        """Test that reset password requires permission."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.put(f"/api/v1/auth/reset/{admin_user.id}")
        assert response.status_code == 403

    def test_delete_user_admin_only(self, api_client, admin_user, teacher_user):
        """Test that delete user admin only."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/auth/user/{admin_user.username}")
        assert response.status_code == 403

    def test_create_user_sets_single_role(self, api_client, admin_user):
        """Test that create user sets single role."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "username": "single@example.com",
            "password": "testpass123",
            "name": "Single Role",
            "role": "ROLE_TEACHER",
        }
        response = api_client.post("/api/v1/auth/createuser", payload, format="json")
        assert response.status_code == 200
        roles = UserRole.objects.filter(user__username="single@example.com")
        assert roles.count() == 1
        assert roles.first().role == Role.TEACHER

    def test_set_password_updates_user(self, api_client, admin_user):
        """Test that set password updates user."""
        user = User.objects.create_user(
            username="newpass@example.com", name="New Pass", password=None
        )
        assert user.password is None
        response = api_client.post(
            f"/api/v1/auth/users/{user.id}/set-password",
            "updatedpass",
            content_type="text/plain",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.password is not None
