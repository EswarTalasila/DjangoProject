"""Image upload business logic (FR-15 IMG).

Submission-specific orchestration. Generic validation, EXIF stripping,
hashing, and storage key generation live in core.media.services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.media.services import (  # noqa: F401  — re-exported for backward compat
    ImageValidationError,
    compute_sha256,
    generate_storage_key,
    strip_exif,
    upload_asset,
    validate_file_size,
    validate_mime_and_magic,
)
from core.media.storage import get_storage_backend
from core.media.types import ImageStatus as AssetStatus

from .models import ImageStatus, SubmissionImage

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

    from .models import Submission

logger = logging.getLogger(__name__)


def check_image_count(submission_id: int) -> None:
    """Raise ImageValidationError(409) if submission already has max images."""
    count = SubmissionImage.objects.filter(
        submission_id=submission_id,
        status__in=[ImageStatus.READY, ImageStatus.PENDING_SCAN],
    ).count()
    if count >= settings.IMG_MAX_IMAGES_PER_SUBMISSION:
        raise ImageValidationError(
            f"Image count limit reached ({settings.IMG_MAX_IMAGES_PER_SUBMISSION})",
            409,
        )


def check_duplicate(submission_id: int, sha256_hash: str) -> None:
    """Raise ImageValidationError(409) if an active image with same hash exists."""
    exists = SubmissionImage.objects.filter(
        submission_id=submission_id,
        sha256_hash=sha256_hash,
    ).exclude(status=ImageStatus.DELETED).exists()
    if exists:
        raise ImageValidationError("Duplicate file for this submission", 409)


def run_scan_hook(image: SubmissionImage) -> None:
    """Execute scan hook (IMG-CN-09).

    Non-production or IMG_ALLOW_UNSCANNED_UPLOADS=true: auto-promote to READY.
    Production without override: leave as PENDING_SCAN.
    """
    from config.env import env

    should_auto_promote = (
        not env.is_production or env.img_allow_unscanned_uploads
    )
    if should_auto_promote:
        image.status = ImageStatus.READY
        image.save(update_fields=["status"])


@transaction.atomic
def upload_image(
    submission: Submission,
    file: UploadedFile,
    uploader_id: int,
    owner_id: int,
) -> SubmissionImage:
    """Full upload pipeline (IMG-UC-01/02).

    Runs under transaction.atomic with submission row lock to prevent
    concurrent count/duplicate race conditions.
    """
    # Lock the submission row to serialize concurrent uploads
    from .models import Submission as SubmissionModel

    SubmissionModel.objects.select_for_update().get(pk=submission.pk)

    # 1. Validate MIME + magic
    mime_type = validate_mime_and_magic(file)

    # 2. Validate size
    size_bytes = validate_file_size(file)

    # 3. Check count limit
    check_image_count(submission.id)

    # 4. Read file data
    file.seek(0)
    raw_data = file.read()

    # 5. Strip EXIF
    clean_data = strip_exif(raw_data, mime_type)

    # 6. Hash AFTER EXIF strip (normalized dedupe)
    sha256_hash = compute_sha256(clean_data)

    # 7. Check duplicate (service level)
    check_duplicate(submission.id, sha256_hash)

    # 8. Generate storage key
    storage_key = generate_storage_key(f"submissions/{submission.id}", mime_type)

    # 9. Store file
    backend = get_storage_backend()
    backend.store(storage_key, clean_data)

    # 10. Create ImageAsset record
    from core.media.models import ImageAsset

    asset = ImageAsset.objects.create(
        storage_key=storage_key,
        original_filename=file.name or "unknown",
        mime_type=mime_type,
        size_bytes=len(clean_data),
        sha256_hash=sha256_hash,
        status=AssetStatus.ACTIVE,
        created_by_id=uploader_id,
    )

    # 11. Create SubmissionImage record linked to asset
    image = SubmissionImage.objects.create(
        submission=submission,
        uploaded_by_id=uploader_id,
        submission_owner_id=owner_id,
        asset=asset,
        storage_key=storage_key,
        original_filename=file.name or "unknown",
        mime_type=mime_type,
        size_bytes=len(clean_data),
        sha256_hash=sha256_hash,
        status=ImageStatus.PENDING_SCAN,
    )

    # 12. Scan hook
    run_scan_hook(image)

    return image


def soft_delete_image(image: SubmissionImage) -> None:
    """Soft-delete an image (IMG-UC-04)."""
    image.status = ImageStatus.DELETED
    image.deleted_at = timezone.now()
    image.save(update_fields=["status", "deleted_at"])

    # Also mark the asset as deleted if present
    if image.asset_id:
        image.asset.status = AssetStatus.DELETED
        image.asset.deleted_at = image.deleted_at
        image.asset.save(update_fields=["status", "deleted_at"])


def cleanup_images_for_submission(submission_id: int) -> None:
    """Hard-delete all images and blobs for a submission (IMG-CN-12 purge cascade).

    Idempotent: missing blobs are logged and skipped.
    """
    images = SubmissionImage.objects.filter(submission_id=submission_id)
    backend = get_storage_backend()

    # Collect asset IDs for cleanup
    asset_ids = list(images.exclude(asset__isnull=True).values_list("asset_id", flat=True))

    for img in images:
        try:
            backend.delete(img.storage_key)
        except Exception:
            logger.warning(
                "Blob cleanup failed for image %s key %s; skipping",
                img.id,
                img.storage_key,
            )
    images.delete()

    # Clean up orphaned assets
    if asset_ids:
        from core.media.models import ImageAsset

        ImageAsset.objects.filter(id__in=asset_ids).delete()


def image_to_dto_dict(image: SubmissionImage) -> dict:
    """Convert a SubmissionImage to a response dict."""
    return {
        "id": str(image.id),
        "originalFilename": image.original_filename,
        "mimeType": image.mime_type,
        "sizeBytes": image.size_bytes,
        "uploadedByUserId": image.uploaded_by_id,
        "status": image.status,
        "createdAt": image.created_at.isoformat() if image.created_at else None,
    }
