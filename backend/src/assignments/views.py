"""
Assignment management API endpoints.

Endpoints:
    POST   /api/v1/assignments               - Create new assignment
    GET    /api/v1/assignments/{id}          - Get assignment detail
    PATCH  /api/v1/assignments/{id}          - Update assignment scheduling
    DELETE /api/v1/assignments/{id}          - Delete assignment
    GET    /api/v1/assignments/{id}/template - Get assignment template
    POST   /api/v1/assignments/{id}/archive  - Archive assignment
    GET    /api/v1/assignments/courses/{id}  - List assignments for course
    GET    /api/v1/assignments/users/{id}    - List assignments for user
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from assignment_templates.services import (
    _assignment_template_with_related,
    assignment_template_to_dto,
)
from core.audit import complete_audit, get_client_ip, log_audit
from core.errors import error_response
from core.models import AuditAction, AuditOutcome
from core.pagination import paginate
from core.parsers import parse_include_archived
from core.permissions import IsTeacher, IsTeacherOrAbove, has_role, primary_role
from courses.models import Enrollment, EnrollmentStatus
from courses.services import can_view_course

from .serializers import AssignmentSerializer, AssignmentUpdateSerializer
from .services import (
    ConflictError,
    ForbiddenError,
    archive_assignment,
    assignment_to_dto,
    create_assignment,
    get_assignment,
    list_by_course,
    list_for_user,
    purge_assignment,
    restore_assignment,
    update_assignment,
)


def _can_read_assignment(user: User, assignment) -> bool:
    """Apply assignment access rules for the current user."""
    role = primary_role(user)
    if role == Role.STUDENT:
        if assignment.course_id is None:
            return False
        return Enrollment.objects.filter(
            course_id=assignment.course_id,
            student_profile__user=user,
            status=EnrollmentStatus.ACTIVE,
        ).exists()
    if role == Role.TEACHER and assignment.course_id is not None:
        return can_view_course(user, assignment.course)
    return True


@api_view(["POST"])
@permission_classes([IsTeacher])
def create(request):
    """Create a new assignment from an assignment template."""
    serializer = AssignmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        assignment = create_assignment(request.user, serializer.validated_data)
    except ForbiddenError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)
    return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def detail(request, assignment_id: int):
    """Get, update, or delete a specific assignment."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not _can_read_assignment(request.user, assignment):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)

    if request.method == "PATCH":
        if not has_role(request.user, Role.TEACHER):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = AssignmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = update_assignment(assignment, request.user, serializer.validated_data)
        except ForbiddenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return error_response(exc)
        return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)

    if request.query_params.get("purge", "").lower() == "true":
        audit_id = log_audit(
            actor=request.user,
            action=AuditAction.PURGE,
            target_resource_type="Assignment",
            target_resource_id=assignment.id,
            old_value={"status": assignment.status},
            new_value={"status": "PURGED"},
            ip_address=get_client_ip(request),
        )
        if not request.user.is_staff:
            complete_audit(audit_id, AuditOutcome.DENIED)
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            purge_assignment(assignment)
        except ConflictError as exc:
            complete_audit(audit_id, AuditOutcome.FAILURE)
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        complete_audit(audit_id, AuditOutcome.SUCCESS)
        return Response(status=status.HTTP_204_NO_CONTENT)

    if not request.user.is_staff and assignment.created_by_id != request.user.id:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    detail = (
        "Assignment is archived. Use DELETE ?purge=true to permanently remove it."
        if assignment.status == "ARCHIVED"
        else "Use POST /archive to archive first. Permanent deletion requires DELETE ?purge=true on an archived assignment."
    )
    return Response({"detail": detail}, status=status.HTTP_409_CONFLICT)


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def list_course(request, course_id: int):
    """List all assignments for a specific course."""
    role = primary_role(request.user)
    if role == Role.TEACHER:
        from courses.models import Course

        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        if not can_view_course(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    include_archived, include_archived_error = parse_include_archived(request)
    if include_archived_error is not None:
        return include_archived_error
    assignments = list_by_course(course_id, include_archived=include_archived)
    return paginate(assignments, request, transform_fn=lambda item: assignment_to_dto(item).model_dump())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user(request, user_id: int):
    """List all assignments for a specific user."""
    if (
        request.user.id != user_id
        and not request.user.is_staff
        and not has_role(request.user, Role.RESEARCHER)
    ):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    assignments = list_for_user(target)
    return paginate(assignments, request, transform_fn=lambda item: assignment_to_dto(item).model_dump())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive(request, assignment_id: int):
    """Archive an assignment."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.ARCHIVE,
        target_resource_type="Assignment",
        target_resource_id=assignment.id,
        old_value={"status": assignment.status},
        new_value={"status": "ARCHIVED"},
        ip_address=get_client_ip(request),
    )
    try:
        assignment = archive_assignment(request.user, assignment)
    except PermissionError as exc:
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def restore(request, assignment_id: int):
    """Restore an archived assignment."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.RESTORE,
        target_resource_type="Assignment",
        target_resource_id=assignment.id,
        old_value={"status": assignment.status},
        new_value={"status": "ACTIVE"},
        ip_address=get_client_ip(request),
    )
    try:
        assignment = restore_assignment(request.user, assignment)
    except PermissionError as exc:
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_assignment_template(request, assignment_id: int):
    """Get the template attached to an assignment using assignment access rules."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_read_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    assignment_template = _assignment_template_with_related(assignment.assignment_template_id)
    return Response(
        assignment_template_to_dto(assignment_template).model_dump(),
        status=status.HTTP_200_OK,
    )
