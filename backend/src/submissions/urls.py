"""Submission URL routes - /api/submissions/*"""

from django.urls import path

from . import image_views, views

urlpatterns = [
    path("<int:submission_id>", views.get_one, name="submissions-get"),
    path("me", views.list_me_view, name="submissions-me"),
    path(
        "<int:submission_id>/override-score",
        views.override_score_view,
        name="submissions-override",
    ),
    # Image endpoints (FR-15 IMG)
    path(
        "<int:submission_id>/images",
        image_views.upload_or_list_images,
        name="submission-images",
    ),
    path(
        "<int:submission_id>/images/<uuid:image_id>",
        image_views.retrieve_or_delete_image,
        name="submission-image-detail",
    ),
]
