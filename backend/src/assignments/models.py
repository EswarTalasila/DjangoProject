"""
Assignment models for distributing assessments to students.

This module defines the Assignment model which connects assessments (templates)
to courses (classes). When a teacher assigns an assessment to a course, empty
submissions are automatically created for all enrolled students.

Assignment Workflow:
    1. Admin creates an Assessment (template with questions)
    2. Teacher creates an Assignment linking assessment to their course
    3. Empty Submissions are auto-created for each enrolled student
    4. Students complete their submissions before the due date
    5. Teacher reviews and grades submissions

Audience Types:
    COURSE: Distributed to all students enrolled in a specific course
    TEACHER: Self-assessment for the teacher (no student recipients)

Database Tables:
    assignments - Links assessments to courses with scheduling info

Note:
    The open_at and due_at fields control when students can access and
    must complete the assignment. Submissions created before open_at
    cannot be started until that timestamp.
"""

from django.db import models

from accounts.models import User
from assessments.models import Assessment
from courses.models import Course


class AudienceType(models.TextChoices):
    """
    Enumeration identifying the target audience for an assignment.

    Determines who receives submissions when an assignment is created.

    Values:
        COURSE: All students in the specified course receive submissions
        TEACHER: Only the creating teacher receives a submission (self-assessment)
    """

    COURSE = "COURSE", "Course"
    TEACHER = "TEACHER", "Teacher"


class Assignment(models.Model):
    """
    Links an assessment template to a course for distribution.

    Assignments schedule when students can access and complete an assessment.
    Creating an assignment automatically generates empty Submission records
    for all enrolled students (for COURSE type) or the teacher (for TEACHER type).

    Attributes:
        assessment: The assessment template being assigned
        audience_type: Who receives the assignment (COURSE or TEACHER)
        course: Target course (required for COURSE type, null for TEACHER)
        created_by: User who created the assignment (PROTECT on delete)
        open_at: When students can begin the assessment
        due_at: Optional deadline for submission (null = no deadline)
        teacher: For TEACHER type, the teacher taking the self-assessment

    Related Models:
        submissions: Submission instances for this assignment

    Delete Behavior:
        - Deleting assessment: Cascades to delete assignments
        - Deleting course: Sets course to NULL (keeps assignment)
        - Deleting created_by user: PROTECT prevents deletion
        - Deleting teacher: Sets teacher to NULL
    """

    # The assessment template being distributed
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, db_column="assessment_id", related_name="assignments"
    )

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

    # When the assessment becomes available to students
    open_at = models.DateTimeField()

    # Optional deadline (null means no deadline)
    due_at = models.DateTimeField(null=True, blank=True)

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

    def __str__(self):
        """Return a readable string representation."""
        return f"Assignment({self.id})"
