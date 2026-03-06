"""Pure unit tests for submissions.image_views (no database).

The _handle_* functions are internal helpers called from within @api_view
decorated views, so they receive a DRF Request. We mock the request object
directly since we're testing the helpers, not the view dispatch.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

pytestmark = pytest.mark.unit


def _mock_request(*, user_id=1, files=None, method="POST"):
    """Build a mock DRF request with user and FILES."""
    request = MagicMock()
    request.user = MagicMock(id=user_id, is_staff=True, is_authenticated=True)
    request.FILES = files or {}
    request.method = method
    request.META = {"REMOTE_ADDR": "127.0.0.1"}
    return request


# ---------------------------------------------------------------------------
# _can_mutate_images
# ---------------------------------------------------------------------------

class TestCanMutateImages:

    @patch("submissions.image_views.primary_role", return_value="STUDENT")
    def test_student_owns_submission(self, mock_role):
        """Allows a student to mutate images on their own submission."""
        from submissions.image_views import _can_mutate_images

        user = MagicMock(id=10)
        submission = MagicMock(student_id=10)

        allowed, action = _can_mutate_images(user, submission)

        assert allowed is True
        assert action is not None

    @patch("submissions.image_views.primary_role", return_value="STUDENT")
    def test_student_does_not_own_submission(self, mock_role):
        """Denies a student from mutating images on another student's submission."""
        from submissions.image_views import _can_mutate_images

        user = MagicMock(id=10)
        submission = MagicMock(student_id=20)

        allowed, action = _can_mutate_images(user, submission)

        assert allowed is False
        assert action is None

    @patch("submissions.image_views._teacher_owns_assignment", return_value=True)
    @patch("submissions.image_views.primary_role", return_value="TEACHER")
    def test_teacher_owns_assignment(self, mock_role, mock_owns):
        """Allows a teacher to mutate images on their own assignment's submission."""
        from submissions.image_views import _can_mutate_images

        user = MagicMock(id=5)
        submission = MagicMock()

        allowed, action = _can_mutate_images(user, submission)

        assert allowed is True

    @patch("submissions.image_views._teacher_owns_assignment", return_value=False)
    @patch("submissions.image_views.primary_role", return_value="TEACHER")
    def test_teacher_does_not_own_assignment(self, mock_role, mock_owns):
        """Denies a teacher from mutating images on another teacher's assignment."""
        from submissions.image_views import _can_mutate_images

        user = MagicMock(id=5)
        submission = MagicMock()

        allowed, action = _can_mutate_images(user, submission)

        assert allowed is False

    @patch("submissions.image_views.primary_role", return_value="RESEARCHER")
    def test_researcher_cannot_mutate(self, mock_role):
        """Denies researchers from mutating submission images."""
        from submissions.image_views import _can_mutate_images

        user = MagicMock(id=5)
        submission = MagicMock()

        allowed, action = _can_mutate_images(user, submission)

        assert allowed is False


# ---------------------------------------------------------------------------
# _check_post_submit_lock
# ---------------------------------------------------------------------------

class TestCheckPostSubmitLock:

    def test_returns_409_for_submitted(self):
        """Returns 409 conflict for a submitted submission."""
        from submissions.image_views import _check_post_submit_lock
        from submissions.models import SubmissionStatus

        submission = MagicMock(status=SubmissionStatus.SUBMITTED)
        result = _check_post_submit_lock(submission)

        assert result is not None
        assert result.status_code == status.HTTP_409_CONFLICT

    def test_returns_409_for_graded(self):
        """Returns 409 conflict for a graded submission."""
        from submissions.image_views import _check_post_submit_lock
        from submissions.models import SubmissionStatus

        submission = MagicMock(status=SubmissionStatus.GRADED)
        result = _check_post_submit_lock(submission)

        assert result is not None
        assert result.status_code == status.HTTP_409_CONFLICT

    def test_returns_none_for_in_progress(self):
        """Returns none for an in-progress submission allowing mutation."""
        from submissions.image_views import _check_post_submit_lock
        from submissions.models import SubmissionStatus

        submission = MagicMock(status=SubmissionStatus.IN_PROGRESS)
        result = _check_post_submit_lock(submission)

        assert result is None


# ---------------------------------------------------------------------------
# _handle_upload
# ---------------------------------------------------------------------------

class TestHandleUpload:

    @patch("submissions.image_views._get_submission_with_assignment", return_value=None)
    def test_returns_404_when_submission_not_found(self, mock_get):
        """Returns 404 when the submission does not exist."""
        from submissions.image_views import _handle_upload

        request = _mock_request()
        response = _handle_upload(request, 999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views._can_mutate_images", return_value=(False, None))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_403_when_not_allowed(self, mock_get, mock_can):
        """Returns 403 when the user lacks permission to upload images."""
        from submissions.image_views import _handle_upload

        mock_get.return_value = MagicMock()
        request = _mock_request()
        response = _handle_upload(request, 1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("submissions.image_views._check_post_submit_lock")
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_UPLOAD"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_409_when_locked(self, mock_get, mock_can, mock_lock):
        """Returns 409 when the submission is locked after final submit."""
        from submissions.image_views import _handle_upload

        mock_get.return_value = MagicMock()
        lock_resp = MagicMock(status_code=409)
        mock_lock.return_value = lock_resp

        request = _mock_request()
        response = _handle_upload(request, 1)

        assert response is lock_resp

    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_UPLOAD"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_400_when_no_file(self, mock_get, mock_can, mock_lock):
        """Returns 400 when no file is included in the upload request."""
        from submissions.image_views import _handle_upload

        mock_get.return_value = MagicMock()
        request = _mock_request(files={})
        response = _handle_upload(request, 1)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("submissions.image_views.complete_audit")
    @patch("submissions.image_views.log_audit", return_value=1)
    @patch("submissions.image_views.get_client_ip", return_value="127.0.0.1")
    @patch("submissions.image_views.image_to_dto_dict", return_value={"id": "1"})
    @patch("submissions.image_views.upload_image")
    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_UPLOAD"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_successful_upload(
        self, mock_get, mock_can, mock_lock, mock_upload,
        mock_dto, mock_ip, mock_log, mock_complete
    ):
        """Returns 201 with image DTO on successful file upload."""
        from submissions.image_views import _handle_upload

        submission = MagicMock(student_id=1, teacher_id=None, id=1)
        mock_get.return_value = submission

        fake_file = MagicMock(name="test.jpg")
        request = _mock_request(files={"file": fake_file})
        mock_upload.return_value = MagicMock()

        response = _handle_upload(request, 1)

        assert response.status_code == status.HTTP_201_CREATED

    @patch("submissions.image_views.complete_audit")
    @patch("submissions.image_views.log_audit", return_value=1)
    @patch("submissions.image_views.get_client_ip", return_value="127.0.0.1")
    @patch("submissions.image_views.upload_image")
    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_UPLOAD"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_upload_validation_error(
        self, mock_get, mock_can, mock_lock, mock_upload,
        mock_ip, mock_log, mock_complete
    ):
        """Returns the validation error status code when image validation fails."""
        from submissions.image_services import ImageValidationError
        from submissions.image_views import _handle_upload

        submission = MagicMock(student_id=1, teacher_id=None, id=1)
        mock_get.return_value = submission

        fake_file = MagicMock(name="test.jpg")
        request = _mock_request(files={"file": fake_file})
        mock_upload.side_effect = ImageValidationError("Too large", 413)

        response = _handle_upload(request, 1)

        assert response.status_code == 413

    @patch("submissions.image_views.complete_audit")
    @patch("submissions.image_views.log_audit", return_value=1)
    @patch("submissions.image_views.get_client_ip", return_value="127.0.0.1")
    @patch("submissions.image_views.upload_image")
    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_UPLOAD"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_upload_unexpected_error(
        self, mock_get, mock_can, mock_lock, mock_upload,
        mock_ip, mock_log, mock_complete
    ):
        """Returns 500 when an unexpected exception occurs during upload."""
        from submissions.image_views import _handle_upload

        submission = MagicMock(student_id=1, teacher_id=None, id=1)
        mock_get.return_value = submission

        fake_file = MagicMock(name="test.jpg")
        request = _mock_request(files={"file": fake_file})
        mock_upload.side_effect = Exception("boom")

        response = _handle_upload(request, 1)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# _handle_list
# ---------------------------------------------------------------------------

class TestHandleList:

    @patch("submissions.image_views._get_submission_with_assignment", return_value=None)
    def test_returns_404_when_not_found(self, mock_get):
        """Returns 404 when the submission does not exist."""
        from submissions.image_views import _handle_list

        request = _mock_request(method="GET")
        response = _handle_list(request, 999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views._can_access_submission", return_value=False)
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_403_when_forbidden(self, mock_get, mock_access):
        """Returns 403 when the user cannot access the submission."""
        from submissions.image_views import _handle_list

        mock_get.return_value = MagicMock()
        request = _mock_request(method="GET")
        response = _handle_list(request, 1)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("submissions.image_views.image_to_dto_dict")
    @patch("submissions.image_views.SubmissionImage")
    @patch("submissions.image_views._can_access_submission", return_value=True)
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_image_list(self, mock_get, mock_access, mock_img_model, mock_dto):
        """Returns 200 with a list of image DTOs for the submission."""
        from submissions.image_views import _handle_list

        mock_get.return_value = MagicMock()
        img1 = MagicMock()
        mock_img_model.objects.filter.return_value.order_by.return_value = [img1]
        mock_dto.return_value = {"id": "1"}

        request = _mock_request(method="GET")
        response = _handle_list(request, 1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [{"id": "1"}]


# ---------------------------------------------------------------------------
# _handle_retrieve
# ---------------------------------------------------------------------------

class TestHandleRetrieve:

    @patch("submissions.image_views._get_submission_with_assignment", return_value=None)
    def test_returns_404_when_submission_not_found(self, mock_get):
        """Returns 404 when the submission does not exist."""
        from submissions.image_views import _handle_retrieve

        request = _mock_request(method="GET")
        response = _handle_retrieve(request, 1, "img-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views._can_access_submission", return_value=False)
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_403_when_forbidden(self, mock_get, mock_access):
        """Returns 403 when the user cannot access the submission."""
        from submissions.image_views import _handle_retrieve

        mock_get.return_value = MagicMock()
        request = _mock_request(method="GET")
        response = _handle_retrieve(request, 1, "img-id")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("submissions.image_views.SubmissionImage")
    @patch("submissions.image_views._can_access_submission", return_value=True)
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_404_when_image_not_found(self, mock_get, mock_access, mock_img):
        """Returns 404 when the requested image does not exist."""
        from submissions.image_views import _handle_retrieve

        mock_get.return_value = MagicMock()
        mock_img.objects.filter.return_value.first.return_value = None

        request = _mock_request(method="GET")
        response = _handle_retrieve(request, 1, "img-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views.SubmissionImage")
    @patch("submissions.image_views._can_access_submission", return_value=True)
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_image_with_headers(self, mock_get, mock_access, mock_img):
        """Returns 200 with X-Accel-Redirect and cache headers for the image."""
        from submissions.image_views import _handle_retrieve

        mock_get.return_value = MagicMock()
        image = MagicMock()
        image.mime_type = "image/jpeg"
        image.storage_key = "submissions/1/uuid.jpg"
        image.sha256_hash = "abc123"
        image.created_at.strftime.return_value = "Mon, 01 Jan 2025 00:00:00 GMT"
        mock_img.objects.filter.return_value.first.return_value = image

        request = _mock_request(method="GET")
        response = _handle_retrieve(request, 1, "img-id")

        assert response.status_code == 200
        assert response["X-Accel-Redirect"] == "/internal/media/submissions/1/uuid.jpg"
        assert response["Cache-Control"] == "private"


# ---------------------------------------------------------------------------
# _handle_delete
# ---------------------------------------------------------------------------

class TestHandleDelete:

    @patch("submissions.image_views._get_submission_with_assignment", return_value=None)
    def test_returns_404_when_submission_not_found(self, mock_get):
        """Returns 404 when the submission does not exist."""
        from submissions.image_views import _handle_delete

        request = _mock_request(method="DELETE")
        response = _handle_delete(request, 1, "img-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views._can_mutate_images", return_value=(False, None))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_403_when_not_allowed(self, mock_get, mock_can):
        """Returns 403 when the user lacks permission to delete images."""
        from submissions.image_views import _handle_delete

        mock_get.return_value = MagicMock()
        request = _mock_request(method="DELETE")
        response = _handle_delete(request, 1, "img-id")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("submissions.image_views._check_post_submit_lock")
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_DELETE"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_409_when_locked(self, mock_get, mock_can, mock_lock):
        """Returns 409 when the submission is locked after final submit."""
        from submissions.image_views import _handle_delete

        mock_get.return_value = MagicMock()
        lock_resp = MagicMock(status_code=409)
        mock_lock.return_value = lock_resp

        request = _mock_request(method="DELETE")
        response = _handle_delete(request, 1, "img-id")

        assert response is lock_resp

    @patch("submissions.image_views.SubmissionImage")
    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_DELETE"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_returns_404_when_image_not_found(self, mock_get, mock_can, mock_lock, mock_img):
        """Returns 404 when the image to delete does not exist."""
        from submissions.image_views import _handle_delete

        mock_get.return_value = MagicMock()
        mock_img.objects.filter.return_value.exclude.return_value.first.return_value = None

        request = _mock_request(method="DELETE")
        response = _handle_delete(request, 1, "img-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("submissions.image_views.complete_audit")
    @patch("submissions.image_views.log_audit", return_value=1)
    @patch("submissions.image_views.get_client_ip", return_value="127.0.0.1")
    @patch("submissions.image_views.soft_delete_image")
    @patch("submissions.image_views.SubmissionImage")
    @patch("submissions.image_views._check_post_submit_lock", return_value=None)
    @patch("submissions.image_views._can_mutate_images", return_value=(True, "IMAGE_DELETE"))
    @patch("submissions.image_views._get_submission_with_assignment")
    def test_successful_delete(
        self, mock_get, mock_can, mock_lock, mock_img,
        mock_soft_delete, mock_ip, mock_log, mock_complete
    ):
        """Returns 204 and soft-deletes the image on successful deletion."""
        from submissions.image_views import _handle_delete

        mock_get.return_value = MagicMock()
        image = MagicMock()
        image.id = "uuid-123"
        image.original_filename = "test.jpg"
        image.sha256_hash = "abc123"
        mock_img.objects.filter.return_value.exclude.return_value.first.return_value = image

        request = _mock_request(method="DELETE")
        response = _handle_delete(request, 1, "img-id")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_soft_delete.assert_called_once_with(image)
