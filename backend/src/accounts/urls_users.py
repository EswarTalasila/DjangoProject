"""User management URL routes - /api/v1/users/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_user, name="users-create"),
    path("staff", views.list_staff, name="users-staff"),
    path("<int:user_id>", views.manage_user, name="users-manage"),
]
