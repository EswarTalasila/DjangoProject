"""
AssignmentTemplate and question models for defining evaluation templates.

Model Hierarchy:
    AssignmentTemplate
        ├── AssignmentTemplateQuestionGroup (optional grouping with rubric)
        └── Question (base)
            ├── MultipleChoiceQuestion (1:1 extension)
            │   ├── McqChoice (1:N choices)
            │   └── McqCorrectAnswer (1:N correct indices)
            ├── ShortAnswerQuestion (1:1 extension)
            └── NumberScaleQuestion (1:1 extension)
"""

from django.db import models

from accounts.models import User


class GradingMode(models.TextChoices):
    AUTO = "AUTO", "Auto"
    MANUAL = "MANUAL", "Manual"
    HYBRID = "HYBRID", "Hybrid"
    MOOD_METER = "MOOD_METER", "Mood Meter"


class GradingStrategy(models.TextChoices):
    AUTO = "AUTO", "Auto"
    MANUAL = "MANUAL", "Manual"


class AssignmentTemplateStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class ScoringPolicy(models.TextChoices):
    STANDARD = "STANDARD", "Standard"
    COMPLETION = "COMPLETION", "Completion"


class SubmissionMode(models.TextChoices):
    DIGITAL = "DIGITAL", "Digital"
    UPLOAD_ONLY = "UPLOAD_ONLY", "Upload Only"
    DIGITAL_WITH_UPLOAD = "DIGITAL_WITH_UPLOAD", "Digital with Upload"


class AssignmentTemplate(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=255, null=True, blank=True)
    grading_mode = models.CharField(max_length=255, choices=GradingMode.choices)
    submission_mode = models.CharField(
        max_length=32,
        choices=SubmissionMode.choices,
        default=SubmissionMode.DIGITAL,
    )
    scoring_policy = models.CharField(
        max_length=32,
        choices=ScoringPolicy.choices,
        default=ScoringPolicy.STANDARD,
    )
    # Optional whole-template rubric. When set, this rubric applies to the
    # entire assignment template rather than individual questions or groups.
    rubric = models.ForeignKey(
        "rubrics.Rubric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_templates",
    )
    created_by_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, db_column="created_by_admin_id"
    )
    status = models.CharField(
        max_length=16,
        choices=AssignmentTemplateStatus.choices,
        default=AssignmentTemplateStatus.ACTIVE,
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_assignment_templates",
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_assignment_templates",
    )
    has_been_used = models.BooleanField(
        default=False,
        help_text="Whether any assignment has ever been created from this template.",
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="First time an assignment was created from this template.",
    )

    class Meta:
        db_table = "assignment_templates"
        indexes = [
            models.Index(fields=["status"], name="idx_assignment_template_status"),
            models.Index(fields=["has_been_used"], name="idx_atmpl_used_flag"),
            models.Index(fields=["used_at"], name="idx_atmpl_used_at"),
        ]

    def __str__(self):
        return self.title


class AssignmentTemplateQuestionGroup(models.Model):
    assignment_template = models.ForeignKey(
        AssignmentTemplate, on_delete=models.CASCADE, related_name="question_groups"
    )
    name = models.CharField(max_length=255)
    rubric = models.ForeignKey(
        "rubrics.Rubric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_groups",
    )
    order_index = models.IntegerField(default=0)

    class Meta:
        db_table = "assignment_template_question_groups"

    def __str__(self):
        return f"{self.assignment_template.title}: {self.name}"


class QuestionKind(models.TextChoices):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    NUMBER_SCALE = "NUMBER_SCALE", "Number Scale"
    MOOD_METER = "MOOD_METER", "Mood Meter"
    FILE_UPLOAD = "FILE_UPLOAD", "File Upload"


class Question(models.Model):
    question_type = models.CharField(max_length=31)
    kind = models.CharField(max_length=255, choices=QuestionKind.choices, db_column="type")
    assignment_template = models.ForeignKey(
        AssignmentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="assignment_template_id",
        related_name="questions",
    )
    prompt = models.TextField()
    max_points = models.FloatField()
    auto_gradable = models.BooleanField(default=False)
    graded = models.BooleanField(default=False)
    image = models.TextField(null=True, blank=True)

    question_group = models.ForeignKey(
        AssignmentTemplateQuestionGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    rubric = models.ForeignKey(
        "rubrics.Rubric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    grading_strategy = models.CharField(
        max_length=10,
        choices=GradingStrategy.choices,
        default=GradingStrategy.AUTO,
    )

    class Meta:
        db_table = "questions"

    def __str__(self):
        return f"{self.kind}: {self.prompt[:32]}"


class MultipleChoiceQuestion(models.Model):
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="multiple_choice",
    )
    select_all = models.BooleanField(default=False)

    class Meta:
        db_table = "multiple_choice_question"

    def __str__(self):
        return f"MCQ({self.question_id})"


class ShortAnswerQuestion(models.Model):
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="short_answer",
    )
    case_sensitive = models.BooleanField(default=False)
    trim = models.BooleanField(default=True)

    class Meta:
        db_table = "short_answer_question"

    def __str__(self):
        return f"ShortAnswer({self.question_id})"


class NumberScaleQuestion(models.Model):
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="number_scale",
    )
    min = models.IntegerField()
    max = models.IntegerField()
    target = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "number_scale_question"

    def __str__(self):
        return f"NumberScale({self.question_id})"


class McqChoice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, db_column="question_id", related_name="mcq_choices"
    )
    choice_text = models.CharField(max_length=255)
    points = models.IntegerField()

    class Meta:
        db_table = "mcq_choices"

    def __str__(self):
        return f"Choice({self.question_id})"


class McqCorrectAnswer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        db_column="question_id",
        related_name="mcq_correct_answers",
    )
    correct_index = models.IntegerField()

    class Meta:
        db_table = "mcq_correct_answers"

    def __str__(self):
        return f"Correct({self.question_id}:{self.correct_index})"
