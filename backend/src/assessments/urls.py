"""Assessment URL routes - /api/assessments/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_or_create, name="assessments-list-create"),
    path("<int:assessment_id>", views.detail, name="assessments-detail"),
]
