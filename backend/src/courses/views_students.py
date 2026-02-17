"""
Student management endpoints for adding students to courses.

This module provides API endpoints for teachers to add students to their
courses, either individually or in bulk via CSV import.

Student Creation Flow:
    1. Teacher submits student data (name, username, courseId)
    2. System creates User account with STUDENT role
    3. System creates StudentProfile linked to the User
    4. System creates Enrollment linking student to course
    5. Empty Submissions are created for existing assignments

Endpoints:
    POST /api/v1/students       - Add single student to course
    POST /api/v1/students/import - Bulk import students from CSV data
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsTeacher

from .serializers import StudentInputSerializer
from .services import bulk_create_students, create_student_in_course


@api_view(["POST"])
@permission_classes([IsTeacher])
def add_one(request):
    """
    Add a single student to a course.

    Creates a new student user account and enrolls them in the specified
    course. If assignments exist for the course, empty submissions are
    created for the new student.

    Request Body:
        {
            "name": "Student Name",
            "username": "student_username",
            "courseId": 123,
            "consent": true,        # Optional
            "password": "secret"    # Optional, generated if not provided
        }

    Returns:
        200: Student DTO with enrollment info
        400: Validation error or business rule violation

    Permissions:
        Requires TEACHER role
    """
    serializer = StudentInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        enrollment = create_student_in_course(request.user, serializer.validated_data)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(enrollment_to_payload(enrollment), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsTeacher])
def add_bulk(request):
    """
    Bulk import students from a list (CSV import).

    Creates multiple student accounts and enrolls them in their specified
    courses. Invalid entries are silently skipped. Used for CSV roster import.

    Request Body:
        [
            {"name": "Student 1", "username": "student1", "courseId": 123},
            {"name": "Student 2", "username": "student2", "courseId": 123},
            ...
        ]

    Returns:
        200: List of created student DTOs (skipped entries not included)
        400: If request body is not a list

    Permissions:
        Requires TEACHER role

    Note:
        Invalid entries are silently skipped to allow partial imports.
        Check the response count against input count to detect skips.
    """
    if not isinstance(request.data, list):
        return Response({"detail": "Expected list of students"}, status=status.HTTP_400_BAD_REQUEST)
    validated = []
    for entry in request.data:
        serializer = StudentInputSerializer(data=entry)
        if not serializer.is_valid():
            continue
        validated.append(serializer.validated_data)
    created = bulk_create_students(request.user, validated)
    return Response(created, status=status.HTTP_201_CREATED)


def enrollment_to_payload(enrollment):
    """
    Convert an Enrollment instance to the student API response format.

    Args:
        enrollment: Enrollment model instance

    Returns:
        Dict with student user info and enrollment details
    """
    student = enrollment.student_profile
    user = student.user if student else None
    return {
        "id": user.id if user else None,
        "name": user.name if user else None,
        "username": user.username if user else None,
        "role": "ROLE_STUDENT",
        "consent": bool(student.consent) if student else False,
        "courseId": enrollment.course_id,
    }
