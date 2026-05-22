"""Accounts URL routes - /api/v1/auth/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.login, name="auth-sessions"),
    path("demo-sessions", views.demo_login, name="auth-demo-sessions"),
    path("me", views.current_user_profile, name="auth-me"),
    path("sessions/oauth", views.login_with_google, name="auth-sessions-oauth"),
    path("token-exchanges", views.refresh, name="auth-token-exchanges"),
    path("session-revocations", views.logout, name="auth-session-revocations"),
    path("password", views.change_password, name="auth-password"),
    path(
        "password-reset-codes",
        views.issue_password_reset_code_view,
        name="auth-password-reset-codes",
    ),
    path("reset-code-validations", views.verify_reset_code, name="auth-reset-code-validations"),
    path("password-resets", views.complete_reset_code, name="auth-password-resets"),
]
