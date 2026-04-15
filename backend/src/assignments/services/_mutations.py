"""Assignment domain mutations: create, update, delete, and lifecycle actions."""

from django.db import transaction
from django.utils import timezone

from assignment_templates.models import (
    AssignmentTemplate,
    AssignmentTemplateStatus,
    QuestionKind,
)
from core.helpers import answer_type_from_question
from courses.models import Course, Enrollment, EnrollmentStatus
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
    """Raised when a mutation is blocked by a state conflict."""


class ForbiddenError(Exception):
    """Raised when the caller lacks permission for the mutation."""


@transaction.atomic
def create_assignment(creator_user, payload: dict) -> Assignment:
    """Create an assignment from an assignment template."""
    assignment_template_id = payload.get("assignmentTemplateId")
    audience = payload.get("audienceType")
    open_at = payload.get("openAt")
    if assignment_template_id is None:
        raise ValueError("assignmentTemplateId is required")
    if not audience:
        raise ValueError("audienceType is required")
    if open_at is None:
        raise ValueError("openAt is required")

    if audience == AudienceType.TEACHER:
        raise ValueError("TEACHER audience type is deprecated and no longer accepted.")

    if audience == AudienceType.COURSE and not payload.get("courseId"):
        raise ValueError("courseId must be set when audienceType is COURSE")

    due_at = payload.get("dueAt")
    if due_at is not None and open_at >= due_at:
        raise ValueError("openAt must be before dueAt.")

    assignment_template = AssignmentTemplate.objects.filter(id=assignment_template_id).first()
    if not assignment_template:
        raise ValueError("AssignmentTemplate not found")
    if assignment_template.status == AssignmentTemplateStatus.ARCHIVED:
        raise ConflictError("Cannot create assignment from an archived assignment template.")
    if assignment_template.status == AssignmentTemplateStatus.DRAFT:
        raise ConflictError(
            "Cannot create assignment from a draft assignment template. Publish it first."
        )

    if audience == AudienceType.COURSE:
        course = Course.objects.filter(id=payload["courseId"]).first()
        if not course:
            raise ValueError("Course not found")
        if not can_manage_course(creator_user, course):
            raise ForbiddenError("You do not own this course.")
        if course and hasattr(course, "status"):
            from courses.models import CourseStatus

            if course.status == CourseStatus.ARCHIVED:
                raise ConflictError("Cannot create assignment for an archived course.")

    assignment = Assignment.objects.create(
        created_by=creator_user,
        assignment_template_id=assignment_template_id,
        title=(payload.get("title") or assignment_template.title),
        audience_type=audience,
        course_id=payload.get("courseId"),
        teacher_id=payload.get("targetTeacherId"),
        open_at=open_at,
        due_at=due_at,
        status=AssignmentStatus.ACTIVE,
    )

    update_fields: list[str] = []
    if not getattr(assignment_template, "has_been_used", False):
        assignment_template.has_been_used = True
        update_fields.append("has_been_used")
    if assignment_template.used_at is None:
        assignment_template.used_at = timezone.now()
        update_fields.append("used_at")
    if update_fields:
        assignment_template.save(update_fields=update_fields)

    if assignment.course_id:
        _create_submissions_for_course(assignment)
    return assignment


def update_assignment(assignment: Assignment, caller_user, payload: dict) -> Assignment:
    """Update assignment mutable fields."""
    if assignment.created_by_id != caller_user.id:
        raise ForbiddenError("Only the assignment creator can update it.")
    if assignment.status == AssignmentStatus.ARCHIVED:
        raise ConflictError("Cannot update an archived assignment.")

    open_at = payload.get("openAt", assignment.open_at)
    due_at = payload.get("dueAt", assignment.due_at)
    if "dueAt" in payload:
        due_at = payload["dueAt"]
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
def archive_assignment(request_user, assignment: Assignment) -> Assignment:
    """Archive an assignment."""
    if not request_user.is_staff and assignment.created_by_id != request_user.id:
        raise PermissionError("Only the assignment creator or an admin can archive it.")
    if assignment.status == AssignmentStatus.ARCHIVED:
        raise ConflictError("Assignment is already archived.")

    assignment.status = AssignmentStatus.ARCHIVED
    assignment.archived_at = timezone.now()
    assignment.archived_by = request_user
    assignment.save(update_fields=["status", "archived_at", "archived_by"])
    return assignment


@transaction.atomic
def restore_assignment(request_user, assignment: Assignment) -> Assignment:
    """Restore an archived assignment back to active."""
    if not request_user.is_staff and assignment.created_by_id != request_user.id:
        raise PermissionError("Only the assignment creator or an admin can restore it.")
    if assignment.status != AssignmentStatus.ARCHIVED:
        raise ConflictError("Assignment is not archived.")

    if assignment.course_id:
        from courses.models import CourseStatus

        course = assignment.course
        if course and course.status == CourseStatus.ARCHIVED:
            raise ConflictError("Cannot restore assignment while its course is archived.")

    if assignment.assignment_template.status == AssignmentTemplateStatus.ARCHIVED:
        raise ConflictError(
            "Cannot restore assignment while its source assignment template is archived."
        )

    assignment.status = AssignmentStatus.ACTIVE
    assignment.archived_at = None
    assignment.archived_by = None
    assignment.restored_at = timezone.now()
    assignment.restored_by = request_user
    assignment.save(
        update_fields=["status", "archived_at", "archived_by", "restored_at", "restored_by"]
    )
    return assignment


@transaction.atomic
def purge_assignment(assignment: Assignment) -> None:
    """Hard-delete an archived assignment."""
    if assignment.status != AssignmentStatus.ARCHIVED:
        raise ConflictError("Only archived assignments can be purged.")
    has_progressed = Submission.objects.filter(assignment=assignment).exclude(
        status=SubmissionStatus.NOT_STARTED
    ).exists()
    if has_progressed:
        raise ConflictError("Cannot purge: assignment has progressed submissions.")

    from submissions.image_services import cleanup_images_for_submission
    from ._archive_exports import cleanup_assignment_archive_artifacts

    for submission in assignment.submissions.all():
        cleanup_images_for_submission(submission.id)
    cleanup_assignment_archive_artifacts(assignment)
    assignment.delete()


@transaction.atomic
def _create_submissions_for_course(assignment: Assignment) -> None:
    """Create placeholder submissions for all enrolled students in the course."""
    assignment_template = AssignmentTemplate.objects.filter(
        id=assignment.assignment_template_id
    ).first()
    if not assignment_template or assignment.course_id is None:
        return

    student_ids = Enrollment.objects.filter(
        course_id=assignment.course_id,
        status=EnrollmentStatus.ACTIVE,
    ).values_list("student_profile__user_id", flat=True)

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
        for question in assignment_template.questions.all():
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
