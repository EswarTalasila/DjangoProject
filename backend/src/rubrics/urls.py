"""Rubric URL routes - /api/v1/rubrics/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_or_create, name="rubrics-list-create"),
    path("<int:rubric_id>", views.detail, name="rubrics-detail"),
    path("<int:rubric_id>/archive", views.archive, name="rubrics-archive"),
]
