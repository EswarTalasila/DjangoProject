"""
Assessment management API endpoints.

Assessments are templates containing questions that can be assigned to
courses. Researchers and admins can create/modify assessments; teachers
can view and assign them to their courses.

Question Types Supported:
    - MULTIPLE_CHOICE: Select from options
    - SHORT_ANSWER: Free-text response
    - NUMBER_SCALE: Numeric rating

Endpoints:
    GET/POST /api/v1/assessments           - List or create assessments
    GET/PATCH/DELETE /api/v1/assessments/{id} - Assessment detail/update/delete
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.audit import complete_audit, get_client_ip, log_audit
from core.errors import error_response
from core.lifecycle import ConflictError
from core.models import AuditAction, AuditOutcome
from core.pagination import paginate
from core.permissions import IsResearcherOrAdmin, IsTeacherOrAbove

from .models import Assessment
from .serializers import AssessmentSerializer
from .services import (
    AssessmentReferencedError,
    _assessment_with_related,
    archive_assessment,
    assessment_to_dto,
    create_assessment,
    list_assessments,
    purge_assessment,
    restore_assessment,
    update_assessment,
)


def _parse_include_archived(request):
    raw = request.query_params.get("includeArchived")
    if raw is None or raw == "":
        return False, None
    value = raw.lower()
    if value not in {"true", "false"}:
        return (
            None,
            Response(
                {"detail": "includeArchived must be true or false"},
                status=status.HTTP_400_BAD_REQUEST,
            ),
        )
    return value == "true", None


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
        try:
            assessment = create_assessment(request.user, serializer.validated_data)
        except ValueError as exc:
            return error_response(exc)
        return Response(assessment_to_dto(assessment).model_dump(), status=status.HTTP_201_CREATED)

    include_archived, include_archived_error = _parse_include_archived(request)
    if include_archived_error is not None:
        return include_archived_error
    assessments = list_assessments(include_archived=include_archived)
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
        # Re-fetch with prefetches for efficient DTO serialization.
        assessment = _assessment_with_related(assessment_id)
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

    # DELETE with ?purge=true — admin-only hard delete of archived assessment
    if request.query_params.get("purge", "").lower() == "true":
        audit_id = log_audit(
            actor=request.user,
            action=AuditAction.PURGE,
            target_resource_type="Assessment",
            target_resource_id=assessment.id,
            old_value={"status": assessment.status},
            new_value={"status": "PURGED"},
            ip_address=get_client_ip(request),
        )
        if not request.user.is_staff:
            complete_audit(audit_id, AuditOutcome.DENIED)
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            purge_assessment(assessment)
        except ConflictError as exc:
            complete_audit(audit_id, AuditOutcome.FAILURE)
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        complete_audit(audit_id, AuditOutcome.SUCCESS)
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(
        {"detail": "Use POST /archive to archive, or DELETE ?purge=true to hard-delete."},
        status=status.HTTP_409_CONFLICT,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive(request, assessment_id: int):
    """Archive an assessment (ARCH-UC-01). Researcher/admin only."""
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        return Response({"detail": "Assessment not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.ARCHIVE,
        target_resource_type="Assessment",
        target_resource_id=assessment.id,
        old_value={"status": assessment.status},
        new_value={"status": "ARCHIVED"},
        ip_address=get_client_ip(request),
    )
    if not IsResearcherOrAdmin().has_permission(request, None):
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        assessment = archive_assessment(request.user, assessment)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(assessment_to_dto(assessment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def restore(request, assessment_id: int):
    """Restore an archived assessment (ARCH-UC-04). Researcher/admin only."""
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        return Response({"detail": "Assessment not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.RESTORE,
        target_resource_type="Assessment",
        target_resource_id=assessment.id,
        old_value={"status": assessment.status},
        new_value={"status": "ACTIVE"},
        ip_address=get_client_ip(request),
    )
    if not IsResearcherOrAdmin().has_permission(request, None):
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        assessment = restore_assessment(request.user, assessment)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(assessment_to_dto(assessment).model_dump(), status=status.HTTP_200_OK)
