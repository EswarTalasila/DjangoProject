"""Security-focused DRF throttle enforcement tests."""

import pytest

from accounts.services import LOGIN_RATE_LIMIT_ATTEMPTS
from core.throttles import AnonAuthThrottle, AnonBurstThrottle

AUTH_LIMIT = AnonAuthThrottle().num_requests
BURST_LIMIT = AnonBurstThrottle().num_requests


def _assert_throttled(api_client, *, url: str, payload_builder, limit: int) -> None:
    """Assert first ``limit`` requests are not 429 and the next one is."""
    for i in range(limit):
        resp = api_client.post(url, payload_builder(i), format="json")
        assert resp.status_code != 429, f"Request throttled too early (iteration {i + 1})"

    throttled = api_client.post(url, payload_builder(limit), format="json")
    assert throttled.status_code == 429
    assert "Retry-After" in throttled


def _assert_identifier_lockout_has_retry_after(
    api_client, *, url: str, payload_builder, lockout_limit: int
) -> None:
    """Assert manual identifier lockout returns 429 with Retry-After header."""
    for i in range(lockout_limit):
        response = api_client.post(url, payload_builder(i), format="json")
        assert response.status_code != 429, f"Identifier throttled too early at iteration {i + 1}"

    throttled = api_client.post(url, payload_builder(lockout_limit), format="json")
    assert throttled.status_code == 429
    assert throttled.json()["detail"] == "Too many failed attempts. Please try again later."
    retry_after = throttled.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) > 0


def _assert_not_ip_throttled(api_client, *, url: str, payload_builder, attempts: int) -> None:
    """Assert endpoint does not return DRF 429 for varied-identifier attempts."""
    for i in range(attempts):
        response = api_client.post(url, payload_builder(i), format="json")
        assert response.status_code != 429, f"Unexpected IP throttle at iteration {i + 1}"


@pytest.mark.django_db
@pytest.mark.security
class TestDRFThrottleEnforcement:
    """Validate DRF-level throttling works correctly on public endpoints."""

    def test_login_is_not_ip_throttled_for_varied_identifiers(self, api_client):
        """Login should rely on identifier lockout, not shared-IP throttling."""
        _assert_not_ip_throttled(
            api_client,
            url="/api/v1/auth/sessions",
            payload_builder=lambda i: {
                "identifier": f"noone-{i}@example.com",
                "password": "wrong",
            },
            attempts=BURST_LIMIT + 3,
        )

    def test_registration_enforces_auth_throttle(self, api_client):
        """Registration endpoint returns 429 after auth throttle limit exceeded."""
        url = "/api/v1/registration/accounts"
        _assert_throttled(
            api_client,
            url=url,
            payload_builder=lambda i: {
                "method": "LOCAL",
                "code": "FAKE-CODE",
                "password": "TestPass1!",
                "confirmPassword": "TestPass1!",
                "firstName": f"Test{chr(ord('a') + i)}",
                "lastName": "User",
            },
            limit=AUTH_LIMIT,
        )

    def test_refresh_enforces_auth_throttle(self, api_client):
        """Token refresh endpoint returns 429 after auth throttle limit exceeded."""
        url = "/api/v1/auth/token-exchanges"
        _assert_throttled(
            api_client,
            url=url,
            payload_builder=lambda _: {"refreshToken": "invalid.refresh.token"},
            limit=AUTH_LIMIT,
        )

    def test_oauth_login_is_not_ip_throttled(self, api_client, monkeypatch):
        """OAuth login should not use shared-IP throttle."""
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda token: {"sub": f"sub-{token}", "email": f"{token}@example.com"},
        )
        _assert_not_ip_throttled(
            api_client,
            url="/api/v1/auth/sessions/oauth",
            payload_builder=lambda i: {"accessToken": f"fake-google-access-token-{i}"},
            attempts=BURST_LIMIT + 3,
        )

    def test_oauth_identifier_lockout_returns_retry_after_header(self, api_client, monkeypatch):
        """OAuth login enforces per-identifier lockout with Retry-After."""
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _: {"sub": "oauth-lock-sub", "email": "oauth-lock@example.com"},
        )
        _assert_identifier_lockout_has_retry_after(
            api_client,
            url="/api/v1/auth/sessions/oauth",
            payload_builder=lambda i: {"accessToken": f"oauth-lock-token-{i}"},
            lockout_limit=LOGIN_RATE_LIMIT_ATTEMPTS,
        )

    def test_validate_code_enforces_auth_throttle(self, api_client):
        """Registration code validation endpoint is rate-limited."""
        _assert_throttled(
            api_client,
            url="/api/v1/registration/code-validations",
            payload_builder=lambda _: {"code": "NOT-A-REAL-CODE"},
            limit=AUTH_LIMIT,
        )

    def test_password_reset_code_issuance_requires_auth(self, api_client):
        """Issuer-driven reset-code generation is not available to anonymous users."""
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": 1},
            format="json",
        )
        assert response.status_code == 401

    def test_reset_code_validation_enforces_burst_throttle(self, api_client):
        """Reset-code verification endpoint is rate-limited."""
        _assert_throttled(
            api_client,
            url="/api/v1/auth/reset-code-validations",
            payload_builder=lambda _: {
                "identifier": "missing@example.com",
                "resetCode": "RESET-FAKE",
            },
            limit=BURST_LIMIT,
        )

    def test_password_reset_completion_enforces_burst_throttle(self, api_client):
        """Password-reset completion endpoint is rate-limited."""
        _assert_throttled(
            api_client,
            url="/api/v1/auth/password-resets",
            payload_builder=lambda i: {
                "identifier": f"missing-complete-{i}@example.com",
                "resetCode": "RESET-FAKE",
                "newPassword": "StrongPass1!",
                "confirmPassword": "StrongPass1!",
            },
            limit=BURST_LIMIT,
        )

    def test_login_identifier_lockout_returns_retry_after_header(self, api_client):
        """Identifier lockout on login returns 429 with Retry-After header."""
        _assert_identifier_lockout_has_retry_after(
            api_client,
            url="/api/v1/auth/sessions",
            payload_builder=lambda _: {"identifier": "locked@example.com", "password": "wrong"},
            lockout_limit=LOGIN_RATE_LIMIT_ATTEMPTS,
        )

    def test_throttle_does_not_affect_authenticated_endpoints(self, api_client, teacher_user):
        """Authenticated endpoints are exempt from anonymous throttle limits."""
        api_client.force_authenticate(user=teacher_user)
        url = "/api/v1/users/staff"

        # Make more requests than the burst throttle limit — all should succeed.
        for i in range(BURST_LIMIT + 2):
            resp = api_client.get(url)
            assert resp.status_code != 429, (
                f"Authenticated request incorrectly throttled at iteration {i + 1}"
            )
            assert resp.status_code in (200, 400, 403, 404)
