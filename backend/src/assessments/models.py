"""
Assessment and question models for defining evaluation templates.

Model Hierarchy:
    Assessment
        ├── AssessmentQuestionGroup (optional grouping with rubric)
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


class AssessmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class ScoringPolicy(models.TextChoices):
    STANDARD = "STANDARD", "Standard"
    COMPLETION = "COMPLETION", "Completion"


class Assessment(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=255, null=True, blank=True)
    grading_mode = models.CharField(max_length=255, choices=GradingMode.choices)
    scoring_policy = models.CharField(
        max_length=32,
        choices=ScoringPolicy.choices,
        default=ScoringPolicy.STANDARD,
    )
    created_by_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, db_column="created_by_admin_id"
    )
    status = models.CharField(
        max_length=16,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.ACTIVE,
    )

    class Meta:
        db_table = "assessments"

    def __str__(self):
        return self.title


class AssessmentQuestionGroup(models.Model):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="question_groups"
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
        db_table = "assessment_question_groups"

    def __str__(self):
        return f"{self.assessment.title}: {self.name}"


class QuestionKind(models.TextChoices):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    NUMBER_SCALE = "NUMBER_SCALE", "Number Scale"


class Question(models.Model):
    question_type = models.CharField(max_length=31)
    kind = models.CharField(max_length=255, choices=QuestionKind.choices, db_column="type")
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="assessment_id",
        related_name="questions",
    )
    prompt = models.TextField()
    max_points = models.FloatField()
    auto_gradable = models.BooleanField(default=False)
    graded = models.BooleanField(default=False)
    image = models.TextField(null=True, blank=True)

    question_group = models.ForeignKey(
        AssessmentQuestionGroup,
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

