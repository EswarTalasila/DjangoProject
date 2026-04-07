"""Assessment URL routes - /api/assessments/*"""

from django.urls import path

from . import image_views, views

urlpatterns = [
    path("", views.list_or_create, name="assessments-list-create"),
    path("<int:assessment_id>", views.detail, name="assessments-detail"),
    path("<int:assessment_id>/archive", views.archive, name="assessments-archive"),
    path("<int:assessment_id>/restore", views.restore, name="assessments-restore"),
    path("<int:assessment_id>/publish", views.publish, name="assessments-publish"),
    # Question images
    path(
        "<int:assessment_id>/questions/<int:question_id>/image",
        image_views.upload_or_delete,
        name="assessments-question-image",
    ),
    path(
        "images/<path:storage_key>",
        image_views.serve_image,
        name="assessments-serve-image",
    ),
]
