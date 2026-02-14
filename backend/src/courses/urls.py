"""Course URL routes - /api/courses/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_or_create, name="courses-list-create"),
    path("<int:course_id>", views.detail, name="courses-detail"),
    path("<int:course_id>/students", views.list_students, name="courses-students-list"),
    path(
        "<int:course_id>/students/<int:student_user_id>",
        views.remove_student,
        name="courses-students-remove",
    ),
    path(
        "<int:course_id>/students/<int:student_user_id>/reset-code",
        views.generate_student_reset_code,
        name="courses-students-reset-code",
    ),
]
