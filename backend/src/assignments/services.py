"""
Assignment domain helpers.

This module provides business logic for assignment distribution including:
- Creating assignments that link assessments to courses or teachers
- Listing assignments for students and teachers based on their context
- Automatic submission creation when assignments are created

Assignment audience types:
- COURSE: Assigned to all students in a course
- TEACHER: Assigned to a specific teacher (self-assessment)
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Role, User
from assessments.models import Assessment, QuestionKind
from core.dtos import AssignmentDTO
from core.permissions import primary_role
from courses.models import Enrollment
from submissions.models import (
    Answer,
    AnswerType,
    MultipleChoiceAnswer,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from .models import Assignment


def assignment_to_dto(assignment: Assignment) -> AssignmentDTO:
    """Convert an Assignment to a DTO for API responses."""
    return AssignmentDTO(
        id=assignment.id,
        assessmentId=assignment.assessment_id,
        audienceType=assignment.audience_type,
        courseId=assignment.course_id,
        targetTeacherId=assignment.teacher_id,
        openAt=assignment.open_at,
        dueAt=assignment.due_at,
    )


def create_assignment(creator_user: User, payload: dict) -> Assignment:
    """
    Create an assignment to distribute an assessment.

    For COURSE audience type, automatically creates placeholder submissions
    for all enrolled students.

    Args:
        creator_user: The teacher creating the assignment
        payload: Dict with assessmentId, audienceType, courseId/targetTeacherId, openAt, dueAt

    Returns:
        The created Assignment

    Raises:
        ValueError: If required fields are missing for the audience type
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
    if audience == "COURSE" and not payload.get("courseId"):
        raise ValueError("courseId must be set when audienceType is COURSE")
    if audience == "TEACHER" and not payload.get("targetTeacherId"):
        raise ValueError("targetTeacherId must be set when audienceType is TEACHER")
    assignment = Assignment.objects.create(
        created_by=creator_user,
        assessment_id=assessment_id,
        audience_type=audience,
        course_id=payload.get("courseId"),
        teacher_id=payload.get("targetTeacherId"),
        open_at=open_at,
        due_at=payload.get("dueAt"),
    )

    if assignment.course_id:
        _create_submissions_for_course(assignment)
    return assignment


def get_assignment(assignment_id: int) -> Assignment | None:
    """Retrieve an assignment by ID, or None if not found."""
    return Assignment.objects.filter(id=assignment_id).first()


def list_by_course(course_id: int) -> list[Assignment]:
    """List all assignments for a course."""
    return list(Assignment.objects.filter(course_id=course_id))


def list_for_user(user: User) -> list[Assignment]:
    """
    List assignments accessible to a user based on their role.

    Students see assignments for courses they're enrolled in.
    Teachers see assignments targeted at them (self-assessments).

    Only returns assignments that are currently open (open_at <= now)
    and not past due (due_at is null or due_at >= now).
    """
    role = primary_role(user)
    now = timezone.now()
    if role == Role.STUDENT:
        enrollments = Enrollment.objects.filter(student_profile__user=user)
        course_ids = [enrollment.course_id for enrollment in enrollments]
        return list(
            Assignment.objects.filter(course_id__in=course_ids, open_at__lte=now)
            .filter(Q(due_at__isnull=True) | Q(due_at__gte=now))
            .order_by("open_at")
        )
    if role == Role.TEACHER:
        return list(
            Assignment.objects.filter(teacher_id=user.id, open_at__lte=now)
            .filter(Q(due_at__isnull=True) | Q(due_at__gte=now))
            .order_by("open_at")
        )
    return []


@transaction.atomic
def delete_assignment(assignment: Assignment) -> None:
    """Delete an assignment and all its submissions."""
    Submission.objects.filter(assignment=assignment).delete()
    assignment.delete()


@transaction.atomic
def _create_submissions_for_course(assignment: Assignment) -> None:
    """
    Create placeholder submissions for all students in the course.

    Called when a COURSE-type assignment is created. Creates NOT_STARTED
    submissions with empty answers for each enrolled student, except for
    MOOD_METER assessments which don't need pre-created submissions.
    """
    assessment = Assessment.objects.filter(id=assignment.assessment_id).first()
    if not assessment:
        return
    if assessment.grading_mode == "MOOD_METER":
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
            if question.kind == QuestionKind.MOOD_METER:
                continue
            answer = Answer.objects.create(
                submission=submission,
                question=question,
                answer_type=_answer_type_from_question(question),
                score=0.0,
                skipped=False,
            )
            if question.kind == QuestionKind.MULTIPLE_CHOICE:
                MultipleChoiceAnswer.objects.create(answer=answer)
            elif question.kind == QuestionKind.SHORT_ANSWER:
                ShortAnswerAnswer.objects.create(answer=answer, text="")
            elif question.kind == QuestionKind.NUMBER_SCALE:
                NumberScaleAnswer.objects.create(answer=answer, val=None)


def _answer_type_from_question(question) -> str:
    """Map a question kind to the corresponding answer type."""
    if question.kind == QuestionKind.MULTIPLE_CHOICE:
        return AnswerType.MULTIPLE_CHOICE
    if question.kind == QuestionKind.SHORT_ANSWER:
        return AnswerType.SHORT_ANSWER
    if question.kind == QuestionKind.NUMBER_SCALE:
        return AnswerType.NUMBER_SCALE
    if question.kind == QuestionKind.MOOD_METER:
        return AnswerType.MOOD_METER
    return AnswerType.SHORT_ANSWER
