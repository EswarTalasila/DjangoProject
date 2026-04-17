"""
Submission management API endpoints.

This module handles student submission workflows including:
- Saving draft submissions (in-progress work)
- Submitting final answers
- Teacher grading and score override
- Listing submissions by various filters (assignment, student)

Submissions go through a lifecycle:
    NOT_STARTED -> IN_PROGRESS (draft) -> SUBMITTED -> (optionally) GRADED

Permission Model:
    - Students can only access/modify their own submissions
    - Teachers can access submissions for assignments they own
    - Researchers can read all submissions
    - Admins (is_staff) can access all submissions
"""

import logging

from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, SudoPermission
from assignments.models import Assignment, AssignmentStatus
from core.audit import complete_audit, get_client_ip, log_audit
from core.errors import error_response
from core.models import AuditAction, AuditOutcome
from core.pagination import paginate
from core.permissions import has_role, has_sudo_permission, primary_role, teacher_owns_assignment
from courses.models import Enrollment, EnrollmentStatus

from .models import Submission, SubmissionStatus
from .serializers import SubmissionSerializer
from .services import (
    create_submission,
    get_by_assignment,
    get_by_student,
    get_by_student_and_assignment,
    get_by_student_and_assignment_for_dto,
    get_submission,
    get_submission_for_dto,
    list_me,
    override_score,
    submission_to_compact_dto,
    submission_to_dto,
)

logger = logging.getLogger(__name__)


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


# Backward-compatible alias — image_views.py imports this name.
_teacher_owns_assignment = teacher_owns_assignment


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
        course_id=assignment.course_id,
        student_profile__user_id=user.id,
        status=EnrollmentStatus.ACTIVE,
    ).exists()


def _can_access_submission(user, submission) -> bool:
    """
    Determine if a user has permission to access a submission.

    Access rules by role:
        - Admin (is_staff): Full access to all submissions
        - RESEARCHER: Full read access to all submissions (data oversight)
        - STUDENT: Can only access their own submissions
        - TEACHER: Can access submissions for assignments they own

    Args:
        user: The User instance requesting access
        submission: The Submission being accessed

    Returns:
        True if user can access the submission, False otherwise
    """
    role = primary_role(user)
    if user.is_staff:
        return True
    if has_role(user, Role.RESEARCHER):
        return has_sudo_permission(user, SudoPermission.VIEW_SUBMISSIONS)
    if role == Role.STUDENT:
        return bool(submission.student_id == user.id)
    if role == Role.TEACHER:
        return teacher_owns_assignment(user, submission.assignment)
    return False


def _researcher_can_view_submissions(user) -> bool:
    """
    Researchers are default-deny for submissions and require explicit sudo.
    """
    role = primary_role(user)
    if user.is_staff or role != Role.RESEARCHER:
        return True
    return has_sudo_permission(user, SudoPermission.VIEW_SUBMISSIONS)


def _create_for_assignment(request, assignment_id: int, assignment: Assignment):
    """
    Internal helper to create a submission with role-based validation.

    Only students can submit. Validates:
    - Caller is a student (SUB-UC-02-E2)
    - Assignment is not archived (SUB-CN-06)
    - Assignment has opened (openAt <= now)
    - Student ID matches caller (self-only)
    - Student is enrolled in the assignment's course (SUB-UC-02-E5)
    """
    role = primary_role(request.user)
    if role != Role.STUDENT:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if assignment.status == AssignmentStatus.ARCHIVED:
        return Response(
            {"detail": "Assignment is archived"},
            status=status.HTTP_409_CONFLICT,
        )
    if assignment.open_at and assignment.open_at > timezone.now():
        return Response({"detail": "Assignment has not opened yet"}, status=status.HTTP_403_FORBIDDEN)
    serializer = SubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if serializer.validated_data.get("studentId") != request.user.id:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if not _student_enrolled_in_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        submission = create_submission(
            assignment_id,
            serializer.validated_data,
            SubmissionStatus.SUBMITTED,
        )
    except ValueError as exc:
        return error_response(exc)
    # Re-fetch with prefetches for efficient DTO serialization.
    submission = get_submission_for_dto(submission.id)
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
    if not _researcher_can_view_submissions(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    role = primary_role(request.user)
    if role == Role.STUDENT:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    # Admins and researchers can view any assignment's submissions
    if (
        not request.user.is_staff
        and not has_role(request.user, Role.RESEARCHER)
        and role == Role.TEACHER
        and not teacher_owns_assignment(request.user, assignment)
    ):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_assignment(assignment_id)
    return paginate(submissions, request, transform_fn=lambda s: submission_to_compact_dto(s).model_dump())


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
        submission = get_submission_for_dto(submission_id)
    except ValueError as exc:
        return error_response(exc)
    if not _can_access_submission(request.user, submission):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_by_assignment_id(request, assignment_id: int):
    """
    List all submissions for a specific assignment.

    Teachers, researchers, and admins can view all submissions for an
    assignment to review student work and grades.

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
    if not _researcher_can_view_submissions(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    role = primary_role(request.user)
    if role == Role.STUDENT:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    # Admins and researchers can view any assignment's submissions
    if (
        not request.user.is_staff
        and not has_role(request.user, Role.RESEARCHER)
        and role == Role.TEACHER
        and not teacher_owns_assignment(request.user, assignment)
    ):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_assignment(assignment_id)
    return paginate(submissions, request, transform_fn=lambda s: submission_to_compact_dto(s).model_dump())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_by_student_id(request, student_id: int):
    """
    List all submissions by a specific student (SUB-UC-07).

    Access control:
    - ADMIN/RESEARCHER: any student's submissions
    - TEACHER: submissions for students in courses they own (SUB-CN-08)
    - STUDENT: own submissions only
    """
    role = primary_role(request.user)
    if request.user.is_staff:
        pass
    elif has_role(request.user, Role.RESEARCHER):
        if not has_sudo_permission(request.user, SudoPermission.VIEW_SUBMISSIONS):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        pass
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        # Teacher can only see submissions for assignments they own (SUB-CN-08).
        owned_qs = Submission.objects.filter(
            student_id=student_id,
            assignment__course__teacher_profile__user_id=request.user.id,
        )
        if not owned_qs.exists():
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        owned_qs = owned_qs.select_related("student", "teacher", "assignment__course")
        return paginate(
            owned_qs,
            request,
            transform_fn=lambda s: submission_to_compact_dto(s).model_dump(),
        )
    else:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    submissions = get_by_student(student_id)
    return paginate(submissions, request, transform_fn=lambda s: submission_to_compact_dto(s).model_dump())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_student_submission(request, student_id: int, assignment_id: int):
    """
    Get a specific student's submission for a specific assignment.

    Used by the frontend to load a student's work for viewing or editing.
    Students can only access their own; teachers access via ownership;
    researchers and admins can access any submission.

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
    if request.user.is_staff:
        pass
    elif has_role(request.user, Role.RESEARCHER):
        if not has_sudo_permission(request.user, SudoPermission.VIEW_SUBMISSIONS):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    elif role == Role.STUDENT:
        if request.user.id != student_id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if not _student_enrolled_in_assignment(request.user, assignment):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    elif role == Role.TEACHER:
        if not teacher_owns_assignment(request.user, assignment):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        submission = get_by_student_and_assignment_for_dto(student_id, assignment_id)
    except ValueError as exc:
        return error_response(exc)
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def save_draft(request, student_id: int, assignment_id: int):
    """
    Save a draft submission (SUB-UC-01).

    Only students can save drafts. Validates:
    - Caller is a student (SUB-UC-01-E2)
    - Student ID matches caller (SUB-UC-01-E3)
    - Assignment exists (SUB-UC-01-E4)
    - Assignment is not archived (SUB-CN-07, SUB-UC-01-E5)
    - Student is enrolled (SUB-UC-01-E6)
    """
    role = primary_role(request.user)
    if role != Role.STUDENT:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if request.user.id != student_id:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    assignment = _assignment_for(assignment_id)
    if not assignment:
        return error_response("Assignment not found", status.HTTP_404_NOT_FOUND)
    if assignment.status == AssignmentStatus.ARCHIVED:
        return Response(
            {"detail": "Assignment is archived"},
            status=status.HTTP_409_CONFLICT,
        )
    if not _student_enrolled_in_assignment(request.user, assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    answers = request.data.get("answers", [])
    payload = {
        "assignmentId": assignment_id,
        "studentId": student_id,
        "status": SubmissionStatus.IN_PROGRESS,
        "answers": answers,
    }
    try:
        submission = create_submission(assignment_id, payload, SubmissionStatus.IN_PROGRESS)
    except ValueError as exc:
        return error_response(exc)
    # Re-fetch with prefetches for efficient DTO serialization.
    submission = get_submission_for_dto(submission.id)
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_me_view(request):
    """
    List submissions for the authenticated caller (SUB-UC-08).
    """
    if not _researcher_can_view_submissions(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    status_filter = request.query_params.get("status")
    results = list_me(request.user.id, status_filter)
    return paginate(results, request, transform_fn=lambda s: submission_to_compact_dto(s).model_dump())


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
        return Response({"detail": "Expected list of scores"}, status=status.HTTP_400_BAD_REQUEST)
    role = primary_role(request.user)
    if not request.user.is_staff and role != Role.TEACHER:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    submission = Submission.objects.filter(id=submission_id).select_related("assignment").first()
    if not submission:
        return error_response("Submission not found", status.HTTP_404_NOT_FOUND)
    if role == Role.TEACHER and not teacher_owns_assignment(request.user, submission.assignment):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    old_scores = list(
        submission.answers.order_by("id").values_list("score", flat=True)
    )
    audit_id = log_audit(
        actor=request.user,
        action=AuditAction.SCORE_OVERRIDE,
        target_resource_type="Submission",
        target_resource_id=submission_id,
        old_value={"scores": old_scores},
        new_value={"scores": request.data},
        ip_address=get_client_ip(request),
    )

    try:
        override_score(submission_id, request.data)
    except ValueError as exc:
        complete_audit(audit_id, AuditOutcome.FAILURE)
        return error_response(exc)
    complete_audit(audit_id, AuditOutcome.SUCCESS)
    # Re-fetch with prefetches for efficient DTO serialization.
    submission = get_submission_for_dto(submission_id)
    return Response(submission_to_dto(submission).model_dump(), status=status.HTTP_200_OK)
