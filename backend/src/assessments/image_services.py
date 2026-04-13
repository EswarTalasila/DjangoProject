"""Assessment question image upload pipeline.

Reuses core.media for validation, EXIF stripping, hashing, and storage.
Each question stores at most one image reference in its `image` TextField
as a JSON blob.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.db import transaction

from core.media.models import ImageAsset
from core.media.services import (
    ImageValidationError,
    compute_sha256,
    generate_storage_key,
    strip_exif,
    validate_file_size,
    validate_mime_and_magic,
)
from core.media.storage import get_storage_backend
from core.media.types import ImageStatus as AssetStatus

from .models import Question

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


def parse_question_image(question: Question) -> dict | None:
    """Parse the JSON stored in Question.image, returning None if empty."""
    if not question.image:
        return None
    try:
        data = json.loads(question.image)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def question_image_to_dto(question: Question) -> dict | None:
    """Build a DTO dict from the question's stored image metadata."""
    meta = parse_question_image(question)
    if not meta:
        return None
    return {
        "id": meta.get("assetId", ""),
        "storageKey": meta.get("storageKey", ""),
        "url": f"/api/v1/assessments/images/{meta.get('storageKey', '')}",
        "originalFilename": meta.get("originalFilename", ""),
        "mimeType": meta.get("mimeType", ""),
        "sizeBytes": meta.get("sizeBytes", 0),
    }


@transaction.atomic
def upload_question_image(
    question: Question,
    file: UploadedFile,
    uploader_id: int,
) -> dict:
    """Upload an image for a question, replacing any existing one.

    Returns a DTO dict with the new image metadata.
    """
    # 1. Validate MIME + magic bytes
    mime_type = validate_mime_and_magic(file)

    # 2. Validate file size
    validate_file_size(file)

    # 3. Read and clean
    file.seek(0)
    raw_data = file.read()
    clean_data = strip_exif(raw_data, mime_type)

    # 4. Hash
    sha256_hash = compute_sha256(clean_data)

    # 5. Storage key
    storage_key = generate_storage_key(
        f"questions/{question.id}", mime_type
    )

    # 6. Store blob
    backend = get_storage_backend()
    backend.store(storage_key, clean_data)

    # 7. Create ImageAsset record
    asset = ImageAsset.objects.create(
        storage_key=storage_key,
        original_filename=file.name or "unknown",
        mime_type=mime_type,
        size_bytes=len(clean_data),
        sha256_hash=sha256_hash,
        status=AssetStatus.ACTIVE,
        created_by_id=uploader_id,
    )

    # 8. Remove old image blob if present
    _cleanup_old_image(question)

    # 9. Persist metadata on the question
    image_meta = {
        "assetId": str(asset.id),
        "storageKey": storage_key,
        "originalFilename": file.name or "unknown",
        "mimeType": mime_type,
        "sizeBytes": len(clean_data),
        "sha256Hash": sha256_hash,
    }
    question.image = json.dumps(image_meta)
    question.save(update_fields=["image"])

    return question_image_to_dto(question)


def remove_question_image(question: Question) -> None:
    """Remove the image from a question and clean up storage."""
    _cleanup_old_image(question)
    question.image = None
    question.save(update_fields=["image"])


def _cleanup_old_image(question: Question) -> None:
    """Delete the old image blob and asset if present."""
    meta = parse_question_image(question)
    if not meta:
        return

    old_key = meta.get("storageKey")
    if old_key:
        try:
            backend = get_storage_backend()
            backend.delete(old_key)
        except Exception:
            logger.warning(
                "Failed to delete old image blob for question %s key %s",
                question.id,
                old_key,
            )

    old_asset_id = meta.get("assetId")
    if old_asset_id:
        ImageAsset.objects.filter(id=old_asset_id).update(
            status=AssetStatus.DELETED,
        )
