"""
Assignment template management API endpoints.

Assignment templates contain reusable questions that can later be assigned to
courses. Researchers and admins can create or modify them; teachers can view
published templates for assignment creation.
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
from core.parsers import parse_include_archived
from core.permissions import IsResearcherOrAdmin, IsTeacherOrAbove

from .models import AssignmentTemplate, AssignmentTemplateStatus
from .serializers import AssignmentTemplateSerializer
from .services import (
    AssignmentTemplateReferencedError,
    _assignment_template_with_related,
    archive_assignment_template,
    assignment_template_to_dto,
    create_assignment_template,
    create_assignment_template_draft,
    delete_assignment_template_draft,
    list_assignment_templates,
    publish_assignment_template,
    purge_assignment_template,
    restore_assignment_template,
    update_assignment_template,
)


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def list_or_create(request):
    """List assignment templates or create a new one."""
    if request.method == "POST":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if request.query_params.get("draft", "").lower() == "true":
            assignment_template = create_assignment_template_draft(request.user)
            assignment_template = _assignment_template_with_related(assignment_template.id)
            return Response(
                assignment_template_to_dto(assignment_template).model_dump(),
                status=status.HTTP_201_CREATED,
            )

        serializer = AssignmentTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment_template = create_assignment_template(
                request.user,
                serializer.validated_data,
            )
        except ValueError as exc:
            return error_response(exc)

        assignment_template = _assignment_template_with_related(assignment_template.id)
        return Response(
            assignment_template_to_dto(assignment_template).model_dump(),
            status=status.HTTP_201_CREATED,
        )

    include_archived, include_archived_error = parse_include_archived(request)
    if include_archived_error is not None:
        return include_archived_error

    include_drafts = IsResearcherOrAdmin().has_permission(request, None)
    assignment_templates = list_assignment_templates(
        include_archived=include_archived,
        include_drafts=include_drafts,
    )
    return paginate(
        assignment_templates,
        request,
        transform_fn=lambda item: assignment_template_to_dto(item).model_dump(),
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def detail(request, assignment_template_id: int):
    """Get, update, or delete a specific assignment template."""
    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        return Response(
            {"detail": "AssignmentTemplate not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        assignment_template = _assignment_template_with_related(assignment_template_id)
        return Response(
            assignment_template_to_dto(assignment_template).model_dump(),
            status=status.HTTP_200_OK,
        )

    if request.method == "PATCH":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = AssignmentTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_assignment_template(
                assignment_template,
                serializer.validated_data,
            )
        except AssignmentTemplateReferencedError as exc:
            return error_response(exc, status_code=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return error_response(exc)
        updated = _assignment_template_with_related(updated.id)
        return Response(
            assignment_template_to_dto(updated).model_dump(),
            status=status.HTTP_200_OK,
        )

    if not IsResearcherOrAdmin().has_permission(request, None):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if assignment_template.status == AssignmentTemplateStatus.DRAFT:
        try:
            delete_assignment_template_draft(assignment_template)
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.query_params.get("purge", "").lower() == "true":
        audit_id = log_audit(
            actor=request.user,
            action=AuditAction.PURGE,
            target_resource_type="AssignmentTemplate",
            target_resource_id=assignment_template.id,
            old_value={"status": assignment_template.status},
            new_value={"status": "PURGED"},
            ip_address=get_client_ip(request),
        )
        if not request.user.is_staff:
            complete_audit(audit_id, AuditOutcome.DENIED)
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            purge_assignment_template(assignment_template)
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
def archive(request, assignment_template_id: int):
    """Archive an assignment template."""
    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        return Response(
            {"detail": "AssignmentTemplate not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.ARCHIVE,
        target_resource_type="AssignmentTemplate",
        target_resource_id=assignment_template.id,
        old_value={"status": assignment_template.status},
        new_value={"status": "ARCHIVED"},
        ip_address=get_client_ip(request),
    )
    if not IsResearcherOrAdmin().has_permission(request, None):
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        assignment_template = archive_assignment_template(request.user, assignment_template)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    assignment_template = _assignment_template_with_related(assignment_template.id)
    return Response(
        assignment_template_to_dto(assignment_template).model_dump(),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def restore(request, assignment_template_id: int):
    """Restore an archived assignment template."""
    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        return Response(
            {"detail": "AssignmentTemplate not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.RESTORE,
        target_resource_type="AssignmentTemplate",
        target_resource_id=assignment_template.id,
        old_value={"status": assignment_template.status},
        new_value={"status": "ACTIVE"},
        ip_address=get_client_ip(request),
    )
    if not IsResearcherOrAdmin().has_permission(request, None):
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        assignment_template = restore_assignment_template(request.user, assignment_template)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    assignment_template = _assignment_template_with_related(assignment_template.id)
    return Response(
        assignment_template_to_dto(assignment_template).model_dump(),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def publish(request, assignment_template_id: int):
    """Publish a draft assignment template."""
    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        return Response(
            {"detail": "AssignmentTemplate not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not IsResearcherOrAdmin().has_permission(request, None):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        assignment_template = publish_assignment_template(assignment_template)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)
    assignment_template = _assignment_template_with_related(assignment_template.id)
    return Response(
        assignment_template_to_dto(assignment_template).model_dump(),
        status=status.HTTP_200_OK,
    )
