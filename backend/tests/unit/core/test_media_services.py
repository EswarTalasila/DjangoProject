"""Pure unit tests for core.media.services (no database).

Tests the generic image validation, EXIF stripping, hashing,
storage key generation, and upload_asset pipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# validate_mime_and_magic
# ---------------------------------------------------------------------------

class TestValidateMimeAndMagic:

    @patch("core.media.services.settings")
    def test_rejects_unsupported_mime(self, mock_settings):
        """Rejects files with a MIME type not in the allowed list."""
        from core.media.services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/jpeg"}
        file = MagicMock()
        file.content_type = "application/pdf"

        with pytest.raises(ImageValidationError) as exc_info:
            validate_mime_and_magic(file)
        assert exc_info.value.status_code == 415

    @patch("core.media.services.settings")
    def test_accepts_jpeg(self, mock_settings):
        """Accepts JPEG with matching magic bytes."""
        from core.media.services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/jpeg"}
        file = MagicMock()
        file.content_type = "image/jpeg"
        file.read.return_value = b"\xff\xd8\xff" + b"\x00" * 9

        assert validate_mime_and_magic(file) == "image/jpeg"

    @patch("core.media.services.settings")
    def test_rejects_jpeg_wrong_magic(self, mock_settings):
        """Rejects JPEG-typed file with non-JPEG magic bytes."""
        from core.media.services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/jpeg"}
        file = MagicMock()
        file.content_type = "image/jpeg"
        file.read.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"

        with pytest.raises(ImageValidationError) as exc_info:
            validate_mime_and_magic(file)
        assert exc_info.value.status_code == 415

    @patch("core.media.services.settings")
    def test_accepts_png(self, mock_settings):
        """Accepts PNG with matching magic bytes."""
        from core.media.services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/png"}
        file = MagicMock()
        file.content_type = "image/png"
        file.read.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"

        assert validate_mime_and_magic(file) == "image/png"

    @patch("core.media.services.settings")
    def test_accepts_webp(self, mock_settings):
        """Accepts WebP with matching RIFF/WEBP magic bytes."""
        from core.media.services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/webp"}
        file = MagicMock()
        file.content_type = "image/webp"
        file.read.return_value = b"RIFF\x00\x00\x00\x00WEBP"

        assert validate_mime_and_magic(file) == "image/webp"

    @patch("core.media.services.settings")
    def test_rejects_webp_wrong_magic(self, mock_settings):
        """Rejects WebP-typed file whose RIFF payload is not WEBP."""
        from core.media.services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/webp"}
        file = MagicMock()
        file.content_type = "image/webp"
        file.read.return_value = b"RIFF\x00\x00\x00\x00XXXX"

        with pytest.raises(ImageValidationError) as exc_info:
            validate_mime_and_magic(file)
        assert exc_info.value.status_code == 415


# ---------------------------------------------------------------------------
# validate_file_size
# ---------------------------------------------------------------------------

class TestValidateFileSize:

    @patch("core.media.services.settings")
    def test_accepts_under_limit(self, mock_settings):
        """Returns size when file is under limit."""
        from core.media.services import validate_file_size

        mock_settings.IMG_MAX_FILE_SIZE_BYTES = 10_000_000
        file = MagicMock(size=500_000)

        assert validate_file_size(file) == 500_000

    @patch("core.media.services.settings")
    def test_rejects_over_limit(self, mock_settings):
        """Raises 413 when file exceeds limit."""
        from core.media.services import ImageValidationError, validate_file_size

        mock_settings.IMG_MAX_FILE_SIZE_BYTES = 1_000_000
        file = MagicMock(size=2_000_000)

        with pytest.raises(ImageValidationError) as exc_info:
            validate_file_size(file)
        assert exc_info.value.status_code == 413


# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------

class TestComputeSha256:

    def test_produces_hex_digest(self):
        """Returns a 64-char hex SHA-256 digest."""
        from core.media.services import compute_sha256

        result = compute_sha256(b"hello world")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        """Same input always gives the same hash."""
        from core.media.services import compute_sha256

        assert compute_sha256(b"test") == compute_sha256(b"test")

    def test_different_for_different_input(self):
        """Different inputs produce different hashes."""
        from core.media.services import compute_sha256

        assert compute_sha256(b"a") != compute_sha256(b"b")


# ---------------------------------------------------------------------------
# strip_exif
# ---------------------------------------------------------------------------

class TestStripExif:

    def test_returns_bytes(self):
        """strip_exif always returns bytes."""
        from core.media.services import strip_exif

        # Create a minimal valid JPEG
        header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        footer = b"\xff\xd9"
        data = header + footer

        result = strip_exif(data, "image/jpeg")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_fallback_on_corrupt(self):
        """Falls back to original data if Pillow cannot parse."""
        from core.media.services import strip_exif

        corrupt = b"not a real image at all"
        result = strip_exif(corrupt, "image/jpeg")
        assert result == corrupt


# ---------------------------------------------------------------------------
# generate_storage_key
# ---------------------------------------------------------------------------

class TestGenerateStorageKey:

    def test_includes_prefix(self):
        """Key starts with the given prefix."""
        from core.media.services import generate_storage_key

        key = generate_storage_key("submissions/42", "image/jpeg")
        assert key.startswith("submissions/42/")

    def test_jpeg_extension(self):
        """JPEG MIME maps to .jpg extension."""
        from core.media.services import generate_storage_key

        key = generate_storage_key("test", "image/jpeg")
        assert key.endswith(".jpg")

    def test_png_extension(self):
        """PNG MIME maps to .png extension."""
        from core.media.services import generate_storage_key

        key = generate_storage_key("test", "image/png")
        assert key.endswith(".png")

    def test_webp_extension(self):
        """WebP MIME maps to .webp extension."""
        from core.media.services import generate_storage_key

        key = generate_storage_key("test", "image/webp")
        assert key.endswith(".webp")

    def test_unknown_mime_uses_bin(self):
        """Unknown MIME type falls back to .bin extension."""
        from core.media.services import generate_storage_key

        key = generate_storage_key("test", "application/octet-stream")
        assert key.endswith(".bin")

    def test_unique_keys(self):
        """Successive calls produce unique keys."""
        from core.media.services import generate_storage_key

        k1 = generate_storage_key("test", "image/jpeg")
        k2 = generate_storage_key("test", "image/jpeg")
        assert k1 != k2


# ---------------------------------------------------------------------------
# upload_asset
# ---------------------------------------------------------------------------

class TestUploadAsset:

    @patch("core.media.storage.get_storage_backend")
    @patch("core.media.services.settings")
    def test_returns_metadata_dict(self, mock_settings, mock_get_backend):
        """upload_asset returns a dict with all required blob metadata keys."""
        from core.media.services import upload_asset

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/jpeg"}
        mock_settings.IMG_MAX_FILE_SIZE_BYTES = 10_000_000

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        # Minimal valid JPEG
        header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        footer = b"\xff\xd9"
        jpeg_data = header + b"\x00" * 50 + footer

        file = MagicMock()
        file.content_type = "image/jpeg"
        file.size = len(jpeg_data)
        file.name = "photo.jpg"
        file.read.return_value = b"\xff\xd8\xff" + b"\x00" * 9  # magic header

        # For the full read after seek(0):
        read_calls = [b"\xff\xd8\xff" + b"\x00" * 9, jpeg_data]
        file.read.side_effect = read_calls

        result = upload_asset(file, uploader_id=1, storage_prefix="test")

        assert "storage_key" in result
        assert "original_filename" in result
        assert "mime_type" in result
        assert "size_bytes" in result
        assert "sha256_hash" in result
        assert result["mime_type"] == "image/jpeg"
        assert result["original_filename"] == "photo.jpg"
        mock_backend.store.assert_called_once()

    @patch("core.media.services.settings")
    def test_rejects_invalid_mime(self, mock_settings):
        """upload_asset raises ImageValidationError for disallowed MIME."""
        from core.media.services import ImageValidationError, upload_asset

        mock_settings.IMG_ALLOWED_MIME_TYPES = {"image/jpeg"}

        file = MagicMock()
        file.content_type = "image/gif"

        with pytest.raises(ImageValidationError) as exc_info:
            upload_asset(file, uploader_id=1, storage_prefix="test")
        assert exc_info.value.status_code == 415


# ---------------------------------------------------------------------------
# ImageAsset model
# ---------------------------------------------------------------------------

class TestImageAssetModel:

    def test_default_status(self):
        """ImageAsset default status is ACTIVE."""
        from core.media.types import ImageStatus

        assert ImageStatus.ACTIVE == "ACTIVE"
        assert ImageStatus.DELETED == "DELETED"

    def test_image_context_enum(self):
        """ImageContext has SUBMISSION value."""
        from core.media.types import ImageContext

        assert ImageContext.SUBMISSION == "SUBMISSION"
