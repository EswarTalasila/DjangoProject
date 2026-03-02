"""
Assessment management API endpoints.

Assessments are templates containing questions that can be assigned to
courses. Researchers and admins can create/modify assessments; teachers
can view and assign them to their courses.

Question Types Supported:
    - TEXT: Free-text response
    - MULTIPLE_CHOICE: Select from options
    - SCALE: Numeric rating (1-5, etc.)
    - LIKERT: Agreement scale
    - MOOD_METER: Emotional state grid

Endpoints:
    GET/POST /api/v1/assessments           - List or create assessments
    GET/PATCH/DELETE /api/v1/assessments/{id} - Assessment detail/update/delete
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.errors import error_response
from core.pagination import paginate
from core.permissions import IsResearcherOrAdmin, IsTeacherOrAbove

from .models import Assessment
from .serializers import AssessmentSerializer
from .services import (
    AssessmentReferencedError,
    assessment_to_dto,
    create_assessment,
    delete_assessment,
    list_assessments,
    update_assessment,
)


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def list_or_create(request):
    """
    List all assessments (GET) or create a new one (POST, researcher/admin).

    GET: Returns all assessments for teachers to browse and assign.
    POST: Creates a new assessment template (researcher or admin).

    Request Body (POST):
        {
            "title": "Assessment Title",
            "description": "Optional description",
            "gradingMode": "MANUAL|AUTO",
            "questions": [
                {"type": "TEXT", "text": "Question text", "required": true},
                ...
            ]
        }

    Returns:
        GET 200: Array of assessment DTOs
        POST 201: Created assessment DTO
        POST 403: Forbidden if not researcher or admin
    """
    if request.method == "POST":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = AssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = create_assessment(request.user, serializer.validated_data)
        return Response(assessment_to_dto(assessment).model_dump(), status=status.HTTP_201_CREATED)

    assessments = list_assessments()
    return paginate(assessments, request, transform_fn=lambda a: assessment_to_dto(a).model_dump())


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def detail(request, assessment_id: int):
    """
    Get, update, or delete a specific assessment.

    GET: Returns assessment with all questions (teacher/researcher/admin).
    PATCH: Updates assessment (researcher/admin only, blocked if referenced).
    DELETE: Removes assessment (researcher/admin only, blocked if referenced).

    Args:
        assessment_id: Database ID of the assessment (path parameter)

    Returns:
        GET 200: Assessment DTO with questions
        PATCH 200: Updated assessment DTO
        DELETE 204: No content on success
        403: Forbidden based on role/permission
        404: "Assessment not found"
        409: Mutation blocked by assignment references
    """
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        return Response({"detail": "Assessment not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(assessment_to_dto(assessment).model_dump(), status=status.HTTP_200_OK)

    if request.method == "PATCH":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = AssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_assessment(assessment, serializer.validated_data)
        except AssessmentReferencedError as exc:
            return error_response(exc, status_code=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return error_response(exc)
        return Response(assessment_to_dto(updated).model_dump(), status=status.HTTP_200_OK)

    if not IsResearcherOrAdmin().has_permission(request, None):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        delete_assessment(assessment)
    except AssessmentReferencedError as exc:
        return error_response(exc, status_code=status.HTTP_409_CONFLICT)
    return Response(status=status.HTTP_204_NO_CONTENT)
