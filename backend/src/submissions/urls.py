"""Submission URL routes - /api/submissions/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("<int:submission_id>", views.get_one, name="submissions-get"),
    path("me", views.list_me_view, name="submissions-me"),
    path(
        "<int:submission_id>/override-score",
        views.override_score_view,
        name="submissions-override",
    ),
]
