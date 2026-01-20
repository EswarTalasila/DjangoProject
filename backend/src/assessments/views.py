"""
Assessment management API endpoints (admin only for write operations).

Assessments are templates containing questions that can be assigned to
courses. Only admins can create/modify assessments; teachers can view and
assign them to their courses.

Question Types Supported:
    - TEXT: Free-text response
    - MULTIPLE_CHOICE: Select from options
    - SCALE: Numeric rating (1-5, etc.)
    - LIKERT: Agreement scale
    - MOOD_METER: Emotional state grid

Endpoints:
    GET/POST /api/v1/assessments           - List or create assessments
    GET/PUT/DELETE /api/v1/assessments/{id} - Assessment detail/update/delete
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role
from assignments.models import Assignment
from core.errors import error_response
from core.permissions import IsAdmin, IsTeacherOrAdmin, primary_role
from courses.models import Enrollment

from .models import Assessment
from .serializers import AssessmentSerializer
from .services import (
    assessment_to_dto,
    create_assessment,
    delete_assessment,
    list_assessments,
    update_assessment,
)


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAdmin])
def list_or_create(request):
    """
    List all assessments (GET) or create a new one (POST, admin only).

    GET: Returns all assessments for teachers to browse and assign.
    POST: Creates a new assessment template (admin only).

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
        POST 403: Forbidden if not admin
    """
    if request.method == "POST":
        if not IsAdmin().has_permission(request, None):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = AssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = create_assessment(request.user, serializer.validated_data)
        return Response(assessment_to_dto(assessment), status=status.HTTP_201_CREATED)

    assessments = list_assessments()
    return Response([assessment_to_dto(a) for a in assessments], status=status.HTTP_200_OK)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def detail(request, assessment_id: int):
    """
    Get, update, or delete a specific assessment.

    GET: Returns assessment with all questions. Students can only view
    assessments assigned to courses they're enrolled in.
    PUT: Updates assessment (admin only). Note: updating after submissions
    exist may corrupt historical data (issue #25).
    DELETE: Removes assessment (admin only).

    Args:
        assessment_id: Database ID of the assessment (path parameter)

    Returns:
        GET 200: Assessment DTO with questions
        PUT 200: Updated assessment DTO
        DELETE 200: "Assessment deleted successfully."
        403: Forbidden based on role/permission
        404: "Assessment not found"
    """
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        return Response("Assessment not found", status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        role = primary_role(request.user)
        if role == Role.STUDENT:
            course_ids = Enrollment.objects.filter(student_profile__user=request.user).values_list(
                "course_id", flat=True
            )
            allowed = Assignment.objects.filter(
                assessment_id=assessment.id,
                course_id__in=course_ids,
            ).exists()
            if not allowed:
                return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(assessment_to_dto(assessment), status=status.HTTP_200_OK)

    if request.method == "PUT":
        if not IsAdmin().has_permission(request, None):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = AssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_assessment(assessment, serializer.validated_data)
        except ValueError as exc:
            return error_response(exc)
        return Response(assessment_to_dto(updated), status=status.HTTP_200_OK)

    if not IsAdmin().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    delete_assessment(assessment)
    return Response("Assessment deleted successfully.", status=status.HTTP_200_OK)
