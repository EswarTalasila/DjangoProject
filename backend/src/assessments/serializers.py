"""
Assessment serializers.

This module provides DRF serializers for assessment creation and management.
Assessments are templates containing questions that can be assigned to courses.

Serializer Hierarchy:
    AssessmentSerializer
        └── QuestionSerializer
            └── data (DictField containing type-specific config)
                ├── MultipleChoiceDataSerializer
                ├── ShortAnswerDataSerializer
                ├── NumberScaleDataSerializer
                └── MoodMeterDataSerializer

The 'data' field in QuestionSerializer is a generic DictField that gets
validated/processed by the service layer based on the question type.
"""

from rest_framework import serializers

from .models import GradingMode, QuestionKind


class MCQChoiceSerializer(serializers.Serializer):
    """
    Validates a single multiple-choice option.

    Fields:
        prompt: The choice text displayed to students
        score: Points awarded when this choice is selected
    """

    prompt = serializers.CharField(max_length=255)
    score = serializers.FloatField()


class MultipleChoiceDataSerializer(serializers.Serializer):
    """
    Validates multiple-choice question configuration.

    Used within QuestionSerializer.data for MULTIPLE_CHOICE type.

    Fields:
        choices: List of MCQChoiceSerializer objects
        selectAll: Whether multiple selections are allowed
    """

    choices = MCQChoiceSerializer(many=True)
    selectAll = serializers.BooleanField(required=False)


class ShortAnswerDataSerializer(serializers.Serializer):
    """
    Validates short-answer question configuration.

    Used within QuestionSerializer.data for SHORT_ANSWER type.

    Fields:
        caseSensitive: Whether answer matching is case-sensitive
        trim: Whether to strip whitespace before comparing
    """

    caseSensitive = serializers.BooleanField(required=False)
    trim = serializers.BooleanField(required=False)


class NumberScaleDataSerializer(serializers.Serializer):
    """
    Validates number-scale question configuration.

    Used within QuestionSerializer.data for NUMBER_SCALE type.

    Fields:
        min: Minimum value on the scale
        max: Maximum value on the scale
        target: Optional correct answer for auto-grading
    """

    min = serializers.IntegerField()
    max = serializers.IntegerField()
    target = serializers.IntegerField(required=False, allow_null=True)


class MoodMeterDataSerializer(serializers.Serializer):
    """
    Validates mood-meter question configuration.

    Used within QuestionSerializer.data for MOOD_METER type.

    Fields:
        labels: Custom labels for the four quadrants
    """

    labels = serializers.ListField(child=serializers.CharField(), required=False)


class QuestionSerializer(serializers.Serializer):
    """
    Validates question payloads within an assessment.

    The 'data' field is a generic dict containing type-specific configuration.
    The service layer validates data against the appropriate *DataSerializer
    based on the question type.

    Fields:
        questionId: Optional ID for updates (null for new questions)
        type: Question type (MULTIPLE_CHOICE, SHORT_ANSWER, etc.)
        prompt: The question text
        maxPoints: Maximum points for this question
        data: Type-specific configuration (choices, scale range, etc.)
    """

    questionId = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=QuestionKind.choices)
    prompt = serializers.CharField()
    maxPoints = serializers.FloatField()
    data = serializers.DictField(required=False)  # type: ignore[assignment]


class AssessmentSerializer(serializers.Serializer):
    """
    Validates assessment creation/update payloads.

    Assessments are templates containing questions. Created by admins,
    they can be assigned to courses by teachers.

    Fields:
        id: Optional ID for updates (omit for new assessments)
        title: Display name of the assessment
        category: Optional grouping category
        gradingMode: How responses are evaluated (AUTO, MANUAL, etc.)
        questions: List of QuestionSerializer objects
        rubricId: Optional ID of a rubric assessment for grading
        rubricAssessmentIds: List of assessment IDs for complex rubrics
    """

    id = serializers.IntegerField(required=False)
    title = serializers.CharField()
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gradingMode = serializers.ChoiceField(choices=GradingMode.choices)
    questions = QuestionSerializer(many=True, required=False)
    rubricId = serializers.IntegerField(required=False, allow_null=True)
    rubricAssessmentIds = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
