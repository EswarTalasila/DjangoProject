"""Integration tests for auth errors."""

import pytest

from accounts.models import OAuthAccount, OAuthProvider, Role, User, UserRole

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestAuthErrors:
    def test_AUTH_UC_01_E1(self, api_client):
        """AUTH-UC-01-E1: invalid credentials return 401 without enumeration."""
        response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "missing@example.com", "password": "bad"},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid identifier or password."

    def test_AUTH_UC_02_E1(self, api_client):
        """AUTH-UC-02-E1: OAuth login requires provider access token."""
        response = api_client.post("/api/v1/auth/sessions/oauth", {}, format="json")
        assert response.status_code == 400
        assert "accessToken" in response.json()

    def test_AUTH_UC_07_E1(self, api_client, teacher_user):
        """AUTH-UC-07-E1: issuer denied when target role is outside scope."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": teacher_user.id},
            format="json",
        )
        assert response.status_code == 403

    def test_AUTH_CN_13(self, api_client, monkeypatch):
        """AUTH-CN-13: student accounts cannot use OAuth login flow."""
        student = User.objects.create_user(
            username="studentoauth",
            name="Student OAuth",
            password="StartPass123!",
        )
        UserRole.objects.create(user=student, role=Role.STUDENT)
        OAuthAccount.objects.create(
            user=student,
            provider=OAuthProvider.GOOGLE,
            subject="google-subject-1",
            email="studentoauth@example.com",
        )
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {"sub": "google-subject-1", "email": "studentoauth@example.com"},
        )

        response = api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "valid-token"},
            format="json",
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Google OAuth is not supported for student accounts."
