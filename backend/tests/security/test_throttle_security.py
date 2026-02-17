"""Security-focused DRF throttle enforcement tests."""

import pytest
from django.test import override_settings

TEST_THROTTLE_SETTINGS = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_EXCEPTION_HANDLER": "core.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "anon_auth": "3/minute",
        "anon_burst": "3/minute",
    },
}

THROTTLE_LIMIT = 3


@pytest.mark.django_db
@pytest.mark.security
class TestDRFThrottleEnforcement:
    """Validate DRF-level throttling works correctly on public endpoints."""

    @override_settings(REST_FRAMEWORK=TEST_THROTTLE_SETTINGS)
    def test_login_enforces_burst_throttle(self, api_client):
        """Login endpoint returns 429 after burst throttle limit exceeded."""
        url = "/api/v1/auth/sessions"
        payload = {"identifier": "noone@example.com", "password": "wrong"}

        for _ in range(THROTTLE_LIMIT):
            resp = api_client.post(url, payload, format="json")
            assert resp.status_code != 429, f"Request throttled too early (iteration {_ + 1})"

        throttled = api_client.post(url, payload, format="json")
        assert throttled.status_code == 429
        assert "Retry-After" in throttled

    @override_settings(REST_FRAMEWORK=TEST_THROTTLE_SETTINGS)
    def test_registration_enforces_auth_throttle(self, api_client):
        """Registration endpoint returns 429 after auth throttle limit exceeded."""
        url = "/api/v1/registration/accounts"
        payload = {
            "method": "LOCAL",
            "code": "FAKE-CODE",
            "username": "newuser",
            "password": "TestPass1!",
            "confirmPassword": "TestPass1!",
            "firstName": "Test",
            "lastName": "User",
        }

        for _ in range(THROTTLE_LIMIT):
            resp = api_client.post(url, payload, format="json")
            assert resp.status_code != 429, f"Request throttled too early (iteration {_ + 1})"

        throttled = api_client.post(url, payload, format="json")
        assert throttled.status_code == 429
        assert "Retry-After" in throttled

    @override_settings(REST_FRAMEWORK=TEST_THROTTLE_SETTINGS)
    def test_refresh_enforces_auth_throttle(self, api_client):
        """Token refresh endpoint returns 429 after auth throttle limit exceeded."""
        url = "/api/v1/auth/token-exchanges"
        payload = {"refreshToken": "invalid.refresh.token"}

        for _ in range(THROTTLE_LIMIT):
            resp = api_client.post(url, payload, format="json")
            assert resp.status_code != 429, f"Request throttled too early (iteration {_ + 1})"

        throttled = api_client.post(url, payload, format="json")
        assert throttled.status_code == 429
        assert "Retry-After" in throttled

    @override_settings(REST_FRAMEWORK=TEST_THROTTLE_SETTINGS)
    def test_oauth_login_enforces_burst_throttle(self, api_client):
        """OAuth login endpoint returns 429 after burst throttle limit exceeded."""
        url = "/api/v1/auth/sessions/oauth"
        payload = {"accessToken": "fake-google-access-token"}

        for _ in range(THROTTLE_LIMIT):
            resp = api_client.post(url, payload, format="json")
            assert resp.status_code != 429, f"Request throttled too early (iteration {_ + 1})"

        throttled = api_client.post(url, payload, format="json")
        assert throttled.status_code == 429
        assert "Retry-After" in throttled

    @override_settings(REST_FRAMEWORK=TEST_THROTTLE_SETTINGS)
    def test_throttle_does_not_affect_authenticated_endpoints(self, api_client, teacher_user):
        """Authenticated endpoints are exempt from anonymous throttle limits."""
        api_client.force_authenticate(user=teacher_user)
        url = "/api/v1/users/staff"

        # Make more requests than the anon throttle limit — all should succeed
        for i in range(THROTTLE_LIMIT + 2):
            resp = api_client.get(url)
            assert resp.status_code != 429, (
                f"Authenticated request incorrectly throttled at iteration {i + 1}"
            )
            assert resp.status_code in (200, 400, 403, 404)
