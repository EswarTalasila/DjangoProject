"""Integration tests for admin login restrictions."""

import pytest

from accounts.models import OAuthAccount, OAuthProvider


@pytest.mark.integration
@pytest.mark.django_db
def test_admin_password_login_is_blocked(api_client, admin_user):
    """POST /auth/sessions rejects admin credentials for non-dashboard login."""
    admin_user.set_password("change-me")
    admin_user.save(update_fields=["password"])

    response = api_client.post(
        "/api/v1/auth/sessions",
        {"identifier": admin_user.username, "password": "change-me"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin accounts must use Django admin."


@pytest.mark.integration
@pytest.mark.django_db
def test_admin_oauth_login_blocked_existing_account(api_client, admin_user, monkeypatch):
    """POST /auth/sessions/oauth rejects admin with existing OAuth account."""
    OAuthAccount.objects.create(
        user=admin_user,
        provider=OAuthProvider.GOOGLE,
        subject="admin-google-sub",
        email=admin_user.email,
    )
    monkeypatch.setattr(
        "accounts.views._google_userinfo",
        lambda _token: {"sub": "admin-google-sub", "email": admin_user.email},
    )

    response = api_client.post(
        "/api/v1/auth/sessions/oauth",
        {"accessToken": "fake-token"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin accounts must use Django admin."


@pytest.mark.integration
@pytest.mark.django_db
def test_admin_oauth_login_blocked_email_link(api_client, admin_user, monkeypatch):
    """POST /auth/sessions/oauth rejects admin on first-time OAuth email link."""
    monkeypatch.setattr(
        "accounts.views._google_userinfo",
        lambda _token: {"sub": "new-admin-sub", "email": admin_user.email},
    )

    response = api_client.post(
        "/api/v1/auth/sessions/oauth",
        {"accessToken": "fake-token"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin accounts must use Django admin."
