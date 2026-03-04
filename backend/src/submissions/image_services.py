"""Image upload business logic (FR-15 IMG)."""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from config.env import env

from .models import ImageStatus, SubmissionImage
from .storage import get_storage_backend

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

    from .models import Submission

logger = logging.getLogger(__name__)

# Pure-Python magic byte signatures for allowed image types (IMG-CN-01).
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # RIFF header; full check below
}


class ImageValidationError(Exception):
    """Raised when an uploaded image fails validation."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def validate_mime_and_magic(file: UploadedFile) -> str:
    """Validate Content-Type is in allowlist and magic bytes match.

    Returns the validated MIME type.
    Raises ImageValidationError(415) on mismatch.
    """
    content_type = file.content_type or ""
    if content_type not in settings.IMG_ALLOWED_MIME_TYPES:
        raise ImageValidationError(
            f"Unsupported image type: {content_type}", 415
        )

    # Read first bytes for magic check
    file.seek(0)
    header = file.read(12)
    file.seek(0)

    if content_type == "image/jpeg":
        if not header.startswith(b"\xff\xd8\xff"):
            raise ImageValidationError("File magic bytes do not match image/jpeg", 415)
    elif content_type == "image/png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ImageValidationError("File magic bytes do not match image/png", 415)
    elif content_type == "image/webp":
        # WebP: RIFF????WEBP
        if not (header[:4] == b"RIFF" and header[8:12] == b"WEBP"):
            raise ImageValidationError("File magic bytes do not match image/webp", 415)

    return content_type


def validate_file_size(file: UploadedFile) -> int:
    """Return file size in bytes. Raises ImageValidationError(413) if too large."""
    size = file.size
    if size > settings.IMG_MAX_FILE_SIZE_BYTES:
        raise ImageValidationError(
            f"File size {size} exceeds maximum {settings.IMG_MAX_FILE_SIZE_BYTES} bytes",
            413,
        )
    return size


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


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of data."""
    return hashlib.sha256(data).hexdigest()


def check_duplicate(submission_id: int, sha256_hash: str) -> None:
    """Raise ImageValidationError(409) if an active image with same hash exists."""
    exists = SubmissionImage.objects.filter(
        submission_id=submission_id,
        sha256_hash=sha256_hash,
    ).exclude(status=ImageStatus.DELETED).exists()
    if exists:
        raise ImageValidationError("Duplicate file for this submission", 409)


def strip_exif(data: bytes, mime_type: str) -> bytes:
    """Strip EXIF metadata from image data using Pillow (IMG-CN-07).

    Returns cleaned image bytes. Falls back to original data if stripping fails.
    """
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(data))
        output = io.BytesIO()
        # Map MIME to Pillow format
        fmt_map = {
            "image/jpeg": "JPEG",
            "image/png": "PNG",
            "image/webp": "WEBP",
        }
        fmt = fmt_map.get(mime_type, "JPEG")
        # Re-save without EXIF (Pillow strips metadata on save by default
        # unless explicitly preserved via exif= kwarg)
        save_kwargs: dict = {"format": fmt}
        if fmt == "JPEG":
            save_kwargs["quality"] = 95
        img.save(output, **save_kwargs)
        return output.getvalue()
    except Exception:
        logger.warning("EXIF stripping failed for %s; using original bytes", mime_type)
        return data


def generate_storage_key(submission_id: int, mime_type: str) -> str:
    """Generate storage path: submissions/{submission_id}/{uuid}.{ext} (IMG-CN-10)."""
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = ext_map.get(mime_type, "bin")
    return f"submissions/{submission_id}/{uuid.uuid4()}.{ext}"


def run_scan_hook(image: SubmissionImage) -> None:
    """Execute scan hook (IMG-CN-09).

    Non-production or IMG_ALLOW_UNSCANNED_UPLOADS=true: auto-promote to READY.
    Production without override: leave as PENDING_SCAN.
    """
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
    storage_key = generate_storage_key(submission.id, mime_type)

    # 9. Store file
    backend = get_storage_backend()
    backend.store(storage_key, clean_data)

    # 10. Create DB record
    image = SubmissionImage.objects.create(
        submission=submission,
        uploaded_by_id=uploader_id,
        submission_owner_id=owner_id,
        storage_key=storage_key,
        original_filename=file.name or "unknown",
        mime_type=mime_type,
        size_bytes=len(clean_data),
        sha256_hash=sha256_hash,
        status=ImageStatus.PENDING_SCAN,
    )

    # 11. Scan hook
    run_scan_hook(image)

    return image


def soft_delete_image(image: SubmissionImage) -> None:
    """Soft-delete an image (IMG-UC-04)."""
    image.status = ImageStatus.DELETED
    image.deleted_at = timezone.now()
    image.save(update_fields=["status", "deleted_at"])


def cleanup_images_for_submission(submission_id: int) -> None:
    """Hard-delete all images and blobs for a submission (IMG-CN-12 purge cascade).

    Idempotent: missing blobs are logged and skipped.
    """
    images = SubmissionImage.objects.filter(submission_id=submission_id)
    backend = get_storage_backend()
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
