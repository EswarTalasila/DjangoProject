"""Submission URL routes - /api/submissions/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("<int:submission_id>", views.get_one, name="submissions-get"),
    path("mine", views.list_mine_view, name="submissions-mine"),
    path("", views.edit, name="submissions-edit"),
    path(
        "<int:submission_id>/override-score",
        views.override_score_view,
        name="submissions-override",
    ),
]
