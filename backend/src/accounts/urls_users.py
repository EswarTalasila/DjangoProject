"""User management URL routes - /api/v1/users/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_user, name="users-create"),
    path("bulk", views.bulk_create, name="users-bulk"),
    path("staff", views.list_staff, name="users-staff"),
    path("sudo", views.grant_sudo, name="users-sudo-grant"),
    path("sudo/<int:grant_id>", views.revoke_sudo, name="users-sudo-revoke"),
    path("<int:user_id>", views.edit_user, name="users-edit"),
    path("<str:username>", views.delete_user, name="users-delete"),
]
