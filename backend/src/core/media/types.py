"""Enums for the shared media subsystem."""

from django.db import models


class ImageStatus(models.TextChoices):
    """Lifecycle status for image assets."""

    ACTIVE = "ACTIVE", "Active"
    DELETED = "DELETED", "Deleted"


class ImageContext(models.TextChoices):
    """Domain context that owns an image asset."""

    SUBMISSION = "SUBMISSION", "Submission"
