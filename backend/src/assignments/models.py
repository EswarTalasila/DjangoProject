"""
Assignment models for distributing assignment templates to students.

This module defines the Assignment model which connects assignment templates to
courses. When a teacher assigns a template to a course, empty submissions are
automatically created for all enrolled students.

Assignment Workflow:
    1. Admin creates an AssignmentTemplate
    2. Teacher creates an Assignment linking the template to their course
    3. Empty submissions are auto-created for each enrolled student
    4. Students complete their submissions before the due date
    5. Teacher reviews and grades submissions

Audience Types:
    COURSE: Distributed to all students enrolled in a specific course
    TEACHER: Self-assessment for the teacher (no student recipients)

Database Tables:
    assignments - Links assignment templates to courses with scheduling info

Note:
    The open_at and due_at fields control when students can access and must
    complete the assignment. Submissions created before open_at cannot be
    started until that timestamp.
"""

from django.db import models

from accounts.models import User
from assignment_templates.models import AssignmentTemplate
from courses.models import Course


class AudienceType(models.TextChoices):
    """
    Enumeration identifying the target audience for an assignment.

    Values:
        COURSE: All students in the specified course receive submissions
        TEACHER: Deprecated — rejected at creation with 400. Removal target: next release.
    """

    COURSE = "COURSE", "Course"
    TEACHER = "TEACHER", "Teacher"


class AssignmentStatus(models.TextChoices):
    """Assignment lifecycle status."""

    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class Assignment(models.Model):
    """
    Links an assignment template to a course for distribution.

    Assignments schedule when students can access and complete a template-driven
    activity.
    Creating an assignment automatically generates empty Submission records
    for all enrolled students (for COURSE type) or the teacher (for TEACHER type).

    Attributes:
        assignment_template: The assignment template being assigned
        audience_type: Who receives the assignment (COURSE or TEACHER)
        course: Target course (required for COURSE type, null for TEACHER)
        created_by: User who created the assignment (PROTECT on delete)
        open_at: When students can begin the assignment
        due_at: Optional deadline for submission (null = no deadline)
        teacher: For TEACHER type, the teacher taking the self-assessment

    Related Models:
        submissions: Submission instances for this assignment

    Delete Behavior:
        - Deleting assignment template: Cascades to delete assignments
        - Deleting course: Sets course to NULL (keeps assignment)
        - Deleting created_by user: PROTECT prevents deletion
        - Deleting teacher: Sets teacher to NULL
    """

    # The assignment template being distributed
    assignment_template = models.ForeignKey(
        AssignmentTemplate,
        on_delete=models.CASCADE,
        db_column="assignment_template_id",
        related_name="assignments",
    )

    # Editable assignment title shown to end users; defaults to the template title at creation.
    title = models.CharField(max_length=255, null=True, blank=True)

    # Who the assignment is for (COURSE = students, TEACHER = self-assessment)
    audience_type = models.CharField(max_length=255, choices=AudienceType.choices)

    # Target course for COURSE type assignments (null for TEACHER type)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="course_id",
        related_name="assignments",
    )

    # Teacher who created this assignment (cannot be deleted while assignment exists)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column="created_by_user_id")

    # When the assignment becomes available to students
    open_at = models.DateTimeField()

    # Optional deadline (null means no deadline)
    due_at = models.DateTimeField(null=True, blank=True)

    # Assignment lifecycle status (ACTIVE or ARCHIVED)
    status = models.CharField(
        max_length=16,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_assignments",
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_assignments",
    )

    # For TEACHER type: the teacher completing self-assessment
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="teacher_id",
        related_name="teacher_assignments",
    )

    class Meta:
        """Database table configuration for Assignment."""

        db_table = "assignments"
        indexes = [
            models.Index(fields=["status"], name="idx_assignment_status"),
        ]
        constraints = [
            # COURSE assignments must reference a course.
            models.CheckConstraint(
                condition=~models.Q(audience_type="COURSE") | models.Q(course_id__isnull=False),
                name="ck_assignment_course_required_for_course_audience",
            ),
            # TEACHER assignments must NOT reference a course.
            models.CheckConstraint(
                condition=~models.Q(audience_type="TEACHER") | models.Q(course_id__isnull=True),
                name="ck_assignment_no_course_for_teacher_audience",
            ),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"Assignment({self.id})"
