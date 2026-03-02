"""Student URL routes - /api/students/*"""

from django.urls import path

from submissions import views as submission_views

urlpatterns = [
    path(
        "<int:student_id>/submissions/",
        submission_views.get_by_student_id,
        name="students-submissions",
    ),
    path(
        "<int:student_id>/assignments/<int:assignment_id>/submission/",
        submission_views.get_student_submission,
        name="students-assignment-submission",
    ),
    path(
        "<int:student_id>/assignments/<int:assignment_id>/draft/",
        submission_views.save_draft,
        name="students-assignment-draft",
    ),
]
