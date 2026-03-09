"""Image upload/retrieve/delete API endpoints (FR-15 IMG)."""

import logging

from django.http import HttpResponse

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role
from core.audit import complete_audit, get_client_ip, log_audit
from core.models import AuditAction, AuditOutcome
from core.permissions import primary_role

from .image_services import (
    ImageValidationError,
    image_to_dto_dict,
    soft_delete_image,
    upload_image,
)
from .models import ImageStatus, Submission, SubmissionImage, SubmissionStatus
from .views import _can_access_submission, _teacher_owns_assignment

logger = logging.getLogger(__name__)


def _get_submission_with_assignment(submission_id: int) -> Submission | None:
    """Fetch submission with pre-loaded assignment → course → teacher_profile."""
    return (
        Submission.objects.select_related(
            "assignment__course__teacher_profile__user"
        )
        .filter(id=submission_id)
        .first()
    )


def _can_mutate_images(user, submission: Submission) -> tuple[bool, str | None]:
    """Check if user can upload/delete images on this submission.

    Returns (allowed, audit_action).
    - Student who owns the submission: allowed, IMAGE_UPLOAD
    - Teacher who owns the course/assignment: allowed, IMAGE_PROXY_UPLOAD
    - Otherwise: not allowed
    """
    role = primary_role(user)

    if role == Role.STUDENT:
        if submission.student_id == user.id:
            return True, AuditAction.IMAGE_UPLOAD
        return False, None

    if role == Role.TEACHER:
        if _teacher_owns_assignment(user, submission.assignment):
            return True, AuditAction.IMAGE_PROXY_UPLOAD
        return False, None

    return False, None


def _check_post_submit_lock(submission: Submission) -> Response | None:
    """Return 409 if submission is past the mutable window (IMG-CN-08)."""
    if submission.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED):
        return Response(
            {"detail": "Submission already submitted or graded"},
            status=status.HTTP_409_CONFLICT,
        )
    return None


# ---------------------------------------------------------------------------
# POST / GET  /api/v1/submissions/{submission_id}/images
# ---------------------------------------------------------------------------


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def upload_or_list_images(request, submission_id: int):
    """Upload an image (POST) or list images (GET) for a submission."""
    if request.method == "POST":
        return _handle_upload(request, submission_id)
    return _handle_list(request, submission_id)


def _handle_upload(request, submission_id: int):
    """IMG-UC-01 / IMG-UC-02: Upload image to submission."""
    submission = _get_submission_with_assignment(submission_id)
    if not submission:
        return Response(
            {"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Permission gate
    allowed, audit_action = _can_mutate_images(request.user, submission)
    if not allowed:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # Post-submit lock
    lock_resp = _check_post_submit_lock(submission)
    if lock_resp:
        return lock_resp

    # File presence check (IMG-CN-14: 400 for malformed)
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Determine owner (student who owns the submission)
    owner_id = submission.student_id or submission.teacher_id

    # Two-phase audit — phase 1
    audit_id = log_audit(
        actor=request.user,
        action=audit_action,  # type: ignore[arg-type]  # guaranteed non-None after allowed check
        target_resource_type="SubmissionImage",
        target_resource_id=submission_id,
        new_value={"filename": file.name, "submission_id": submission_id},
        ip_address=get_client_ip(request),
    )

    try:
        image = upload_image(
            submission=submission,
            file=file,
            uploader_id=request.user.id,
            owner_id=owner_id,
        )
    except ImageValidationError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=exc.status_code)
    except Exception:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        logger.exception("Unexpected error during image upload")
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Phase 2 — success
    complete_audit(audit_id, AuditOutcome.SUCCESS)

    return Response(image_to_dto_dict(image), status=status.HTTP_201_CREATED)


def _handle_list(request, submission_id: int):
    """IMG-UC-05: List READY images for a submission."""
    submission = _get_submission_with_assignment(submission_id)
    if not submission:
        return Response(
            {"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if not _can_access_submission(request.user, submission):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    images = SubmissionImage.objects.filter(
        submission_id=submission_id,
        status=ImageStatus.READY,
    ).order_by("created_at")

    return Response([image_to_dto_dict(img) for img in images])


# ---------------------------------------------------------------------------
# GET / DELETE  /api/v1/submissions/{submission_id}/images/{image_id}
# ---------------------------------------------------------------------------


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def retrieve_or_delete_image(request, submission_id: int, image_id):
    """Retrieve (GET) or delete (DELETE) a specific image."""
    if request.method == "DELETE":
        return _handle_delete(request, submission_id, image_id)
    return _handle_retrieve(request, submission_id, image_id)


def _handle_retrieve(request, submission_id: int, image_id):
    """IMG-UC-03: Serve image via X-Accel-Redirect (or direct in test)."""
    submission = _get_submission_with_assignment(submission_id)
    if not submission:
        return Response(
            {"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if not _can_access_submission(request.user, submission):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # Only serve READY images — PENDING_SCAN, REJECTED, DELETED all return 404
    image = SubmissionImage.objects.filter(
        id=image_id,
        submission_id=submission_id,
        status=ImageStatus.READY,
    ).first()
    if not image:
        return Response(
            {"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Build response with X-Accel-Redirect for Nginx (IMG-CN-11)
    response = HttpResponse(status=200, content_type=image.mime_type)
    response["X-Accel-Redirect"] = f"/internal/media/{image.storage_key}"
    response["ETag"] = f'"{image.sha256_hash}"'
    response["Last-Modified"] = image.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    response["Cache-Control"] = "private"
    response["Content-Disposition"] = "inline"
    return response


def _handle_delete(request, submission_id: int, image_id):
    """IMG-UC-04: Soft-delete an image."""
    submission = _get_submission_with_assignment(submission_id)
    if not submission:
        return Response(
            {"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Permission gate
    allowed, _ = _can_mutate_images(request.user, submission)
    if not allowed:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # Post-submit lock
    lock_resp = _check_post_submit_lock(submission)
    if lock_resp:
        return lock_resp

    # Find non-deleted image
    image = SubmissionImage.objects.filter(
        id=image_id,
        submission_id=submission_id,
    ).exclude(status=ImageStatus.DELETED).first()
    if not image:
        return Response(
            {"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Two-phase audit
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.IMAGE_DELETE,
        target_resource_type="SubmissionImage",
        target_resource_id=submission_id,
        old_value={
            "image_id": str(image.id),
            "filename": image.original_filename,
            "sha256": image.sha256_hash,
        },
        ip_address=get_client_ip(request),
    )

    soft_delete_image(image)
    complete_audit(audit_id, AuditOutcome.SUCCESS)

    return Response(status=status.HTTP_204_NO_CONTENT)
