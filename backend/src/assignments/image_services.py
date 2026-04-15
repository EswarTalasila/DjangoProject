"""Assignment question image upload and reuse helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.db import transaction

from core.media.models import ImageAsset
from core.media.services import (
    compute_sha256,
    generate_storage_key,
    strip_exif,
    validate_file_size,
    validate_mime_and_magic,
)
from core.media.storage import get_storage_backend
from core.media.types import ImageStatus as AssetStatus

from .models import AssignmentQuestion

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


def _image_meta_for_asset(asset: ImageAsset) -> dict:
    """Build the shared image metadata payload for assignment-question storage."""
    return {
        "assetId": str(asset.id),
        "storageKey": asset.storage_key,
        "originalFilename": asset.original_filename,
        "mimeType": asset.mime_type,
        "sizeBytes": asset.size_bytes,
        "sha256Hash": asset.sha256_hash,
    }


def assignment_question_image_to_dto(question: AssignmentQuestion) -> dict | None:
    """Convert stored assignment-question image metadata into the frontend DTO shape."""
    if not question.image:
        return None
    try:
        payload = json.loads(question.image)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "id": payload.get("assetId", ""),
        "storageKey": payload.get("storageKey", ""),
        "url": f"/api/v1/assignments/images/{payload.get('storageKey', '')}",
        "originalFilename": payload.get("originalFilename", ""),
        "mimeType": payload.get("mimeType", ""),
        "sizeBytes": payload.get("sizeBytes", 0),
    }


@transaction.atomic
def upload_assignment_question_image(
    question: AssignmentQuestion,
    file: UploadedFile,
    uploader_id: int,
) -> dict:
    """Upload or replace an assignment-question image."""
    mime_type = validate_mime_and_magic(file)
    validate_file_size(file)

    file.seek(0)
    raw_data = file.read()
    clean_data = strip_exif(raw_data, mime_type)
    sha256_hash = compute_sha256(clean_data)
    storage_key = generate_storage_key(f"assignment-questions/{question.id}", mime_type)

    backend = get_storage_backend()
    backend.store(storage_key, clean_data)

    asset = ImageAsset.objects.create(
        storage_key=storage_key,
        original_filename=file.name or "unknown",
        mime_type=mime_type,
        size_bytes=len(clean_data),
        sha256_hash=sha256_hash,
        status=AssetStatus.ACTIVE,
        created_by_id=uploader_id,
    )

    question.image_asset = asset
    question.image = json.dumps(_image_meta_for_asset(asset))
    question.save(update_fields=["image_asset", "image"])
    return assignment_question_image_to_dto(question)


@transaction.atomic
def attach_existing_question_image(question: AssignmentQuestion, asset: ImageAsset) -> dict:
    """Attach a previously uploaded asset to an assignment-local question without duplicating it."""
    question.image_asset = asset
    question.image = json.dumps(_image_meta_for_asset(asset))
    question.save(update_fields=["image_asset", "image"])
    return assignment_question_image_to_dto(question)


@transaction.atomic
def remove_assignment_question_image(question: AssignmentQuestion) -> None:
    """Detach an image from an assignment-local question."""
    question.image_asset = None
    question.image = None
    question.save(update_fields=["image_asset", "image"])
