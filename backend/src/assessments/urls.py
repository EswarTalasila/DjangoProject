"""Assessment URL routes - /api/assessments/*"""

from django.urls import path

from submissions import views as submission_views

from . import views

urlpatterns = [
    path("", views.list_or_create, name="assessments-list-create"),
    path("<int:assessment_id>", views.detail, name="assessments-detail"),
    path(
        "<int:assessment_id>/teacher-self-assess",
        submission_views.teacher_self_assess,
        name="assessments-teacher-self-assess",
    ),
]
