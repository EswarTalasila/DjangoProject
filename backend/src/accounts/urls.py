"""Accounts URL routes - /api/auth/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login, name="auth-login"),
    path("register", views.register, name="auth-register"),
    path("google", views.login_with_google, name="auth-google"),
    path("check-email", views.check_email, name="auth-check-email"),
    path("createuser", views.create_user, name="auth-create-user"),
    path("create/bulk", views.bulk_create, name="auth-create-bulk"),
    path("edituser/<int:user_id>", views.edit_user, name="auth-edit-user"),
    path("reset/<int:user_id>", views.reset_password, name="auth-reset-password"),
    path("users/<int:user_id>/set-password", views.set_password, name="auth-set-password"),
    path("teachers-admins", views.list_teachers_admins, name="auth-teachers-admins"),
    path("user/<str:username>", views.delete_user, name="auth-delete-user"),
]
