"""
Assignment management API endpoints.

Endpoints:
    POST   /api/v1/assignments              - Create new assignment
    GET    /api/v1/assignments/{id}          - Get assignment detail
    PATCH  /api/v1/assignments/{id}          - Update assignment scheduling
    DELETE /api/v1/assignments/{id}          - Delete assignment
    GET    /api/v1/assignments/{id}/template - Get assignment assessment template
    POST   /api/v1/assignments/{id}/archive  - Archive assignment
    GET    /api/v1/assignments/courses/{id}  - List assignments for course
    GET    /api/v1/assignments/users/{id}    - List assignments for user
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from assessments.services import assessment_to_dto as assessment_template_to_dto
from core.errors import error_response
from core.pagination import paginate
from core.permissions import IsTeacher, IsTeacherOrAbove, has_role, primary_role
from courses.models import Enrollment
from courses.services import can_view_course

from .serializers import AssignmentSerializer, AssignmentUpdateSerializer
from .services import (
    ConflictError,
    ForbiddenError,
    archive_assignment,
    assignment_to_dto,
    create_assignment,
    delete_assignment,
    get_assignment,
    list_by_course,
    list_for_user,
    update_assignment,
)


def _can_read_assignment(user: User, assignment) -> bool:
    role = primary_role(user)
    if role == Role.STUDENT:
        if assignment.course_id is None:
            return False
        return Enrollment.objects.filter(
            course_id=assignment.course_id,
            student_profile__user=user,
        ).exists()
    if role == Role.TEACHER and assignment.course_id is not None:
        return can_view_course(user, assignment.course)
    return True


@api_view(["POST"])
@permission_classes([IsTeacher])
def create(request):
    """
    Create a new assignment from an assessment.

    Returns:
        201: Assignment DTO
        400: Validation error (invalid payload, scheduling, deprecated audience type)
        403: Forbidden (not teacher, or does not own course)
        409: Assessment is archived
    """
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
    """
    Get, update, or delete a specific assignment.

    GET: Returns assignment details with role-based access control.
    PATCH: Updates scheduling fields (creator-only).
    DELETE: Removes assignment if no submissions progressed (creator-only).
    """
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

    # DELETE
    if not has_role(request.user, Role.TEACHER):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        delete_assignment(assignment, request.user)
    except ForbiddenError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def list_course(request, course_id: int):
    """
    List all assignments for a specific course.

    ADMIN/RESEARCHER: can list any course's assignments.
    TEACHER: must own the course.
    """
    role = primary_role(request.user)
    if role == Role.TEACHER:
        from courses.models import Course

        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        if not can_view_course(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    assignments = list_by_course(course_id)
    return paginate(assignments, request, transform_fn=lambda a: assignment_to_dto(a).model_dump())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user(request, user_id: int):
    """
    List all assignments for a specific user.

    For students: Returns ACTIVE assignments from enrolled courses within time window.
    For teachers: Returns assignments they created.
    Researchers and admins can view assignments for any user.
    """
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
    return paginate(assignments, request, transform_fn=lambda a: assignment_to_dto(a).model_dump())


@api_view(["POST"])
@permission_classes([IsTeacher])
def archive(request, assignment_id: int):
    """
    Archive an assignment.

    Returns:
        200: Updated assignment DTO with status=ARCHIVED
        403: Forbidden (not creator)
        404: Assignment not found
        409: Already archived
    """
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        assignment = archive_assignment(assignment, request.user)
    except ForbiddenError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def template(request, assignment_id: int):
    """
    Get the assessment template attached to an assignment using assignment-level access rules.
    """
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response({"detail": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    if not _can_read_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(
        assessment_template_to_dto(assignment.assessment).model_dump(),
        status=status.HTTP_200_OK,
    )
