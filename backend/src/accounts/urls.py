"""Accounts URL routes - /api/v1/auth/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.login, name="auth-sessions"),
    path("sessions/oauth", views.login_with_google, name="auth-sessions-oauth"),
    path("token-exchanges", views.refresh, name="auth-token-exchanges"),
    path("session-revocations", views.logout, name="auth-session-revocations"),
    path("password", views.change_password, name="auth-password"),
    path("reset-requests", views.create_reset_request, name="auth-reset-request-create"),
    path(
        "reset-request-lookups",
        views.reset_request_status,
        name="auth-reset-request-lookups",
    ),
    path(
        "reset-requests/<int:request_id>",
        views.transition_reset_request,
        name="auth-reset-request-transition",
    ),
    path("reset-code-validations", views.verify_reset_code, name="auth-reset-code-validations"),
    path("password-resets", views.complete_reset_code, name="auth-password-resets"),
]
