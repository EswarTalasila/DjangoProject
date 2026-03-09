"""Pure unit tests for submissions.image_services (no database)."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class _NoopAtomicMixin:
    def setup_method(self):
        self._p_enter = patch(
            "django.db.transaction.Atomic.__enter__", return_value=None
        )
        self._p_exit = patch(
            "django.db.transaction.Atomic.__exit__", return_value=False
        )
        self._p_enter.start()
        self._p_exit.start()

    def teardown_method(self):
        self._p_exit.stop()
        self._p_enter.stop()


# ---------------------------------------------------------------------------
# validate_mime_and_magic
# ---------------------------------------------------------------------------

class TestValidateMimeAndMagic:

    @patch("submissions.image_services.settings")
    def test_rejects_unsupported_mime_type(self, mock_settings):
        """Rejects files with a MIME type not in the allowed list."""
        from submissions.image_services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/jpeg", "image/png"]
        file = MagicMock()
        file.content_type = "image/gif"

        with pytest.raises(ImageValidationError, match="Unsupported image type"):
            validate_mime_and_magic(file)

    @patch("submissions.image_services.settings")
    def test_accepts_valid_jpeg(self, mock_settings):
        """Accepts a JPEG file with correct MIME type and magic bytes."""
        from submissions.image_services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/jpeg"]
        file = MagicMock()
        file.content_type = "image/jpeg"
        file.read.return_value = b"\xff\xd8\xff" + b"\x00" * 9

        result = validate_mime_and_magic(file)
        assert result == "image/jpeg"

    @patch("submissions.image_services.settings")
    def test_rejects_jpeg_with_wrong_magic(self, mock_settings):
        """Rejects a JPEG-typed file whose magic bytes do not match."""
        from submissions.image_services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/jpeg"]
        file = MagicMock()
        file.content_type = "image/jpeg"
        file.read.return_value = b"\x00\x00\x00" + b"\x00" * 9

        with pytest.raises(ImageValidationError, match="magic bytes do not match"):
            validate_mime_and_magic(file)

    @patch("submissions.image_services.settings")
    def test_accepts_valid_png(self, mock_settings):
        """Accepts a PNG file with correct MIME type and magic bytes."""
        from submissions.image_services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/png"]
        file = MagicMock()
        file.content_type = "image/png"
        file.read.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4

        result = validate_mime_and_magic(file)
        assert result == "image/png"

    @patch("submissions.image_services.settings")
    def test_rejects_png_with_wrong_magic(self, mock_settings):
        """Rejects a PNG-typed file whose magic bytes do not match."""
        from submissions.image_services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/png"]
        file = MagicMock()
        file.content_type = "image/png"
        file.read.return_value = b"\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00" * 4

        with pytest.raises(ImageValidationError, match="magic bytes do not match"):
            validate_mime_and_magic(file)

    @patch("submissions.image_services.settings")
    def test_accepts_valid_webp(self, mock_settings):
        """Accepts a WebP file with correct MIME type and magic bytes."""
        from submissions.image_services import validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/webp"]
        file = MagicMock()
        file.content_type = "image/webp"
        file.read.return_value = b"RIFF\x00\x00\x00\x00WEBP"

        result = validate_mime_and_magic(file)
        assert result == "image/webp"

    @patch("submissions.image_services.settings")
    def test_rejects_webp_with_wrong_magic(self, mock_settings):
        """Rejects a WebP-typed file whose magic bytes do not match."""
        from submissions.image_services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/webp"]
        file = MagicMock()
        file.content_type = "image/webp"
        file.read.return_value = b"RIFF\x00\x00\x00\x00XXXX"

        with pytest.raises(ImageValidationError, match="magic bytes do not match"):
            validate_mime_and_magic(file)

    @patch("submissions.image_services.settings")
    def test_handles_none_content_type(self, mock_settings):
        """Rejects files with None content type as unsupported."""
        from submissions.image_services import ImageValidationError, validate_mime_and_magic

        mock_settings.IMG_ALLOWED_MIME_TYPES = ["image/jpeg"]
        file = MagicMock()
        file.content_type = None

        with pytest.raises(ImageValidationError, match="Unsupported image type"):
            validate_mime_and_magic(file)


# ---------------------------------------------------------------------------
# validate_file_size
# ---------------------------------------------------------------------------

class TestValidateFileSize:

    @patch("submissions.image_services.settings")
    def test_accepts_small_file(self, mock_settings):
        """Accepts a file whose size is under the maximum limit."""
        from submissions.image_services import validate_file_size

        mock_settings.IMG_MAX_FILE_SIZE_BYTES = 10_000_000
        file = MagicMock()
        file.size = 500_000

        result = validate_file_size(file)
        assert result == 500_000

    @patch("submissions.image_services.settings")
    def test_rejects_oversized_file(self, mock_settings):
        """Rejects a file that exceeds the maximum allowed size."""
        from submissions.image_services import ImageValidationError, validate_file_size

        mock_settings.IMG_MAX_FILE_SIZE_BYTES = 1_000_000
        file = MagicMock()
        file.size = 2_000_000

        with pytest.raises(ImageValidationError, match="exceeds maximum"):
            validate_file_size(file)


# ---------------------------------------------------------------------------
# check_image_count
# ---------------------------------------------------------------------------

class TestCheckImageCount:

    @patch("submissions.image_services.settings")
    @patch("submissions.image_services.SubmissionImage")
    def test_allows_under_limit(self, mock_img, mock_settings):
        """Allows upload when image count is below the per-submission limit."""
        from submissions.image_services import check_image_count

        mock_settings.IMG_MAX_IMAGES_PER_SUBMISSION = 10
        mock_img.objects.filter.return_value.count.return_value = 5

        check_image_count(1)  # should not raise

    @patch("submissions.image_services.settings")
    @patch("submissions.image_services.SubmissionImage")
    def test_rejects_at_limit(self, mock_img, mock_settings):
        """Rejects upload when image count has reached the per-submission limit."""
        from submissions.image_services import ImageValidationError, check_image_count

        mock_settings.IMG_MAX_IMAGES_PER_SUBMISSION = 10
        mock_img.objects.filter.return_value.count.return_value = 10

        with pytest.raises(ImageValidationError, match="limit reached"):
            check_image_count(1)


# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------

class TestComputeSha256:

    def test_computes_hash(self):
        """Produces a 64-character hex SHA-256 digest from input bytes."""
        from submissions.image_services import compute_sha256

        result = compute_sha256(b"hello")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest length


# ---------------------------------------------------------------------------
# check_duplicate
# ---------------------------------------------------------------------------

class TestCheckDuplicate:

    @patch("submissions.image_services.SubmissionImage")
    def test_allows_no_duplicate(self, mock_img):
        """Allows upload when no duplicate hash exists for the submission."""
        from submissions.image_services import check_duplicate

        mock_img.objects.filter.return_value.exclude.return_value.exists.return_value = False

        check_duplicate(1, "abc123")  # should not raise

    @patch("submissions.image_services.SubmissionImage")
    def test_rejects_duplicate(self, mock_img):
        """Rejects upload when a matching hash already exists for the submission."""
        from submissions.image_services import ImageValidationError, check_duplicate

        mock_img.objects.filter.return_value.exclude.return_value.exists.return_value = True

        with pytest.raises(ImageValidationError, match="Duplicate"):
            check_duplicate(1, "abc123")


