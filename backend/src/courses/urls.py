"""Course URL routes - /api/courses/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_or_create, name="courses-list-create"),
    path("<int:course_id>", views.detail, name="courses-detail"),
    path("<int:course_id>/archive", views.archive, name="courses-archive"),
    path("<int:course_id>/restore", views.restore, name="courses-restore"),
    path("<int:course_id>/students", views.list_or_add_students, name="courses-students"),
    path(
        "<int:course_id>/students/<int:student_user_id>",
        views.remove_student,
        name="courses-students-remove",
    ),
]
