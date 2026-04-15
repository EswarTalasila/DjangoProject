"""Assignment URL routes - /api/v1/assignments/*"""

from django.urls import path

from submissions import views as submission_views

from . import image_views, views

urlpatterns = [
    path("", views.create, name="assignments-create"),
    path("<int:assignment_id>", views.detail, name="assignments-detail"),
    path(
        "<int:assignment_id>/template",
        views.get_assignment_template,
        name="assignments-template",
    ),
    path(
        "<int:assignment_id>/questions",
        views.create_assignment_question,
        name="assignments-question-create",
    ),
    path(
        "<int:assignment_id>/teacher-criteria",
        views.create_assignment_teacher_criterion,
        name="assignments-teacher-criterion-create",
    ),
    path(
        "<int:assignment_id>/images",
        views.reusable_images,
        name="assignments-reusable-images",
    ),
    path(
        "<int:assignment_id>/questions/<int:question_id>/image",
        image_views.upload_or_delete,
        name="assignments-question-image",
    ),
    path(
        "<int:assignment_id>/questions/<int:question_id>/image/reuse",
        image_views.reuse_image,
        name="assignments-question-image-reuse",
    ),
    path(
        "images/<path:storage_key>",
        image_views.serve_image,
        name="assignments-image-serve",
    ),
    path(
        "<int:assignment_id>/archive",
        views.archive,
        name="assignments-archive",
    ),
    path(
        "<int:assignment_id>/restore",
        views.restore,
        name="assignments-restore",
    ),
    path(
        "<int:assignment_id>/archive-bundle",
        views.archive_bundle,
        name="assignments-archive-bundle",
    ),
    path(
        "<int:assignment_id>/archive-bundle/download",
        views.download_archive_bundle,
        name="assignments-archive-bundle-download",
    ),
    path(
        "<int:assignment_id>/submissions",
        submission_views.assignment_submissions,
        name="assignments-submissions",
    ),
    path("courses/<int:course_id>", views.list_course, name="assignments-course"),
    path("users/<int:user_id>", views.list_user, name="assignments-user"),
]
