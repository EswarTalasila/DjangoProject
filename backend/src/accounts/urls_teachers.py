"""Teacher-specific URL routes - /api/teachers/*"""

from django.urls import path

from submissions import views as submission_views

urlpatterns = [
    path(
        "<int:teacher_id>/submissions",
        submission_views.get_by_teacher_id,
        name="teachers-submissions",
    ),
]
