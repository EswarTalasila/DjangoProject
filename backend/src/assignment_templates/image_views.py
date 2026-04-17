"""Question image upload/serve/delete API endpoints."""

import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role
from assignments.models import Assignment
from core.media.services import ImageValidationError
from core.media.storage import get_storage_backend
from core.permissions import IsResearcherOrAdmin, has_role
from courses.models import Enrollment, EnrollmentStatus
from courses.services import can_view_course

from .image_services import (
    parse_question_image,
    question_image_to_dto,
    remove_question_image,
    upload_question_image,
)
from .models import AssignmentTemplate, Question

logger = logging.getLogger(__name__)


def _assessment_is_locked(assignment_template: AssignmentTemplate) -> bool:
    """Return True when assignments reference the assignment_template."""
    return Assignment.objects.filter(assignment_template=assignment_template).exists()


def _can_read_question_image(user, question: Question) -> bool:
    """Allow access for researcher/admin or users with assignment-level access."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or has_role(user, Role.RESEARCHER):
        return True

    assignments = Assignment.objects.select_related("course").filter(
        assignment_template_id=question.assignment_template_id
    )

    if has_role(user, Role.TEACHER):
        return any(
            assignment.course_id is not None and can_view_course(user, assignment.course)
            for assignment in assignments
        )

    if has_role(user, Role.STUDENT):
        return any(
            assignment.course_id is not None
            and Enrollment.objects.filter(
                course_id=assignment.course_id,
                student_profile__user=user,
                status=EnrollmentStatus.ACTIVE,
            ).exists()
            for assignment in assignments
        )

    return False


def _find_question_by_storage_key(storage_key: str) -> Question | None:
    """Find the question that owns the exact storage key."""
    lookup_fragment = f'"storageKey": "{storage_key}"'
    candidates = Question.objects.filter(image__contains=lookup_fragment)
    for question in candidates:
        meta = parse_question_image(question)
        if meta and meta.get("storageKey") == storage_key:
            return question
    return None


# ---------------------------------------------------------------------------
# POST / DELETE  /api/v1/assignment-templates/{assignment_template_id}/questions/{question_id}/image
# ---------------------------------------------------------------------------


@api_view(["POST", "DELETE"])
@permission_classes([IsResearcherOrAdmin])
def upload_or_delete(request, assignment_template_id: int, question_id: int):
    """Upload (POST) or remove (DELETE) the image for a question."""
    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        return Response(
            {"detail": "AssignmentTemplate not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if _assessment_is_locked(assignment_template):
        return Response(
            {"detail": "Cannot modify assignment template referenced by assignments"},
            status=status.HTTP_409_CONFLICT,
        )

    question = Question.objects.filter(
        id=question_id, assignment_template=assignment_template
    ).first()
    if not question:
        return Response(
            {"detail": "Question not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "POST":
        return _handle_upload(request, question)
    return _handle_delete(request, question)


def _handle_upload(request, question: Question):
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"detail": "No file provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        dto = upload_question_image(
            question=question,
            file=file,
            uploader_id=request.user.id,
        )
    except ImageValidationError as exc:
        return Response({"detail": str(exc)}, status=exc.status_code)
    except Exception:
        logger.exception("Unexpected error during question image upload")
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(dto, status=status.HTTP_201_CREATED)


def _handle_delete(request, question: Question):
    if not parse_question_image(question):
        return Response(
            {"detail": "No image attached"},
            status=status.HTTP_404_NOT_FOUND,
        )

    remove_question_image(question)
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# GET  /api/v1/assignment-templates/images/<path:storage_key>
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def serve_image(request, storage_key: str):
    """Serve a question image blob by storage key."""
    question = _find_question_by_storage_key(storage_key)
    if not question:
        return Response(
            {"detail": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not _can_read_question_image(request.user, question):
        return Response(
            {"detail": "Forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )

    meta = parse_question_image(question)
    if not meta or meta.get("storageKey") != storage_key:
        return Response(
            {"detail": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    backend = get_storage_backend()
    try:
        data = backend.retrieve(storage_key)
    except Exception:
        return Response(
            {"detail": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    mime_type = meta.get("mimeType", "application/octet-stream")
    response = HttpResponse(data, content_type=mime_type)
    response["Cache-Control"] = "private, max-age=3600"
    response["Content-Disposition"] = "inline"
    return response
