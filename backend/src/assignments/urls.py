"""Assignment URL routes - /api/v1/assignments/*"""

from django.urls import path

from submissions import views as submission_views

from . import views

urlpatterns = [
    path("", views.create, name="assignments-create"),
    path("<int:assignment_id>", views.detail, name="assignments-detail"),
    path(
        "<int:assignment_id>/template",
        views.template,
        name="assignments-template",
    ),
    path(
        "<int:assignment_id>/archive",
        views.archive,
        name="assignments-archive",
    ),
    path(
        "<int:assignment_id>/submissions",
        submission_views.assignment_submissions,
        name="assignments-submissions",
    ),
    path("courses/<int:course_id>", views.list_course, name="assignments-course"),
    path("users/<int:user_id>", views.list_user, name="assignments-user"),
]
