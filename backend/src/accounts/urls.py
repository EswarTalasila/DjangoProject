"""Accounts URL routes - /api/auth/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login, name="auth-login"),
    path("oauth/google", views.login_with_google, name="auth-oauth-google"),
    path("refresh", views.refresh, name="auth-refresh"),
    path("logout", views.logout, name="auth-logout"),
    path("password/change", views.change_password, name="auth-password-change"),
    path("reset-requests", views.create_reset_request, name="auth-reset-request-create"),
    path(
        "reset-requests/status",
        views.reset_request_status,
        name="auth-reset-request-status",
    ),
    path(
        "reset-requests/<int:request_id>",
        views.transition_reset_request,
        name="auth-reset-request-transition",
    ),
    path("reset-codes/verify", views.verify_reset_code, name="auth-reset-code-verify"),
    path("reset-codes/complete", views.complete_reset_code, name="auth-reset-code-complete"),
]
