"""
Submission management API endpoints.

This module handles student and teacher submission workflows including:
- Creating and editing submissions for assignments
- Saving draft submissions (in-progress work)
- Submitting final answers
- Teacher grading and score override
- Listing submissions by various filters (assignment, student, teacher)

Submissions go through a lifecycle:
    NOT_STARTED -> IN_PROGRESS (draft) -> SUBMITTED -> (optionally) GRADED

Permission Model:
    - Students can only access/modify their own submissions
    - Teachers can access submissions for assignments they own
    - Admins can access all submissions
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from accounts.services import teacher_owns_student
from assignments.models import Assignment
from core.errors import error_response, server_error_response
from core.permissions import primary_role
from courses.models import Enrollment

from .models import Submission
from .serializers import AnswerSerializer, SubmissionSerializer
from .services import (
    create_submission,
    edit_submission,
    get_by_assignment,
    get_by_student,
    get_by_student_and_assignment,
    get_by_teacher,
    get_submission,
    list_mine,
    override_score,
    submission_to_dto,
    submit_teacher_self_assessment,
)


def _assignment_for(assignment_id: int) -> Assignment | None:
    """
    Fetch an assignment with pre-loaded course and teacher relationships.

    Uses select_related to eagerly load the course's teacher profile,
    avoiding N+1 queries when checking ownership permissions.

    Args:
        assignment_id: Database ID of the assignment to fetch

    Returns:
        Assignment instance with related course/teacher loaded, or None if not found
    """
    return (
        Assignment.objects.select_related("course__teacher_profile__user")
        .filter(id=assignment_id)
        .first()
    )


def _teacher_owns_assignment(user, assignment: Assignment) -> bool:
    """
    Check if the given user (teacher) owns the assignment.

    Ownership is determined by either:
    1. The assignment's teacher_id matches the user's ID, OR
    2. The assignment's course belongs to the user's teacher profile

    Args:
        user: The User instance to check ownership for
        assignment: The Assignment to check

    Returns:
        True if the user owns the assignment, False otherwise
    """
    if assignment.teacher_id == user.id:
        return True
    if assignment.course and assignment.course.teacher_profile:
        return bool(assignment.course.teacher_profile.user_id == user.id)
    return False


def _student_enrolled_in_assignment(user, assignment: Assignment) -> bool:
    """
    Check if the student is enrolled in the course that contains this assignment.

    Args:
        user: The User instance (student) to check enrollment for
        assignment: The Assignment whose course enrollment to verify

    Returns:
        True if student is enrolled in the assignment's course, False otherwise.
        Returns False if assignment has no associated course.
    """
    if not assignment.course_id:
        return False
    return Enrollment.objects.filter(
        course_id=assignment.course_id, student_profile__user_id=user.id
    ).exists()


def _can_access_submission(user, submission) -> bool:
    """
    Determine if a user has permission to access a submission.

    Access rules by role:
        - ADMIN: Full access to all submissions
        - STUDENT: Can only access their own submissions
        - TEACHER: Can access submissions for assignments they own

    Args:
        user: The User instance requesting access
        submission: The Submission being accessed

    Returns:
        True if user can access the submission, False otherwise
    """
    role = primary_role(user)
    if role == Role.ADMIN:
        return True
    if role == Role.STUDENT:
        return bool(submission.student_id == user.id)
    if role == Role.TEACHER:
        return _teacher_owns_assignment(user, submission.assignment)
    return False


def _create_for_assignment(request, assignment_id: int, assignment: Assignment):
    """
    Internal helper to create a submission with role-based validation.

    Validates that:
    - Students can only create submissions for themselves
    - Students must be enrolled in the assignment's course
    - Teachers cannot create student submissions (they use teacher_self_assess)

    Args:
        request: The HTTP request with user and submission data
        assignment_id: ID of the assignment to submit to
        assignment: Pre-fetched Assignment instance

    Returns:
        Response with created submission DTO (201) or error response
    """
    role = primary_role(request.user)
    serializer = SubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if role == Role.STUDENT:
        if serializer.validated_data.get("studentId") != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _student_enrolled_in_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        return Response(status=status.HTTP_403_FORBIDDEN)
    try:
        submission = create_submission(assignment_id, serializer.validated_data, "SUBMITTED")
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_for_assignment(request, assignment_id: int):
    """
    Create a new submission for an assignment.

    Students use this endpoint to submit their answers to an assignment.
    The submission is created with SUBMITTED status.

    Args:
        assignment_id: ID of the assignment to submit to (path parameter)

    Request Body:
        {
            "assignmentId": 123,
            "studentId": 456,
            "answers": [
                {"questionId": 1, "value": "answer text"},
                ...
            ]
        }

    Returns:
        201: Submission DTO with id, answers, status, timestamps
        403: Forbidden if student not enrolled or not their own submission
        404: "Assignment not found" if assignment_id invalid
    """
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    return _create_for_assignment(request, assignment_id, assignment)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def assignment_submissions(request, assignment_id: int):
    """
    List all submissions for an assignment (GET) or create a new one (POST).

    GET: Returns all submissions for the assignment (teachers/admins only).
    POST: Creates a new submission (students only, for their own work).

    Args:
        assignment_id: ID of the assignment (path parameter)

    GET Returns:
        200: Array of submission DTOs
        403: Forbidden if student (they should use get_student_submission)
        403: Forbidden if teacher doesn't own the assignment
        404: "Assignment not found"

    POST: See create_for_assignment for request/response format
    """
    if request.method == "POST":
        assignment = _assignment_for(assignment_id)
        if not assignment:
            return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
        return _create_for_assignment(request, assignment_id, assignment)
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    role = primary_role(request.user)
    if role == Role.STUDENT:
        return Response(status=status.HTTP_403_FORBIDDEN)
    if role == Role.TEACHER and not _teacher_owns_assignment(request.user, assignment):
        return Response(status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_assignment(assignment_id)
    return Response([submission_to_dto(sub).model_dump() for sub in submissions], status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def teacher_self_assess(request, assessment_id: int):
    """
    Submit a teacher's self-assessment for mood meter or reflection.

    Teachers complete self-assessments that aren't tied to specific
    assignments. This creates a submission with the teacher as both
    creator and subject.

    Args:
        assessment_id: ID of the assessment being completed (path parameter)

    Request Body:
        [
            {"questionId": 1, "value": "response text"},
            {"questionId": 2, "value": "5"},
            ...
        ]

    Returns:
        201: Submission DTO
        400: "Expected list of answers" if body isn't an array
        400: ValueError message if validation fails
    """
    if not isinstance(request.data, list):
        return Response("Expected list of answers", status=status.HTTP_400_BAD_REQUEST)
    answers = []
    for entry in request.data:
        serializer = AnswerSerializer(data=entry)
        serializer.is_valid(raise_exception=True)
        answers.append(serializer.validated_data)
    try:
        submission = submit_teacher_self_assessment(request.user.id, assessment_id, answers)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_one(request, submission_id: int):
    """
    Retrieve a single submission by its ID.

    Returns the full submission with all answers. Access is controlled
    by role: students see only their own, teachers see their assignments'.

    Args:
        submission_id: Database ID of the submission (path parameter)

    Returns:
        200: Full submission DTO with answers
        403: Forbidden if user cannot access this submission
        404: "Submission not found" if ID invalid
    """
    try:
        submission = get_submission(submission_id)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    if not _can_access_submission(request.user, submission):
        return Response(status=status.HTTP_403_FORBIDDEN)
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_by_assignment_id(request, assignment_id: int):
    """
    List all submissions for a specific assignment.

    Teachers and admins can view all submissions for an assignment
    to review student work and grades.

    Args:
        assignment_id: ID of the assignment (path parameter)

    Returns:
        200: Array of submission DTOs
        403: Forbidden if student or teacher doesn't own assignment
        404: "Assignment not found" if ID invalid
    """
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    role = primary_role(request.user)
    if role == Role.STUDENT:
        return Response(status=status.HTTP_403_FORBIDDEN)
    if role == Role.TEACHER and not _teacher_owns_assignment(request.user, assignment):
        return Response(status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_assignment(assignment_id)
    return Response([submission_to_dto(sub).model_dump() for sub in submissions], status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_by_student_id(request, student_id: int):
    """
    List all submissions by a specific student.

    Students can only view their own submissions. Teachers can view
    submissions from students they created. Admins can view any student's.

    Args:
        student_id: User ID of the student (path parameter)

    Returns:
        200: Array of submission DTOs
        403: Forbidden if requesting other student's data (as student)
        403: Forbidden if teacher doesn't own this student
    """
    role = primary_role(request.user)
    if role == Role.ADMIN:
        pass
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        student_user = User.objects.filter(id=student_id).first()
        if not student_user or not teacher_owns_student(request.user, student_user):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_student(student_id)
    return Response([submission_to_dto(sub).model_dump() for sub in submissions], status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_by_teacher_id(request, teacher_id: int):
    """
    List all submissions created by a specific teacher (self-assessments).

    Returns teacher self-assessment submissions. Teachers can only view
    their own; admins can view any teacher's.

    Args:
        teacher_id: User ID of the teacher (path parameter)

    Returns:
        200: Array of submission DTOs
        403: Forbidden if teacher requesting another teacher's data
        403: Forbidden if student (no access to teacher submissions)
    """
    role = primary_role(request.user)
    if role == Role.ADMIN:
        pass
    elif role == Role.TEACHER:
        if request.user.id != teacher_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_teacher(teacher_id)
    return Response([submission_to_dto(sub).model_dump() for sub in submissions], status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_student_submission(request, student_id: int, assignment_id: int):
    """
    Get a specific student's submission for a specific assignment.

    Used by the frontend to load a student's work for viewing or editing.
    Students can only access their own; teachers access via ownership.

    Args:
        student_id: User ID of the student (path parameter)
        assignment_id: ID of the assignment (path parameter)

    Returns:
        200: Submission DTO with all answers
        403: Forbidden if student accessing another's submission
        403: Forbidden if teacher doesn't own the assignment
        403: Forbidden if student not enrolled in assignment's course
        404: "Assignment not found" or "Submission not found"
    """
    role = primary_role(request.user)
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    if role == Role.ADMIN:
        pass
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _student_enrolled_in_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        if not _teacher_owns_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    try:
        submission = get_by_student_and_assignment(student_id, assignment_id)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def save_draft(request, student_id: int, assignment_id: int):
    """
    Save a draft submission (work in progress, not yet submitted).

    Students use this to save partial work before final submission.
    Creates or updates a submission with IN_PROGRESS status.

    Args:
        student_id: User ID of the student (path parameter)
        assignment_id: ID of the assignment (path parameter)

    Request Body:
        {
            "answers": [
                {"questionId": 1, "value": "partial answer"},
                ...
            ]
        }

    Returns:
        200: Submission DTO with IN_PROGRESS status
        403: Forbidden if student saving another's draft
        403: Forbidden if not enrolled in assignment's course
        404: "Assignment not found"
    """
    role = primary_role(request.user)
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    if role == Role.ADMIN:
        pass
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _student_enrolled_in_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    answers = request.data.get("answers", [])
    payload = {
        "assignmentId": assignment_id,
        "studentId": student_id,
        "status": "IN_PROGRESS",
        "answers": answers,
    }
    try:
        submission = create_submission(assignment_id, payload, "IN_PROGRESS")
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_mine_view(request):
    """
    List submissions for the authenticated user with optional status filter.

    Used by the dashboard to show the user's own submissions. Supports
    filtering by status (e.g., only IN_PROGRESS or only SUBMITTED).

    Query Parameters:
        userId: Required - User ID to fetch submissions for
        status: Optional - Filter by submission status (IN_PROGRESS, SUBMITTED, etc.)

    Returns:
        200: Array of submission summary DTOs (lighter than full DTOs)
        400: Bad request if userId not provided
        403: Forbidden if requesting another user's submissions (non-admin)
    """
    user_id = request.query_params.get("userId")
    if user_id is None:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    if request.user.id != int(user_id) and primary_role(request.user) != Role.ADMIN:
        return Response(status=status.HTTP_403_FORBIDDEN)
    status_filter = request.query_params.get("status")
    return Response(list_mine(int(user_id), status_filter), status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def edit(request):
    """
    Update an existing submission (answers and/or status).

    Used by students to modify their submission before final submit,
    or by teachers to update grading information.

    Request Body:
        {
            "assignmentId": 123,
            "studentId": 456,         # For student submissions
            "teacherId": 789,         # For teacher self-assessments
            "status": "SUBMITTED",    # Optional status update
            "answers": [...]          # Updated answers
        }

    Returns:
        200: Updated submission DTO
        403: Forbidden if student editing another's submission
        403: Forbidden if teacher editing submission they don't own
        404: "Assignment not found"
    """
    serializer = SubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assignment_id = serializer.validated_data.get("assignmentId")
    student_id = serializer.validated_data.get("studentId")
    teacher_id = serializer.validated_data.get("teacherId")
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    role = primary_role(request.user)
    if role == Role.ADMIN:
        pass
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _student_enrolled_in_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        if request.user.id != teacher_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _teacher_owns_assignment(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    try:
        submission = edit_submission(serializer.validated_data)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def override_score_view(request, submission_id: int):
    """
    Override scores for individual answers in a submission (teacher grading).

    Teachers use this to manually grade or adjust scores for student answers.
    Only teachers who own the assignment or admins can override scores.

    Args:
        submission_id: ID of the submission to grade (path parameter)

    Request Body:
        [
            {"answerId": 1, "score": 10},
            {"answerId": 2, "score": 8},
            ...
        ]

    Returns:
        200: Updated submission DTO with new scores
        400: "Expected list of scores" if body isn't an array
        403: Forbidden if not teacher/admin or doesn't own assignment
        404: "Submission not found"
    """
    if not isinstance(request.data, list):
        return Response("Expected list of scores", status=status.HTTP_400_BAD_REQUEST)
    role = primary_role(request.user)
    if role not in (Role.ADMIN, Role.TEACHER):
        return Response(status=status.HTTP_403_FORBIDDEN)
    submission = Submission.objects.filter(id=submission_id).select_related("assignment").first()
    if not submission:
        return error_response("Submission not found", status.HTTP_404_NOT_FOUND)
    if role == Role.TEACHER and not _teacher_owns_assignment(request.user, submission.assignment):
        return Response(status=status.HTTP_403_FORBIDDEN)
    try:
        submission = override_score(submission_id, request.data)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)
