"""ImageAsset model for generic image blob tracking."""

import uuid

from django.conf import settings
from django.db import models

from .types import ImageStatus


class ImageAsset(models.Model):
    """A stored image blob with metadata, independent of any domain context.

    Each upload creates one ImageAsset.  Domain-specific link tables
    (e.g. SubmissionImage) hold a FK to this model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    sha256_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=ImageStatus.choices,
        default=ImageStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="image_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "image_assets"

    def __str__(self):
        return f"ImageAsset({self.id})"
