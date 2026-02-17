"""
Assignment domain queries — read-only helpers and DTOs.
"""

from django.db.models import Q
from django.utils import timezone

from accounts.models import Role, User
from core.dtos import AssignmentDTO
from core.permissions import primary_role
from courses.models import Enrollment

from ..models import Assignment


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
