"""
Course management API endpoints.

This module provides REST API views for course CRUD operations and
student enrollment management. Teachers create and manage courses;
students are enrolled by teachers.

Course Workflow:
    1. Teacher creates a course (POST /api/v1/courses)
    2. Teacher adds students to course (via student endpoints)
    3. Teacher creates assignments for the course
    4. Students complete assignments and submit work

Endpoints:
    GET/POST /api/v1/courses           - List or create courses
    GET/PATCH/DELETE /api/v1/courses/{id} - Course detail/update/delete
    GET/POST /api/v1/courses/{id}/students  - List or add students
    DELETE /api/v1/courses/{id}/students/{userId} - Remove student
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.audit import complete_audit, get_client_ip, log_audit
from core.errors import error_response
from core.lifecycle import ConflictError
from core.models import AuditAction, AuditOutcome
from core.pagination import paginate
from core.parsers import parse_include_archived
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsTeacher, IsTeacherOrAbove

from .models import Course, CourseStatus
from .serializers import CourseInputSerializer, StudentNestedInputSerializer
from .services import (
    archive_course,
    can_manage_course,
    can_view_course,
    course_to_dto,
    create_course,
    create_student_in_course,
    edit_course,
    enrollment_to_student_dto,
    list_courses_for_user,
    list_students_in_course,
    purge_course,
    remove_student_from_course,
    restore_course,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def list_or_create(request):
    """
    List all courses for the user (GET) or create a new course (POST).

    GET: Returns courses the user can access.
        Students see their enrolled courses. Teachers see their own courses.
        Researchers and admins see all courses.
    POST: Creates a new course owned by the requesting teacher.

    Request Body (POST):
        {"name": "Course Name"}

    Returns:
        GET 200: Array of course DTOs with id, name, teacherId
        POST 200: Created course DTO
        POST 403: Forbidden if not a teacher (admins cannot create courses)
    """
    if request.method == "POST":
        if not IsTeacher().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            course = create_course(request.user, serializer.validated_data["name"])
        except ValueError as exc:
            return error_response(exc)
        course_data = course_to_dto(course).model_dump()
        return Response(course_data, status=status.HTTP_201_CREATED)

    include_archived, include_archived_error = parse_include_archived(request)
    if include_archived_error is not None:
        return include_archived_error
    courses = list_courses_for_user(request.user, include_archived=include_archived)
    return paginate(courses, request, transform_fn=lambda c: course_to_dto(c).model_dump())


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def detail(request, course_id: int):
    """
    Get, update, or delete a specific course.

    GET: Returns course details (requires view permission).
    PATCH: Updates course name (requires manage permission).
    DELETE: Deletes course and all enrollments (requires manage permission).

    Args:
        course_id: Database ID of the course (path parameter)

    Request Body (PATCH):
        {"name": "New Course Name"}

    Returns:
        GET/PATCH 200: Course DTO
        DELETE 204: No content on success
        403: Forbidden if user lacks permission
        404: "Course not found"

    Warning:
        DELETE performs a hard delete of the course and all student
        enrollments. Student users created for this course are also deleted.
    """
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not can_view_course(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(course_to_dto(course).model_dump(), status=status.HTTP_200_OK)

    if request.method == "PATCH":
        if not can_manage_course(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = edit_course(course, serializer.validated_data["name"])
        return Response(course_to_dto(course).model_dump(), status=status.HTTP_200_OK)

    # DELETE with ?purge=true — admin-only hard delete of archived course
    if request.query_params.get("purge", "").lower() == "true":
        audit_id = log_audit(
            actor=request.user,
            action=AuditAction.PURGE,
            target_resource_type="Course",
            target_resource_id=course.id,
            old_value={"status": course.status},
            new_value={"status": "PURGED"},
            ip_address=get_client_ip(request),
        )
        if not request.user.is_staff:
            complete_audit(audit_id, AuditOutcome.DENIED)
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            purge_course(course)
        except ConflictError as exc:
            complete_audit(audit_id, AuditOutcome.FAILURE)
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        complete_audit(audit_id, AuditOutcome.SUCCESS)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Regular DELETE not supported — use archive instead
    return Response(
        {"detail": "Use POST /archive to archive, or DELETE ?purge=true to hard-delete."},
        status=status.HTTP_409_CONFLICT,
    )


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def list_or_add_students(request, course_id: int):
    """
    List students (GET) or add a student (POST) to a course.

    GET: Returns paginated roster of active enrollments.
    POST: Creates a new student and enrolls them (teacher-owner only).

    Returns:
        GET 200: Paginated student DTOs
        POST 201: Created student DTO
        403: Forbidden
        404: Course not found
    """
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "POST":
        if not can_manage_course(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = StudentNestedInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            enrollment = create_student_in_course(
                request.user, course_id, serializer.validated_data
            )
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            enrollment_to_student_dto(enrollment).model_dump(),
            status=status.HTTP_201_CREATED,
        )

    if not can_view_course(request.user, course):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    students = list_students_in_course(course)
    return paginate(students, request, transform_fn=lambda s: s.model_dump())


@api_view(["DELETE"])
@permission_classes([IsTeacher])
def remove_student(request, course_id: int, student_user_id: int):
    """
    Remove a student from a course (and delete their user account).

    Unenrolls the student and permanently deletes their user account.
    This is typically used when a student is removed from a class roster.

    Args:
        course_id: Database ID of the course (path parameter)
        student_user_id: User ID of the student to remove (path parameter)

    Returns:
        200: "Student removed successfully"
        403: Forbidden if teacher doesn't own the course
        404: "Course not found" or "Student not found in course"

    Warning:
        This performs a hard delete of the student user account and
        all their submissions. Consider soft delete for data retention.
    """
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
    if not can_manage_course(request.user, course):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if course.status == CourseStatus.ARCHIVED:
        return Response(
            {"detail": "Cannot remove students from an archived course."},
            status=status.HTTP_409_CONFLICT,
        )
    try:
        remove_student_from_course(course, student_user_id)
    except ConflictError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except ValueError as exc:
        return error_response(exc)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive(request, course_id: int):
    """Archive a course (ARCH-UC-03). Course owner or admin."""
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.ARCHIVE,
        target_resource_type="Course",
        target_resource_id=course.id,
        old_value={"status": course.status},
        new_value={"status": "ARCHIVED"},
        ip_address=get_client_ip(request),
    )
    if not can_manage_course(request.user, course) and not request.user.is_staff:
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        course = archive_course(request.user, course)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(course_to_dto(course).model_dump(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def restore(request, course_id: int):
    """Restore an archived course (ARCH-UC-04). Course owner or admin."""
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.RESTORE,
        target_resource_type="Course",
        target_resource_id=course.id,
        old_value={"status": course.status},
        new_value={"status": "ACTIVE"},
        ip_address=get_client_ip(request),
    )
    if not can_manage_course(request.user, course) and not request.user.is_staff:
        complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        course = restore_course(request.user, course)
    except ConflictError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(course_to_dto(course).model_dump(), status=status.HTTP_200_OK)
