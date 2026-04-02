"""
Submission and answer models for student work.

This module defines the models that store student responses to assessments.
When an assignment is created, empty submissions are generated for each
enrolled student. Students then fill in answers and submit their work.

Model Hierarchy:
    Submission (student's work for an assignment)
        └── Answer (base)
            ├── MultipleChoiceAnswer (1:1 extension)
            │   └── MultipleChoiceSelected (1:N selected choices)
            ├── ShortAnswerAnswer (1:1 extension)
            └── NumberScaleAnswer (1:1 extension)

    Response (legacy survey-style response, may be deprecated)

Submission Lifecycle:
    NOT_STARTED → IN_PROGRESS → SUBMITTED → GRADED

Database Tables:
    submissions, answer, multiple_choice_answer, multiple_choice_selected,
    short_answer_answer, number_scale_answer, response

Note:
    Submissions are pre-created when assignments are made. Students cannot
    create their own submissions - they can only update existing ones.
"""

import uuid

from django.db import models

from accounts.models import User
from assessments.models import Question
from assignments.models import Assignment


class SubmissionStatus(models.TextChoices):
    """
    Enumeration of submission lifecycle states.

    Tracks the progress of a student's work through the assessment process.

    Values:
        NOT_STARTED: Submission created but student hasn't begun
        IN_PROGRESS: Student has started but not finished
        SUBMITTED: Student has submitted for grading
        GRADED: Teacher has reviewed and assigned a score
    """

    NOT_STARTED = "NOT_STARTED", "Not Started"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    GRADED = "GRADED", "Graded"


class Submission(models.Model):
    """
    A student's work for a specific assignment.

    Submissions are pre-created when a teacher assigns an assessment to a course.
    Each enrolled student gets one submission per assignment. Students update
    their submission by adding answers and eventually submitting for grading.

    Attributes:
        assignment: The assignment this submission is for
        score: Total score after grading (null until graded)
        status: Current lifecycle state (NOT_STARTED, IN_PROGRESS, etc.)
        student: Student who owns this submission (null for TEACHER assignments)
        teacher: Teacher for TEACHER-type assignments (null for COURSE type)
        submitted_at: Timestamp when student submitted (null until submitted)

    Related Models:
        answers: Answer instances containing the student's responses

    Note:
        Either student OR teacher will be set, not both, depending on
        the assignment's audience_type.
    """

    # The assignment this submission belongs to
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, db_column="assignment_id", related_name="submissions"
    )

    # Total score (sum of answer scores), null until graded
    score = models.FloatField(null=True, blank=True)

    # Current submission status
    status = models.CharField(max_length=255, choices=SubmissionStatus.choices)

    # For COURSE assignments: the student completing the work
    student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="student_id",
        related_name="student_submissions",
    )

    # For TEACHER assignments: the teacher doing self-assessment
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="teacher_id",
        related_name="teacher_submissions",
    )

    # When the submission was finalized (null until submitted)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Database table configuration for Submission."""

        db_table = "submissions"
        constraints = [
            # Exactly one of student or teacher must be set (XOR).
            models.CheckConstraint(
                condition=(
                    models.Q(student_id__isnull=False, teacher_id__isnull=True)
                    | models.Q(student_id__isnull=True, teacher_id__isnull=False)
                ),
                name="ck_submission_owner_xor",
            ),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"Submission({self.id})"


class AnswerType(models.TextChoices):
    """
    Enumeration of answer types (mirrors QuestionKind).

    Used as a discriminator to determine which extension model
    contains the answer data.

    Values:
        MULTIPLE_CHOICE: Selection from options (MultipleChoiceAnswer)
        SHORT_ANSWER: Free-text response (ShortAnswerAnswer)
        NUMBER_SCALE: Numeric rating (NumberScaleAnswer)
    """

    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    NUMBER_SCALE = "NUMBER_SCALE", "Number Scale"
    MOOD_METER = "MOOD_METER", "Mood Meter"


class Answer(models.Model):
    """
    Base answer model for student responses to questions.

    Each answer corresponds to one question in the assessment. The answer_type
    determines which extension model contains the actual response data.

    Attributes:
        answer_type: Discriminator for the answer subtype
        question: The question being answered
        submission: The submission this answer belongs to
        score: Points earned for this answer (null until graded)
        skipped: Whether the student chose to skip this question

    Related Models:
        multiple_choice: MultipleChoiceAnswer (if answer_type=MULTIPLE_CHOICE)
        short_answer: ShortAnswerAnswer (if answer_type=SHORT_ANSWER)
        number_scale: NumberScaleAnswer (if answer_type=NUMBER_SCALE)
    """

    # Discriminator for which extension model to use
    answer_type = models.CharField(max_length=31, choices=AnswerType.choices)

    # The question being answered
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, db_column="question_id", related_name="answers"
    )

    # Parent submission containing this answer
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        db_column="submission_id",
        related_name="answers",
    )

    # Points earned for this answer (null until graded)
    score = models.FloatField(null=True, blank=True)

    # Whether the student intentionally skipped this question
    skipped = models.BooleanField(default=False)

    class Meta:
        """Database table configuration for Answer."""

        db_table = "answer"

    def __str__(self):
        """Return a readable string representation."""
        return f"Answer({self.id})"


class MultipleChoiceAnswer(models.Model):
    """
    Extension model for MULTIPLE_CHOICE answer responses.

    The actual selected choices are stored in MultipleChoiceSelected,
    as there can be multiple selections for "select all that apply" questions.

    Attributes:
        answer: One-to-one link to base Answer (also primary key)

    Related Models:
        selected: MultipleChoiceSelected instances for chosen options
    """

    # Link to base answer (shares the same primary key)
    answer = models.OneToOneField(
        Answer,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="multiple_choice",
    )

    class Meta:
        """Database table configuration for MultipleChoiceAnswer."""

        db_table = "multiple_choice_answer"

    def __str__(self):
        """Return a readable string representation."""
        return f"MCAnswer({self.answer_id})"


class MultipleChoiceSelected(models.Model):
    """
    Records which choice(s) a student selected for a multiple-choice question.

    Each record represents one selected option. For single-select questions,
    there will be one record. For "select all that apply", there may be multiple.

    Attributes:
        answer: Parent MultipleChoiceAnswer this selection belongs to
        choice_index: 0-based index into the question's McqChoice list

    Note:
        The choice_index can be null if the student hasn't selected anything yet.
    """

    # Parent answer (CASCADE deletes selections when answer is deleted)
    answer = models.ForeignKey(
        MultipleChoiceAnswer,
        on_delete=models.CASCADE,
        db_column="answer_id",
        related_name="selected",
    )

    # 0-based index into the question's mcq_choices list
    choice_index = models.IntegerField(null=True, blank=True)

    class Meta:
        """Database table configuration for MultipleChoiceSelected."""

        db_table = "multiple_choice_selected"

    def __str__(self):
        """Return a readable string representation."""
        return f"MCSelected({self.answer_id}:{self.choice_index})"


class ShortAnswerAnswer(models.Model):
    """
    Extension model for SHORT_ANSWER responses.

    Contains the free-text response entered by the student.

    Attributes:
        answer: One-to-one link to base Answer (also primary key)
        text: The student's text response (max 255 characters)
    """

    # Link to base answer (shares the same primary key)
    answer = models.OneToOneField(
        Answer,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="short_answer",
    )

    # The student's free-text response
    text = models.CharField(max_length=255)

    class Meta:
        """Database table configuration for ShortAnswerAnswer."""

        db_table = "short_answer_answer"

    def __str__(self):
        """Return a readable string representation."""
        return f"ShortAnswer({self.answer_id})"


class NumberScaleAnswer(models.Model):
    """
    Extension model for NUMBER_SCALE responses.

    Contains the numeric value selected by the student within the
    question's defined min/max range.

    Attributes:
        answer: One-to-one link to base Answer (also primary key)
        val: The numeric value selected (null if not yet answered)
    """

    # Link to base answer (shares the same primary key)
    answer = models.OneToOneField(
        Answer,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="number_scale",
    )

    # The student's selected value (should be within question's min/max)
    val = models.IntegerField(null=True, blank=True)

    class Meta:
        """Database table configuration for NumberScaleAnswer."""

        db_table = "number_scale_answer"

    def __str__(self):
        """Return a readable string representation."""
        return f"NumberScaleAnswer({self.answer_id})"


class MoodMeterAnswer(models.Model):
    """
    Extension model for MOOD_METER responses.

    Stores the selected mood as a quadrant + mood name from the Yale RULER
    mood meter grid. Quadrants represent energy (high/low) × pleasantness (high/low).

    Attributes:
        answer: One-to-one link to base Answer (also primary key)
        quadrant: Which quadrant the selected mood belongs to
        mood_name: The specific mood label selected (e.g., "Excited", "Calm")
        row: Grid row position (0-9)
        col: Grid column position (0-9)
    """

    answer = models.OneToOneField(
        Answer,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="mood_meter",
    )

    quadrant = models.CharField(max_length=64, blank=True, default="")
    mood_name = models.CharField(max_length=64, blank=True, default="")
    row = models.IntegerField(null=True, blank=True)
    col = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mood_meter_answer"

    def __str__(self):
        return f"MoodMeterAnswer({self.answer_id}: {self.mood_name})"


class ImageStatus(models.TextChoices):
    """Status lifecycle for submission images (FR-15 IMG)."""

    PENDING_SCAN = "PENDING_SCAN", "Pending Scan"
    READY = "READY", "Ready"
    REJECTED = "REJECTED", "Rejected"
    DELETED = "DELETED", "Deleted"


class SubmissionImage(models.Model):
    """Image attached to a submission (FR-15 IMG)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        db_column="submission_id",
        related_name="images",
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        db_column="uploaded_by_user_id",
        related_name="uploaded_images",
    )
    submission_owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        db_column="submission_owner_user_id",
        related_name="owned_submission_images",
    )
    # Link to the shared ImageAsset (nullable during migration transition)
    asset = models.ForeignKey(
        "core.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="asset_id",
        related_name="submission_images",
    )
    # Blob metadata kept on SubmissionImage for backward compatibility
    storage_key = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    sha256_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=ImageStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "submission_image"
        indexes = [
            models.Index(fields=["submission", "status"], name="idx_subimg_sub_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0),
                name="ck_subimg_size_positive",
            ),
            models.UniqueConstraint(
                fields=["submission", "sha256_hash"],
                condition=~models.Q(status="DELETED"),
                name="uq_subimg_hash_active",
            ),
        ]

    def __str__(self):
        return f"SubmissionImage({self.id})"


class Response(models.Model):
    """
    Legacy survey-style response model (may be deprecated).

    This model appears to be a simplified response format that doesn't
    require the full Submission/Answer hierarchy. It may be used for
    quick surveys or standalone questions.

    Attributes:
        question: The question being responded to
        respondent: The user who submitted this response
        skipped: Whether the respondent chose to skip
        submitted_at: When the response was submitted

    Note:
        This model may be deprecated in favor of the Submission/Answer
        system. Check usage before relying on it.
    """

    # The question being answered
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="question_id",
        related_name="responses",
    )

    # User who submitted this response
    respondent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="respondent_id",
        related_name="responses",
    )

    # Whether the respondent skipped this question
    skipped = models.BooleanField(null=True, blank=True)

    # When the response was submitted
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Database table configuration for Response."""

        db_table = "response"

    def __str__(self):
        """Return a readable string representation."""
        return f"Response({self.id})"
