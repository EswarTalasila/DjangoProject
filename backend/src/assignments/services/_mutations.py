"""
Assignment domain mutations — create, update, delete, and archive operations.
"""

from django.db import transaction
from django.utils import timezone

from assessments.models import Assessment, AssessmentStatus, QuestionKind
from core.helpers import answer_type_from_question
from courses.models import Course, Enrollment
from courses.services import can_manage_course
from submissions.models import (
    Answer,
    MultipleChoiceAnswer,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from ..models import Assignment, AssignmentStatus, AudienceType


class ConflictError(Exception):
    """Raised when a mutation is blocked by a state conflict (409)."""


class ForbiddenError(Exception):
    """Raised when the caller lacks permission for the mutation (403)."""


def create_assignment(creator_user, payload: dict) -> Assignment:
    """
    Create an assignment to distribute an assessment.

    Validates course ownership, archived assessment, scheduling, and audience type.
    For COURSE audience type, atomically pre-creates submissions for enrolled students.

    Raises:
        ValueError: Invalid payload (400)
        ForbiddenError: Caller does not own the course (403)
        ConflictError: Assessment is archived (409)
    """
    assessment_id = payload.get("assessmentId")
    audience = payload.get("audienceType")
    open_at = payload.get("openAt")
    if assessment_id is None:
        raise ValueError("assessmentId is required")
    if not audience:
        raise ValueError("audienceType is required")
    if open_at is None:
        raise ValueError("openAt is required")

    # ASGN-CN-11: Reject deprecated TEACHER audience type
    if audience == AudienceType.TEACHER:
        raise ValueError("TEACHER audience type is deprecated and no longer accepted.")

    if audience == AudienceType.COURSE and not payload.get("courseId"):
        raise ValueError("courseId must be set when audienceType is COURSE")

    # ASGN-CN-07: Scheduling validation
    due_at = payload.get("dueAt")
    if due_at is not None and open_at >= due_at:
        raise ValueError("openAt must be before dueAt.")

    # ASGN-CN-04: Archived assessment blocks creation
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found")
    if assessment.status == AssessmentStatus.ARCHIVED:
        raise ConflictError("Cannot create assignment from an archived assessment.")

    # ASGN-CN-10: Course ownership gate
    if audience == AudienceType.COURSE:
        course = Course.objects.filter(id=payload["courseId"]).first()
        if not course:
            raise ValueError("Course not found")
        if not can_manage_course(creator_user, course):
            raise ForbiddenError("You do not own this course.")
        # ARCH-CN: Cannot create assignment for an archived course
        if course and hasattr(course, 'status'):
            from courses.models import CourseStatus
            if course.status == CourseStatus.ARCHIVED:
                raise ConflictError("Cannot create assignment for an archived course.")

    assignment = Assignment.objects.create(
        created_by=creator_user,
        assessment_id=assessment_id,
        title=(payload.get("title") or assessment.title),
        audience_type=audience,
        course_id=payload.get("courseId"),
        teacher_id=payload.get("targetTeacherId"),
        open_at=open_at,
        due_at=due_at,
        status=AssignmentStatus.ACTIVE,
    )

    if assignment.course_id:
        _create_submissions_for_course(assignment)
    return assignment


def update_assignment(assignment: Assignment, caller_user, payload: dict) -> Assignment:
    """
    Update assignment mutable fields (title, openAt, dueAt).

    Raises:
        ForbiddenError: Caller is not the assignment creator (403)
        ConflictError: Assignment is archived (409)
        ValueError: Invalid scheduling (400)
    """
    # ASGN-CN-01: Creator ownership
    if assignment.created_by_id != caller_user.id:
        raise ForbiddenError("Only the assignment creator can update it.")

    # ASGN-CN-09: Archived assignments cannot be updated
    if assignment.status == AssignmentStatus.ARCHIVED:
        raise ConflictError("Cannot update an archived assignment.")

    open_at = payload.get("openAt", assignment.open_at)
    due_at = payload.get("dueAt", assignment.due_at)
    # Handle explicit null for dueAt
    if "dueAt" in payload:
        due_at = payload["dueAt"]

    # ASGN-CN-07: Scheduling validation
    if due_at is not None and open_at >= due_at:
        raise ValueError("openAt must be before dueAt.")

    if "openAt" in payload:
        assignment.open_at = payload["openAt"]
    if "dueAt" in payload:
        assignment.due_at = payload["dueAt"]
    if "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            raise ValueError("title cannot be empty.")
        assignment.title = title
    assignment.save()
    return assignment


@transaction.atomic
def delete_assignment(assignment: Assignment, caller_user=None) -> None:
    """
    Delete an assignment if no submissions have progressed beyond NOT_STARTED.

    Raises:
        ForbiddenError: Caller is not the assignment creator (403)
        ConflictError: Submissions exist beyond NOT_STARTED (409)
    """
    # ASGN-CN-01: Creator ownership
    if caller_user is not None and assignment.created_by_id != caller_user.id:
        raise ForbiddenError("Only the assignment creator can delete it.")

    # ASGN-CN-06: Check submission status
    has_progressed = Submission.objects.filter(
        assignment=assignment,
    ).exclude(status=SubmissionStatus.NOT_STARTED).exists()
    if has_progressed:
        raise ConflictError(
            "Cannot delete assignment: submissions have progressed beyond NOT_STARTED."
        )

    # Safe to delete — only NOT_STARTED submissions exist
    Submission.objects.filter(assignment=assignment).delete()
    assignment.delete()


@transaction.atomic
def archive_assignment(request_user, assignment: Assignment) -> Assignment:
    """
    Archive an assignment (set status to ARCHIVED).

    Raises:
        PermissionError: Caller is not the assignment creator or admin (403)
        ConflictError: Assignment is already archived (409)
    """
    # ARCH-UC-01: Creator or admin can archive
    if not request_user.is_staff and assignment.created_by_id != request_user.id:
        raise PermissionError("Only the assignment creator or an admin can archive it.")

    # ASGN-UC-07-E3: Already archived
    if assignment.status == AssignmentStatus.ARCHIVED:
        raise ConflictError("Assignment is already archived.")

    assignment.status = AssignmentStatus.ARCHIVED
    assignment.archived_at = timezone.now()
    assignment.archived_by = request_user
    assignment.save(update_fields=["status", "archived_at", "archived_by"])
    return assignment


@transaction.atomic
def restore_assignment(request_user, assignment: Assignment) -> Assignment:
    """
    Restore an archived assignment back to ACTIVE.

    ARCH-CN-14: Cannot restore if parent course or assessment is archived.

    Raises:
        PermissionError: Caller is not the assignment creator or admin (403)
        ConflictError: Assignment is not archived, or parent is archived (409)
    """
    if not request_user.is_staff and assignment.created_by_id != request_user.id:
        raise PermissionError("Only the assignment creator or an admin can restore it.")
    if assignment.status != AssignmentStatus.ARCHIVED:
        raise ConflictError("Assignment is not archived.")
    # ARCH-CN-14: check parent course
    if assignment.course_id:
        from courses.models import CourseStatus
        course = assignment.course
        if course and course.status == CourseStatus.ARCHIVED:
            raise ConflictError("Cannot restore assignment while its course is archived.")
    # ARCH-CN-14: check parent assessment
    if assignment.assessment.status == AssessmentStatus.ARCHIVED:
        raise ConflictError("Cannot restore assignment while its source assessment is archived.")
    assignment.status = AssignmentStatus.ACTIVE
    assignment.archived_at = None
    assignment.archived_by = None
    assignment.restored_at = timezone.now()
    assignment.restored_by = request_user
    assignment.save(update_fields=["status", "archived_at", "archived_by", "restored_at", "restored_by"])
    return assignment


@transaction.atomic
def purge_assignment(assignment: Assignment) -> None:
    """Hard-delete an archived assignment. Admin-only, called from view."""
    if assignment.status != AssignmentStatus.ARCHIVED:
        raise ConflictError("Only archived assignments can be purged.")
    has_progressed = Submission.objects.filter(
        assignment=assignment
    ).exclude(status=SubmissionStatus.NOT_STARTED).exists()
    if has_progressed:
        raise ConflictError("Cannot purge: assignment has progressed submissions.")
    assignment.delete()


@transaction.atomic
def _create_submissions_for_course(assignment: Assignment) -> None:
    """
    Create placeholder submissions for all students in the course.

    Called when a COURSE-type assignment is created. Creates NOT_STARTED
    submissions with empty answers for each enrolled student.
    """
    assessment = Assessment.objects.filter(id=assignment.assessment_id).first()
    if not assessment:
        return
    if assignment.course_id is None:
        return
    student_ids = Enrollment.objects.filter(course_id=assignment.course_id).values_list(
        "student_profile__user_id", flat=True
    )
    for student_id in student_ids:
        if Submission.objects.filter(assignment=assignment, student_id=student_id).exists():
            continue
        submission = Submission.objects.create(
            assignment=assignment,
            student_id=student_id,
            teacher_id=None,
            submitted_at=None,
            status=SubmissionStatus.NOT_STARTED,
        )
        for question in assessment.questions.all():
            answer = Answer.objects.create(
                submission=submission,
                question=question,
                answer_type=answer_type_from_question(question),
                score=0.0,
                skipped=False,
            )
            if question.kind == QuestionKind.MULTIPLE_CHOICE:
                MultipleChoiceAnswer.objects.create(answer=answer)
            elif question.kind == QuestionKind.SHORT_ANSWER:
                ShortAnswerAnswer.objects.create(answer=answer, text="")
            elif question.kind == QuestionKind.NUMBER_SCALE:
                NumberScaleAnswer.objects.create(answer=answer, val=None)
