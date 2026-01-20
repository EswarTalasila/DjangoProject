"""
Assessment and question models for defining evaluation templates.

This module defines the Assessment model (templates) and various Question types
that make up assessments. Assessments are created by admins and can be assigned
to courses by teachers.

Model Hierarchy:
    Assessment
        └── Question (base)
            ├── MultipleChoiceQuestion (1:1 extension)
            │   ├── McqChoice (1:N choices)
            │   └── McqCorrectAnswer (1:N correct indices)
            ├── ShortAnswerQuestion (1:1 extension)
            ├── NumberScaleQuestion (1:1 extension)
            └── MoodMeterQuestion (1:1 extension)
                └── MoodMeterLabel (1:N quadrant labels)

Question Types:
    MULTIPLE_CHOICE: Select one or more options from a list
    SHORT_ANSWER: Free-text response with optional auto-grading
    NUMBER_SCALE: Numeric rating within a min/max range
    MOOD_METER: 2D grid for emotional state tracking (energy x pleasantness)

Grading Modes:
    AUTO: Questions are auto-graded based on correct answers
    MANUAL: Teacher manually grades all responses
    HYBRID: Mix of auto and manual grading
    RUBRIC: Graded against a linked rubric assessment
    REFLECTION: Self-reflection with no grading
    MOOD_METER: Special mode for mood tracking assessments

Database Tables:
    assessments, questions, multiple_choice_question, short_answer_question,
    number_scale_question, mood_meter_question, mcq_choices, mcq_correct_answers,
    mood_meter_labels
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models

from accounts.models import User


class GradingMode(models.TextChoices):
    """
    Enumeration of grading modes supported by assessments.

    Determines how student responses are evaluated and scored.

    Values:
        AUTO: System automatically grades based on correct answers
        MANUAL: Teacher reviews and assigns points to each response
        HYBRID: Some questions auto-graded, others manual
        RUBRIC: Graded against criteria in a linked rubric assessment
        REFLECTION: No points assigned, used for self-reflection
        MOOD_METER: Special mode for emotional state tracking
    """

    AUTO = "AUTO", "Auto"
    MANUAL = "MANUAL", "Manual"
    HYBRID = "HYBRID", "Hybrid"
    RUBRIC = "RUBRIC", "Rubric"
    REFLECTION = "REFLECTION", "Reflection"
    MOOD_METER = "MOOD_METER", "Mood Meter"


class Assessment(models.Model):
    """
    Template containing questions that can be assigned to courses.

    Assessments are created by admins and serve as reusable templates.
    Teachers assign assessments to their courses, which creates submissions
    for enrolled students.

    Attributes:
        title: Display name of the assessment
        category: Optional grouping category for organization
        grading_mode: How responses should be evaluated (AUTO, MANUAL, etc.)
        created_by_admin: Admin who created this assessment (PROTECT on delete)
        rubric: Optional link to another assessment used as grading rubric
        rubric_assessment_ids: Array of assessment IDs for complex rubrics

    Related Models:
        questions: Question instances belonging to this assessment
        assignments: Assignment instances distributing this assessment

    Note:
        Updating an assessment after submissions exist may corrupt
        historical data (see issue #25).
    """

    # Display name shown to students and teachers
    title = models.CharField(max_length=255)

    # Optional category for grouping/filtering assessments
    category = models.CharField(max_length=255, null=True, blank=True)

    # How student responses should be evaluated
    grading_mode = models.CharField(max_length=255, choices=GradingMode.choices)

    # Admin who created this assessment (cannot be deleted while assessment exists)
    created_by_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, db_column="created_by_admin_id"
    )

    # Optional link to a rubric assessment for RUBRIC grading mode
    rubric = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="rubric_id",
        related_name="rubric_children",
    )

    # PostgreSQL array of assessment IDs for complex multi-rubric scenarios
    rubric_assessment_ids = ArrayField(
        models.BigIntegerField(), default=list, blank=True, null=True
    )

    class Meta:
        """Database table configuration for Assessment."""

        db_table = "assessments"

    def __str__(self):
        """Return a readable string representation."""
        return self.title


class QuestionKind(models.TextChoices):
    """
    Enumeration of supported question types.

    Each kind has a corresponding extension model with type-specific settings.

    Values:
        MULTIPLE_CHOICE: Select from predefined options (McqChoice)
        SHORT_ANSWER: Free-text response with optional matching
        NUMBER_SCALE: Numeric rating within defined range
        MOOD_METER: 2D emotional state grid selection
    """

    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    NUMBER_SCALE = "NUMBER_SCALE", "Number Scale"
    MOOD_METER = "MOOD_METER", "Mood Meter"


class Question(models.Model):
    """
    Base question model shared by all question types.

    This is the parent model for questions. Each question has a kind that
    determines which extension model (MultipleChoiceQuestion, etc.) contains
    the type-specific settings.

    Attributes:
        question_type: Discriminator for JPA inheritance (legacy)
        kind: The type of question (from QuestionKind enum)
        assessment: Parent assessment this question belongs to
        prompt: The question text shown to students
        max_points: Maximum points achievable for this question
        auto_gradable: Whether this question can be auto-graded
        graded: Whether points should be assigned for this question
        image: Optional base64-encoded image or URL for the question

    Related Models:
        multiple_choice: MultipleChoiceQuestion extension (if kind=MULTIPLE_CHOICE)
        short_answer: ShortAnswerQuestion extension (if kind=SHORT_ANSWER)
        number_scale: NumberScaleQuestion extension (if kind=NUMBER_SCALE)
        mood_meter: MoodMeterQuestion extension (if kind=MOOD_METER)
        mcq_choices: McqChoice options (for multiple choice)
        mcq_correct_answers: McqCorrectAnswer indices (for multiple choice)
        mood_meter_labels: MoodMeterLabel quadrant labels (for mood meter)
    """

    # Discriminator field for JPA inheritance mapping (legacy from Java)
    question_type = models.CharField(max_length=31)

    # The type of question (determines which extension model to use)
    kind = models.CharField(max_length=255, choices=QuestionKind.choices, db_column="type")

    # Parent assessment (SET_NULL allows orphan questions during editing)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="assessment_id",
        related_name="questions",
    )

    # The question text displayed to students
    prompt = models.TextField()

    # Maximum points for correct answer
    max_points = models.FloatField()

    # Whether the system can automatically grade responses
    auto_gradable = models.BooleanField(default=False)

    # Whether this question should be scored (false for reflection questions)
    graded = models.BooleanField(default=False)

    # Optional image (base64 or URL) displayed with the question
    image = models.TextField(null=True, blank=True)

    class Meta:
        """Database table configuration for Question."""

        db_table = "questions"

    def __str__(self):
        """Return a readable string representation."""
        return f"{self.kind}: {self.prompt[:32]}"


class MultipleChoiceQuestion(models.Model):
    """
    Extension model for MULTIPLE_CHOICE questions.

    Contains settings specific to multiple choice questions. The actual
    choices are stored in McqChoice, and correct answers in McqCorrectAnswer.

    Attributes:
        question: One-to-one link to base Question (also primary key)
        select_all: If True, allows selecting multiple answers ("select all that apply")

    Related Models:
        question.mcq_choices: The available choices for this question
        question.mcq_correct_answers: Indices of correct choices
    """

    # Link to base question (shares the same primary key)
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="multiple_choice",
    )

    # Whether multiple choices can be selected (select all that apply)
    select_all = models.BooleanField(default=False)

    class Meta:
        """Database table configuration for MultipleChoiceQuestion."""

        db_table = "multiple_choice_question"

    def __str__(self):
        """Return a readable string representation."""
        return f"MCQ({self.question_id})"


class ShortAnswerQuestion(models.Model):
    """
    Extension model for SHORT_ANSWER questions.

    Contains settings that control how free-text responses are compared
    against expected answers for auto-grading.

    Attributes:
        question: One-to-one link to base Question (also primary key)
        case_sensitive: If True, answer comparison is case-sensitive
        trim: If True, leading/trailing whitespace is ignored in comparison
    """

    # Link to base question (shares the same primary key)
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="short_answer",
    )

    # Whether answer matching should be case-sensitive
    case_sensitive = models.BooleanField(default=False)

    # Whether to strip whitespace before comparing answers
    trim = models.BooleanField(default=True)

    class Meta:
        """Database table configuration for ShortAnswerQuestion."""

        db_table = "short_answer_question"

    def __str__(self):
        """Return a readable string representation."""
        return f"ShortAnswer({self.question_id})"


class NumberScaleQuestion(models.Model):
    """
    Extension model for NUMBER_SCALE questions.

    Contains settings for numeric rating questions (e.g., "Rate 1-5").
    Used for Likert scales, satisfaction ratings, etc.

    Attributes:
        question: One-to-one link to base Question (also primary key)
        min: Minimum allowed value on the scale
        max: Maximum allowed value on the scale
        target: Optional "correct" value for auto-grading (null = no auto-grade)
    """

    # Link to base question (shares the same primary key)
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="number_scale",
    )

    # Minimum value on the scale (inclusive)
    min = models.IntegerField()

    # Maximum value on the scale (inclusive)
    max = models.IntegerField()

    # Optional target value for auto-grading (null = manual grading only)
    target = models.IntegerField(null=True, blank=True)

    class Meta:
        """Database table configuration for NumberScaleQuestion."""

        db_table = "number_scale_question"

    def __str__(self):
        """Return a readable string representation."""
        return f"NumberScale({self.question_id})"


class MoodMeterQuestion(models.Model):
    """
    Extension model for MOOD_METER questions.

    Mood meters are 2D grids for tracking emotional states along two axes:
    - X-axis: Pleasantness (negative to positive)
    - Y-axis: Energy (low to high)

    The four quadrants represent different emotional states:
    - High energy + Positive: Excited, enthusiastic
    - High energy + Negative: Angry, anxious
    - Low energy + Positive: Calm, content
    - Low energy + Negative: Sad, tired

    Attributes:
        question: One-to-one link to base Question (also primary key)

    Related Models:
        question.mood_meter_labels: Custom labels for the four quadrants
    """

    # Link to base question (shares the same primary key)
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="id",
        related_name="mood_meter",
    )

    class Meta:
        """Database table configuration for MoodMeterQuestion."""

        db_table = "mood_meter_question"

    def __str__(self):
        """Return a readable string representation."""
        return f"MoodMeter({self.question_id})"


class McqChoice(models.Model):
    """
    An answer option for a multiple-choice question.

    Stores the available choices that students can select. The points
    field allows partial credit for different choices.

    Attributes:
        question: Parent question this choice belongs to
        choice_text: The text displayed for this option
        points: Points awarded when this choice is selected

    Note:
        The order of choices is determined by the database insertion order.
        Correct answers are tracked separately in McqCorrectAnswer.
    """

    # Parent question (CASCADE deletes choices when question is deleted)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, db_column="question_id", related_name="mcq_choices"
    )

    # Text displayed for this answer option
    choice_text = models.CharField(max_length=255)

    # Points awarded when this choice is selected (can be 0 or negative)
    points = models.IntegerField()

    class Meta:
        """Database table configuration for McqChoice."""

        db_table = "mcq_choices"

    def __str__(self):
        """Return a readable string representation."""
        return f"Choice({self.question_id})"


class McqCorrectAnswer(models.Model):
    """
    Identifies which choice(s) are correct for a multiple-choice question.

    Stores indices (0-based) into the McqChoice list that represent
    correct answers. For "select all that apply" questions, there may
    be multiple correct indices.

    Attributes:
        question: Parent question this answer belongs to
        correct_index: 0-based index into the mcq_choices list

    Note:
        A question can have multiple McqCorrectAnswer records when
        the MultipleChoiceQuestion.select_all is True.
    """

    # Parent question (CASCADE deletes answers when question is deleted)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        db_column="question_id",
        related_name="mcq_correct_answers",
    )

    # 0-based index into the question's mcq_choices
    correct_index = models.IntegerField()

    class Meta:
        """Database table configuration for McqCorrectAnswer."""

        db_table = "mcq_correct_answers"

    def __str__(self):
        """Return a readable string representation."""
        return f"Correct({self.question_id}:{self.correct_index})"


class MoodMeterLabel(models.Model):
    """
    Custom label for a mood meter quadrant.

    Mood meters have four quadrants, and each can have a custom label.
    Labels are stored in order: top-right, top-left, bottom-left, bottom-right
    (or similar convention based on implementation).

    Attributes:
        question: Parent mood meter question this label belongs to
        label: Custom text label for the quadrant (optional)

    Note:
        If no custom labels are provided, default labels are used
        based on the standard mood meter quadrant names.
    """

    # Parent question (CASCADE deletes labels when question is deleted)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        db_column="question_id",
        related_name="mood_meter_labels",
    )

    # Custom label text for this quadrant (null uses default label)
    label = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        """Database table configuration for MoodMeterLabel."""

        db_table = "mood_meter_labels"

    def __str__(self):
        """Return a readable string representation."""
        return f"MoodLabel({self.question_id})"
