"""Assignment question image upload, reuse, delete, and serve endpoints."""

import json
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role
from core.media.models import ImageAsset
from core.media.services import ImageValidationError
from core.media.storage import get_storage_backend
from core.permissions import has_role
from courses.models import Enrollment, EnrollmentStatus
from courses.services import can_view_course

from .image_services import (
    assignment_question_image_to_dto,
    attach_existing_question_image,
    remove_assignment_question_image,
    upload_assignment_question_image,
)
from .models import AssignmentQuestion

logger = logging.getLogger(__name__)


def _can_manage_assignment_question(user, question: AssignmentQuestion) -> bool:
    """Allow mutation for assignment owner or admins only."""
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or question.assignment.created_by_id == user.id)


def _can_read_assignment_question(user, question: AssignmentQuestion) -> bool:
    """Allow reads for admins, researchers, course teachers, and enrolled students."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or has_role(user, Role.RESEARCHER):
        return True
    assignment = question.assignment
    if has_role(user, Role.TEACHER):
        return bool(assignment.course_id and can_view_course(user, assignment.course))
    if has_role(user, Role.STUDENT):
        return bool(
            assignment.course_id
            and Enrollment.objects.filter(
                course_id=assignment.course_id,
                student_profile__user=user,
                status=EnrollmentStatus.ACTIVE,
            ).exists()
        )
    return False


def _find_question_by_storage_key(storage_key: str) -> AssignmentQuestion | None:
    """Find the assignment-owned question snapshot that references the given storage key."""
    candidates = AssignmentQuestion.objects.select_related("assignment__course").filter(
        image__contains=f'"storageKey": "{storage_key}"'
    )
    for question in candidates:
        if not question.image:
            continue
        try:
            payload = json.loads(question.image)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("storageKey") == storage_key:
            return question
    return None


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def upload_or_delete(request, assignment_id: int, question_id: int):
    """Upload or remove an image for a teacher-authored assignment-local question."""
    question = AssignmentQuestion.objects.select_related("assignment").filter(
        id=question_id,
        assignment_id=assignment_id,
    ).first()
    if not question:
        return Response({"detail": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_manage_assignment_question(request.user, question):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if question.assignment.status == "ARCHIVED":
        return Response(
            {"detail": "Archived assignments cannot be extended."},
            status=status.HTTP_409_CONFLICT,
        )
    if question.locked_from_source:
        return Response(
            {"detail": "Cannot replace researcher-provided images on locked template questions."},
            status=status.HTTP_409_CONFLICT,
        )

    if request.method == "DELETE":
        if not question.image:
            return Response({"detail": "No image attached"}, status=status.HTTP_404_NOT_FOUND)
        remove_assignment_question_image(question)
        return Response(status=status.HTTP_204_NO_CONTENT)

    file = request.FILES.get("file")
    if not file:
        return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        dto = upload_assignment_question_image(question, file, uploader_id=request.user.id)
    except ImageValidationError as exc:
        return Response({"detail": str(exc)}, status=exc.status_code)
    except Exception:
        logger.exception("Unexpected error during assignment question image upload")
        return Response({"detail": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(dto, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reuse_image(request, assignment_id: int, question_id: int):
    """Attach a previously uploaded asset to a teacher-authored assignment question."""
    question = AssignmentQuestion.objects.select_related("assignment").filter(
        id=question_id,
        assignment_id=assignment_id,
    ).first()
    if not question:
        return Response({"detail": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_manage_assignment_question(request.user, question):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if question.assignment.status == "ARCHIVED":
        return Response(
            {"detail": "Archived assignments cannot be extended."},
            status=status.HTTP_409_CONFLICT,
        )
    if question.locked_from_source:
        return Response(
            {"detail": "Cannot replace researcher-provided images on locked template questions."},
            status=status.HTTP_409_CONFLICT,
        )

    asset_id = request.data.get("assetId")
    if not asset_id:
        return Response({"detail": "assetId is required"}, status=status.HTTP_400_BAD_REQUEST)
    asset = ImageAsset.objects.filter(id=asset_id).first()
    if not asset:
        return Response({"detail": "Image asset not found"}, status=status.HTTP_404_NOT_FOUND)
    dto = attach_existing_question_image(question, asset)
    return Response(dto, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def serve_image(request, storage_key: str):
    """Serve an assignment question image blob by storage key."""
    question = _find_question_by_storage_key(storage_key)
    if not question:
        return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_read_assignment_question(request.user, question):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    meta = assignment_question_image_to_dto(question)
    if not meta or meta.get("storageKey") != storage_key:
        return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

    backend = get_storage_backend()
    try:
        data = backend.retrieve(storage_key)
    except Exception:
        return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

    response = HttpResponse(data, content_type=meta.get("mimeType", "application/octet-stream"))
    response["Cache-Control"] = "private, max-age=3600"
    response["Content-Disposition"] = "inline"
    return response
