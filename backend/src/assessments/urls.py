"""Assessment URL routes - /api/assessments/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_or_create, name="assessments-list-create"),
    path("<int:assessment_id>", views.detail, name="assessments-detail"),
    path("<int:assessment_id>/archive", views.archive, name="assessments-archive"),
    path("<int:assessment_id>/restore", views.restore, name="assessments-restore"),
]
