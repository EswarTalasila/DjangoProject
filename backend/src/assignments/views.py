"""
Assignment management API endpoints.

Assignments connect assessments to courses, enabling teachers to distribute
work to students. When an assignment is created, empty submissions are
pre-created for all enrolled students.

Assignment Audience Types:
    - COURSE: Assignment for a specific course (requires courseId)
    - TEACHER: Teacher self-assessment (no course required)

Endpoints:
    POST /api/v1/assignments              - Create new assignment
    GET/DELETE /api/v1/assignments/{id}   - Get or delete assignment
    GET /api/v1/assignments/course/{id}   - List assignments for course
    GET /api/v1/assignments/user/{id}     - List assignments for user
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from core.errors import error_response
from core.permissions import IsTeacher, IsTeacherOrAbove, has_role, primary_role
from courses.models import Enrollment

from .serializers import AssignmentSerializer
from .services import (
    assignment_to_dto,
    create_assignment,
    delete_assignment,
    get_assignment,
    list_by_course,
    list_for_user,
)


@api_view(["POST"])
@permission_classes([IsTeacher])
def create(request):
    """
    Create a new assignment from an assessment.

    When creating a COURSE assignment, empty submissions are automatically
    created for all students enrolled in the course.

    Request Body:
        {
            "assessmentId": 123,
            "audienceType": "COURSE",  # or "TEACHER"
            "courseId": 456            # Required for COURSE type
        }

    Returns:
        201: Assignment DTO with id, assessmentId, courseId, teacherId
        400: ValueError if validation fails (missing courseId for COURSE, etc.)
        403: Forbidden if not a teacher
    """
    serializer = AssignmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        assignment = create_assignment(request.user, serializer.validated_data)
    except ValueError as exc:
        return error_response(exc)
    return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def detail(request, assignment_id: int):
    """
    Get or delete a specific assignment.

    GET: Returns assignment details. Students must be enrolled in the
    course; teachers/admins can view any assignment.
    DELETE: Removes assignment and all associated submissions (teacher only).

    Args:
        assignment_id: Database ID of the assignment (path parameter)

    Returns:
        GET 200: Assignment DTO
        DELETE 200: "Assignment deleted successfully."
        403: Forbidden if student not enrolled or not a teacher for DELETE
        404: "Assignment not found"
    """
    assignment = get_assignment(assignment_id)
    if not assignment:
        return Response("Assignment not found", status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        role = primary_role(request.user)
        if role == Role.STUDENT:
            if assignment.course_id is None:
                return Response(status=status.HTTP_403_FORBIDDEN)
            enrolled = Enrollment.objects.filter(
                course_id=assignment.course_id,
                student_profile__user=request.user,
            ).exists()
            if not enrolled:
                return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(assignment_to_dto(assignment).model_dump(), status=status.HTTP_200_OK)
    if not IsTeacher().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    delete_assignment(assignment)
    return Response("Assignment deleted successfully.", status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def list_course(request, course_id: int):
    """
    List all assignments for a specific course.

    Used by teachers to view all assignments they've created for a course.

    Args:
        course_id: Database ID of the course (path parameter)

    Returns:
        200: Array of assignment DTOs
    """
    assignments = list_by_course(course_id)
    return Response(
        [assignment_to_dto(a).model_dump() for a in assignments], status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user(request, user_id: int):
    """
    List all assignments for a specific user.

    For students: Returns assignments from courses they're enrolled in.
    For teachers: Returns assignments they created.
    Researchers and admins can view assignments for any user.
    Non-researchers can only view their own assignments.

    Args:
        user_id: Database ID of the user (path parameter)

    Returns:
        200: Array of assignment DTOs
        403: Forbidden if requesting another user's assignments
        404: "User not found"
    """
    if (
        request.user.id != user_id
        and not request.user.is_staff
        and not has_role(request.user, Role.RESEARCHER)
    ):
        return Response(status=status.HTTP_403_FORBIDDEN)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)
    assignments = list_for_user(target)
    return Response(
        [assignment_to_dto(a).model_dump() for a in assignments], status=status.HTTP_200_OK
    )
