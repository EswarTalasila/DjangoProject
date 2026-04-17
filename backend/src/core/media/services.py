"""Generic media validation and processing pipeline.

Functions extracted from submissions.image_services to be reusable across
any domain context (submissions, profiles, etc.).
"""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

# Pure-Python magic byte signatures for allowed image types.
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


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of data."""
    return hashlib.sha256(data).hexdigest()


def strip_exif(data: bytes, mime_type: str) -> bytes:
    """Strip EXIF metadata from image data using Pillow.

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


def generate_storage_key(prefix: str, mime_type: str) -> str:
    """Generate storage path: {prefix}/{uuid}.{ext}.

    ``prefix`` is a domain-specific path component, e.g.
    ``"submissions/42"`` or ``"profiles"``.
    """
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = ext_map.get(mime_type, "bin")
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def upload_asset(
    file: UploadedFile,
    uploader_id: int,
    storage_prefix: str,
) -> dict:
    """Generic image upload: validate -> strip EXIF -> hash -> store -> return metadata.

    Returns a dict with the blob metadata needed to create an ImageAsset record.
    Does NOT touch the database -- the caller is responsible for record creation.
    """
    from .storage import get_storage_backend

    # 1. Validate MIME + magic
    mime_type = validate_mime_and_magic(file)

    # 2. Validate size
    validate_file_size(file)

    # 3. Read file data
    file.seek(0)
    raw_data = file.read()

    # 4. Strip EXIF
    clean_data = strip_exif(raw_data, mime_type)

    # 5. Hash AFTER EXIF strip (normalized dedupe)
    sha256_hash = compute_sha256(clean_data)

    # 6. Generate storage key
    storage_key = generate_storage_key(storage_prefix, mime_type)

    # 7. Store file
    backend = get_storage_backend()
    backend.store(storage_key, clean_data)

    return {
        "storage_key": storage_key,
        "original_filename": file.name or "unknown",
        "mime_type": mime_type,
        "size_bytes": len(clean_data),
        "sha256_hash": sha256_hash,
    }
