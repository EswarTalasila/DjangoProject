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
from assignment_templates.models import (
    AssignmentTemplate,
    AssignmentTemplateQuestionGroup,
    GradingStrategy,
    Question,
    QuestionKind,
)
from core.media.models import ImageAsset
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


class AssignmentContentOrigin(models.TextChoices):
    """Source provenance for assignment-owned content rows."""

    TEMPLATE = "TEMPLATE", "Template"
    TEACHER_ADDITION = "TEACHER_ADDITION", "Teacher Addition"


class AssignmentQuestionGroup(models.Model):
    """Assignment-owned snapshot of a template question group or teacher group."""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="question_groups",
    )
    source_template_group = models.ForeignKey(
        AssignmentTemplateQuestionGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_group_snapshots",
    )
    name = models.CharField(max_length=255)
    order_index = models.IntegerField(default=0)
    origin = models.CharField(
        max_length=32,
        choices=AssignmentContentOrigin.choices,
        default=AssignmentContentOrigin.TEMPLATE,
    )
    locked_from_source = models.BooleanField(default=False)

    class Meta:
        """Database table configuration for AssignmentQuestionGroup."""

        db_table = "assignment_question_groups"
        indexes = [
            models.Index(fields=["assignment", "order_index"], name="idx_asgn_qgroup_order"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"AssignmentQuestionGroup({self.assignment_id}:{self.name})"


class AssignmentQuestion(models.Model):
    """Assignment-owned question snapshot used by submissions and archive/export flows."""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    source_template_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_question_snapshots",
    )
    question_group = models.ForeignKey(
        AssignmentQuestionGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_questions_created",
    )
    kind = models.CharField(max_length=255, choices=QuestionKind.choices, db_column="type")
    prompt = models.TextField()
    max_points = models.FloatField()
    auto_gradable = models.BooleanField(default=False)
    graded = models.BooleanField(default=False)
    image = models.TextField(null=True, blank=True)
    image_asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_questions",
    )
    grading_strategy = models.CharField(
        max_length=10,
        choices=GradingStrategy.choices,
        default=GradingStrategy.AUTO,
    )
    data = models.JSONField(default=dict, blank=True)
    order_index = models.IntegerField(default=0)
    origin = models.CharField(
        max_length=32,
        choices=AssignmentContentOrigin.choices,
        default=AssignmentContentOrigin.TEMPLATE,
    )
    locked_from_source = models.BooleanField(default=False)

    class Meta:
        """Database table configuration for AssignmentQuestion."""

        db_table = "assignment_questions"
        indexes = [
            models.Index(fields=["assignment", "order_index"], name="idx_asgn_question_order"),
            models.Index(fields=["origin"], name="idx_asgn_question_origin"),
        ]

    @property
    def question_type(self) -> str:
        """Compatibility alias matching the template Question API."""
        return self.kind

    @property
    def assignment_template_id(self) -> int | None:
        """Compatibility alias for legacy code and tests still keyed to template ownership."""
        return getattr(self.assignment, "assignment_template_id", None)

    @property
    def assignment_template(self):
        """Compatibility alias exposing the linked source template through the assignment."""
        return getattr(self.assignment, "assignment_template", None)

    def __str__(self):
        """Return a readable string representation."""
        return f"AssignmentQuestion({self.assignment_id}:{self.kind})"


class AssignmentTeacherCriterion(models.Model):
    """Teacher-authored rubric criteria layered on top of the researcher template."""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="teacher_criteria",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_teacher_criteria_created",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    weight = models.FloatField(default=1.0)
    order_index = models.IntegerField(default=0)

    class Meta:
        """Database table configuration for AssignmentTeacherCriterion."""

        db_table = "assignment_teacher_criteria"
        indexes = [
            models.Index(fields=["assignment", "order_index"], name="idx_asgn_criterion_order"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight__gt=0),
                name="ck_assignment_teacher_criterion_weight_positive",
            )
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"AssignmentTeacherCriterion({self.assignment_id}:{self.title})"


class AssignmentArchiveArtifact(models.Model):
    """Generated ZIP artifact for an archived assignment bundle."""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="archive_artifacts",
    )
    identifiable = models.BooleanField(default=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_assignment_archive_artifacts",
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512, unique=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256_hash = models.CharField(max_length=64)
    manifest = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Database table configuration for AssignmentArchiveArtifact."""

        db_table = "assignment_archive_artifacts"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "identifiable"],
                name="uq_assignment_archive_artifact_variant",
            )
        ]
        indexes = [
            models.Index(
                fields=["assignment", "generated_at"],
                name="idx_asgn_archive_artf",
            )
        ]

    def __str__(self):
        """Return a readable string representation."""
        variant = "identifiable" if self.identifiable else "anonymized"
        return f"AssignmentArchiveArtifact({self.assignment_id}:{variant})"
