"""
Assignment domain mutations — create and delete operations.
"""

from django.db import transaction

from assessments.models import Assessment, GradingMode, QuestionKind
from core.helpers import answer_type_from_question
from courses.models import Enrollment
from submissions.models import (
    Answer,
    MultipleChoiceAnswer,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from ..models import Assignment, AudienceType


def create_assignment(creator_user, payload: dict) -> Assignment:
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
    if audience == AudienceType.COURSE and not payload.get("courseId"):
        raise ValueError("courseId must be set when audienceType is COURSE")
    if audience == AudienceType.TEACHER and not payload.get("targetTeacherId"):
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
    if assessment.grading_mode == GradingMode.MOOD_METER:
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
