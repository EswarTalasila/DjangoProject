"""Security tests for OAuth error sanitization and auth error consistency."""

import json
import urllib.error
from unittest.mock import patch

import pytest


@pytest.mark.django_db
@pytest.mark.security
class TestOAuthErrorSanitization:
    """Validate that OAuth error responses never leak internal exception details."""

    def test_oauth_login_url_error_returns_generic_message(self, api_client):
        """URLError details must not appear in OAuth login error response."""
        with patch(
            "accounts.views._google_userinfo",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "fake-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body == {"detail": "Access token verification failed."}
        body_str = json.dumps(body)
        assert "Connection refused" not in body_str
        assert "URLError" not in body_str

    def test_oauth_login_http_error_returns_generic_message(self, api_client):
        """HTTPError details must not appear in OAuth login error response."""
        with patch(
            "accounts.views._google_userinfo",
            side_effect=urllib.error.HTTPError(
                url="https://googleapis.com",
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=None,
            ),
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "fake-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body == {"detail": "Access token verification failed."}
        body_str = json.dumps(body)
        assert "403" not in body_str
        assert "Forbidden" not in body_str

    def test_oauth_login_json_error_returns_generic_message(self, api_client):
        """JSONDecodeError details must not appear in OAuth login error response."""
        with patch(
            "accounts.views._google_userinfo",
            side_effect=json.JSONDecodeError("msg", "doc", 0),
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "fake-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body == {"detail": "Access token verification failed."}
        body_str = json.dumps(body)
        assert "JSONDecodeError" not in body_str

    def test_oauth_login_generic_exception_returns_generic_message(self, api_client):
        """Generic exception secrets must not leak through OAuth login error response."""
        with patch(
            "accounts.views._google_userinfo",
            side_effect=Exception("Internal secret details: api_key=xyz123"),
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "fake-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        body_str = json.dumps(body)
        assert "api_key" not in body_str
        assert "xyz123" not in body_str

    def test_oauth_registration_google_failure_returns_generic_message(
        self, api_client, admin_user
    ):
        """SSL exception details must not appear in OAuth registration error response."""
        with patch(
            "accounts.views._google_userinfo",
            side_effect=Exception("SSL certificate verify failed"),
        ):
            response = api_client.post(
                "/api/v1/registration/accounts",
                {
                    "method": "OAUTH",
                    "code": "FAKE-CODE",
                    "accessToken": "bad-token",
                    "firstName": "Test",
                    "lastName": "User",
                },
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body.get("detail") == "Invalid Google access token."
        body_str = json.dumps(body)
        assert "SSL" not in body_str
        assert "certificate" not in body_str


@pytest.mark.django_db
@pytest.mark.security
class TestAuthErrorConsistency:
    """Validate that auth error messages are consistent to prevent user enumeration."""

    def test_login_invalid_credentials_generic_message(self, api_client, teacher_user):
        """Wrong password must return a generic message, not a specific error."""
        teacher_user.set_password("CorrectPassword123!")
        teacher_user.save(update_fields=["password"])

        response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": teacher_user.username, "password": "WrongPassword999!"},
            format="json",
        )

        assert response.status_code == 401
        body = response.json()
        assert body.get("detail") == "Invalid identifier or password."

    def test_login_nonexistent_user_same_message(self, api_client):
        """Nonexistent user login must return the same message as wrong password (no enumeration)."""
        response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "nobody_at_all@example.com", "password": "AnyPassword123!"},
            format="json",
        )

        assert response.status_code == 401
        body = response.json()
        assert body.get("detail") == "Invalid identifier or password."

    def test_oauth_login_no_account_returns_generic_message(self, api_client):
        """OAuth login for unknown email must not reveal whether email exists in the system."""
        with patch(
            "accounts.views._google_userinfo",
            return_value={"sub": "999", "email": "unknown@example.com"},
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "valid-looking-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body.get("detail") == "Invalid identifier or password."

    def test_oauth_login_missing_google_fields_returns_generic_message(self, api_client):
        """Google userinfo with empty fields must return a generic 401, not internal error."""
        with patch(
            "accounts.views._google_userinfo",
            return_value={"sub": "", "email": ""},
        ):
            response = api_client.post(
                "/api/v1/auth/sessions/oauth",
                {"accessToken": "valid-looking-token"},
                format="json",
            )

        assert response.status_code == 401
        body = response.json()
        assert body.get("detail") == "Access token verification failed."
