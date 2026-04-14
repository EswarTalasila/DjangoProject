"""AssignmentTemplate URL routes."""

from django.urls import path

from . import image_views, views

urlpatterns = [
    path("", views.list_or_create, name="assignment-templates-list-create"),
    path("<int:assignment_template_id>", views.detail, name="assignment-templates-detail"),
    path("<int:assignment_template_id>/archive", views.archive, name="assignment-templates-archive"),
    path("<int:assignment_template_id>/restore", views.restore, name="assignment-templates-restore"),
    path("<int:assignment_template_id>/publish", views.publish, name="assignment-templates-publish"),
    # Question images
    path(
        "<int:assignment_template_id>/questions/<int:question_id>/image",
        image_views.upload_or_delete,
        name="assignment-templates-question-image",
    ),
    path(
        "images/<path:storage_key>",
        image_views.serve_image,
        name="assignment-templates-serve-image",
    ),
]
