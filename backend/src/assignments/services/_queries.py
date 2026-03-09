"""
Assignment domain queries — read-only helpers and DTOs.
"""

from django.db.models import Q
from django.utils import timezone

from accounts.models import Role, User
from core.dtos import AssignmentDTO
from core.permissions import primary_role
from courses.models import Course, Enrollment

from ..models import Assignment, AssignmentStatus


def assignment_to_dto(assignment: Assignment) -> AssignmentDTO:
    """Convert an Assignment to a DTO for API responses."""
    return AssignmentDTO(
        id=assignment.id,
        title=(assignment.title or assignment.assessment.title),
        assessmentId=assignment.assessment_id,
        assessmentTitle=assignment.assessment.title,
        audienceType=assignment.audience_type,
        courseId=assignment.course_id,
        targetTeacherId=assignment.teacher_id,
        openAt=assignment.open_at,
        dueAt=assignment.due_at,
        status=assignment.status,
    )


def get_assignment(assignment_id: int) -> Assignment | None:
    """Retrieve an assignment by ID, or None if not found."""
    return Assignment.objects.filter(id=assignment_id).first()


def list_by_course(course_id: int, include_archived: bool = False) -> list[Assignment]:
    """List assignments for a course. ARCH-CN-06: default ACTIVE-only."""
    qs = Assignment.objects.filter(course_id=course_id)
    if not include_archived:
        qs = qs.filter(status=AssignmentStatus.ACTIVE)
    return list(qs)


def list_for_user(user: User) -> list[Assignment]:
    """
    List assignments accessible to a user based on their role.

    Students see ACTIVE assignments from enrolled courses within the time window.
    Teachers see assignments they created.
    """
    role = primary_role(user)
    now = timezone.now()
    if role == Role.STUDENT:
        enrollments = Enrollment.objects.filter(student_profile__user=user)
        course_ids = [enrollment.course_id for enrollment in enrollments]
        return list(
            Assignment.objects.filter(
                course_id__in=course_ids,
                open_at__lte=now,
                status=AssignmentStatus.ACTIVE,
            )
            .filter(Q(due_at__isnull=True) | Q(due_at__gte=now))
            .order_by("open_at")
        )
    if role == Role.TEACHER:
        return list(
            Assignment.objects.filter(created_by=user).order_by("open_at")
        )
    # ADMIN/RESEARCHER viewing own assignments — return empty (they use cross-user endpoint)
    return []
