"""
Assignment management API endpoints.

Endpoints:
    POST   /api/v1/assignments               - Create new assignment
    GET    /api/v1/assignments/{id}          - Get assignment detail
    PATCH  /api/v1/assignments/{id}          - Update assignment scheduling
    DELETE /api/v1/assignments/{id}          - Delete assignment
    GET    /api/v1/assignments/{id}/template - Get assignment template
    POST   /api/v1/assignments/{id}/archive  - Archive assignment
    GET    /api/v1/assignments/{id}/archive-bundle - Get archive bundle metadata
    POST   /api/v1/assignments/{id}/archive-bundle - Generate archive bundle
    GET    /api/v1/assignments/{id}/archive-bundle/download - Download archive bundle
    GET    /api/v1/assignments/courses/{id}  - List assignments for course
    GET    /api/v1/assignments/users/{id}    - List assignments for user
"""

from pathlib import Path

from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from core.audit import complete_audit, get_client_ip, log_audit
from core.errors import error_response
from core.models import AuditAction, AuditOutcome
from core.pagination import paginate
from core.parsers import parse_include_archived
from core.permissions import IsTeacher, IsTeacherOrAbove, has_role, primary_role
from courses.models import Enrollment, EnrollmentStatus
from courses.services import can_view_course

from .serializers import (
    AssignmentOrderedIdsSerializer,
    AssignmentQuestionCreateSerializer,
    AssignmentQuestionUpdateSerializer,
    AssignmentSerializer,
    AssignmentTeacherCriterionCreateSerializer,
    AssignmentTeacherCriterionLevelCreateSerializer,
    AssignmentTeacherCriterionLevelUpdateSerializer,
    AssignmentTeacherCriterionUpdateSerializer,
    AssignmentUpdateSerializer,
)
from .services import (
    ConflictError,
    ForbiddenError,
    add_assignment_question,
    add_assignment_teacher_criterion,
    add_assignment_teacher_criterion_level,
    archive_assignment,
    assignment_archive_artifact_to_dict,
    assignment_content_to_dto,
    assignment_to_dto,
    create_assignment,
    delete_assignment_question,
    delete_assignment_teacher_criterion,
    delete_assignment_teacher_criterion_level,
    generate_assignment_archive_artifact,
    get_assignment,
    get_assignment_archive_artifact,
    get_assignment_with_content,
    list_by_course,
    list_for_user,
    list_reusable_question_images,
    purge_assignment,
    reorder_assignment_questions,
    reorder_assignment_teacher_criteria,
    reorder_assignment_teacher_criterion_levels,
    restore_assignment,
    update_assignment,
    update_assignment_question,
    update_assignment_teacher_criterion,
    update_assignment_teacher_criterion_level,
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


def _parse_identifiable(value: str | None) -> bool | None:
    """Parse an optional identifiable=true/false query parameter."""
    if value is None or value == "":
        return None
    lowered = value.lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise ValueError("identifiable must be true or false.")


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
    """Get the effective assignment content snapshot using assignment access rules."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_read_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_assignment_question(request, assignment_id: int):
    """Add a teacher-authored question to an assignment-local content snapshot."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if assignment.status == "ARCHIVED":
        return Response(
            {"detail": "Archived assignments cannot be extended."},
            status=status.HTTP_409_CONFLICT,
        )
    serializer = AssignmentQuestionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        question = add_assignment_question(assignment, request.user, serializer.validated_data)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def question_detail(request, assignment_id: int, question_id: int):
    """Update or delete a teacher-authored assignment-local question."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        if request.method == "PATCH":
            serializer = AssignmentQuestionUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            update_assignment_question(assignment, question_id, request.user, serializer.validated_data)
        else:
            delete_assignment_question(assignment, question_id, request.user)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)

    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reorder_questions(request, assignment_id: int):
    """Reorder teacher-authored assignment-local questions."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AssignmentOrderedIdsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        reorder_assignment_questions(assignment, request.user, serializer.validated_data["orderedIds"])
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_assignment_teacher_criterion(request, assignment_id: int):
    """Add a teacher-authored criterion to an assignment-local rubric overlay."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if assignment.status == "ARCHIVED":
        return Response(
            {"detail": "Archived assignments cannot be extended."},
            status=status.HTTP_409_CONFLICT,
        )
    serializer = AssignmentTeacherCriterionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        add_assignment_teacher_criterion(assignment, request.user, serializer.validated_data)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def teacher_criterion_detail(request, assignment_id: int, criterion_id: int):
    """Update or delete a teacher-authored assignment-local rubric criterion."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        if request.method == "PATCH":
            serializer = AssignmentTeacherCriterionUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            update_assignment_teacher_criterion(
                assignment,
                criterion_id,
                request.user,
                serializer.validated_data,
            )
        else:
            delete_assignment_teacher_criterion(assignment, criterion_id, request.user)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)

    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reorder_teacher_criteria(request, assignment_id: int):
    """Reorder teacher-authored assignment-local rubric criteria."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AssignmentOrderedIdsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        reorder_assignment_teacher_criteria(
            assignment,
            request.user,
            serializer.validated_data["orderedIds"],
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_teacher_criterion_level(request, assignment_id: int, criterion_id: int):
    """Add a teacher-authored rubric level to a teacher-owned criterion."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AssignmentTeacherCriterionLevelCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        add_assignment_teacher_criterion_level(
            assignment,
            criterion_id,
            request.user,
            serializer.validated_data,
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def teacher_criterion_level_detail(
    request,
    assignment_id: int,
    criterion_id: int,
    level_id: int,
):
    """Update or delete a teacher-authored rubric level."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        if request.method == "PATCH":
            serializer = AssignmentTeacherCriterionLevelUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            update_assignment_teacher_criterion_level(
                assignment,
                criterion_id,
                level_id,
                request.user,
                serializer.validated_data,
            )
        else:
            delete_assignment_teacher_criterion_level(
                assignment,
                criterion_id,
                level_id,
                request.user,
            )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)

    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reorder_teacher_criterion_levels(request, assignment_id: int, criterion_id: int):
    """Reorder teacher-authored levels on a teacher-owned criterion."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AssignmentOrderedIdsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        reorder_assignment_teacher_criterion_levels(
            assignment,
            criterion_id,
            request.user,
            serializer.validated_data["orderedIds"],
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return error_response(exc)
    assignment = get_assignment_with_content(assignment_id)
    return Response(assignment_content_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reusable_images(request, assignment_id: int):
    """List reusable question images visible from the assignment context."""
    assignment = get_assignment_with_content(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_read_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(list_reusable_question_images(assignment), status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def archive_bundle(request, assignment_id: int):
    """Get or generate assignment archive bundle metadata."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        identifiable = _parse_identifiable(request.query_params.get("identifiable"))
    except ValueError as exc:
        return error_response(exc)

    try:
        if request.method == "POST":
            artifact = generate_assignment_archive_artifact(
                assignment,
                request.user,
                identifiable=identifiable,
            )
        else:
            artifact = get_assignment_archive_artifact(
                assignment,
                request.user,
                identifiable=identifiable,
            )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    if artifact is None:
        return Response({"detail": "Archive bundle not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        assignment_archive_artifact_to_dict(artifact),
        status=status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_archive_bundle(request, assignment_id: int):
    """Download an existing assignment archive bundle."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        identifiable = _parse_identifiable(request.query_params.get("identifiable"))
    except ValueError as exc:
        return error_response(exc)

    try:
        artifact = get_assignment_archive_artifact(
            assignment,
            request.user,
            identifiable=identifiable,
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    if artifact is None:
        return Response({"detail": "Archive bundle not found"}, status=status.HTTP_404_NOT_FOUND)

    path = Path(artifact.file_path)
    if not path.exists():
        return Response({"detail": "Archive bundle file missing"}, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename=artifact.filename,
        content_type="application/zip",
    )
