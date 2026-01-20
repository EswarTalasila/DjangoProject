"""Integration tests for auth errors."""

import pytest


@pytest.mark.django_db
class TestAuthErrors:
    def test_login_invalid_credentials_returns_401(self, api_client):
        """Test that login invalid credentials returns 401."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"username": "missing@example.com", "password": "bad"},
            format="json",
        )
        assert response.status_code == 401
        assert b"Invalid username or password" in response.content

    def test_google_login_requires_access_token(self, api_client):
        """Test that google login requires access token."""
        response = api_client.post("/api/v1/auth/google", {}, format="json")
        assert response.status_code == 400
        assert response.json().get("error") == "accessToken is required"

    def test_check_email_missing_returns_404(self, api_client):
        """Test that check email missing returns 404."""
        response = api_client.post("/api/v1/auth/check-email", {"email": "none@example.com"})
        assert response.status_code == 404
        payload = response.json()
        assert payload["exists"] is False
        assert payload["needsPassword"] is False
