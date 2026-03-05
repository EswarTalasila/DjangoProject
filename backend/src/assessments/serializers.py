"""Assessment serializers."""

from rest_framework import serializers

from .models import GradingMode, QuestionKind, ScoringPolicy


class MCQChoiceSerializer(serializers.Serializer):
    """Serializer for a single multiple-choice option with its point value."""

    prompt = serializers.CharField(max_length=255)
    score = serializers.FloatField()


class MultipleChoiceDataSerializer(serializers.Serializer):
    """Serializer for MCQ question data: list of choices and optional select-all flag."""

    choices = MCQChoiceSerializer(many=True)
    selectAll = serializers.BooleanField(required=False)


class ShortAnswerDataSerializer(serializers.Serializer):
    """Serializer for short-answer question configuration options."""

    caseSensitive = serializers.BooleanField(required=False)
    trim = serializers.BooleanField(required=False)


class NumberScaleDataSerializer(serializers.Serializer):
    """Serializer for number-scale question data: min/max range and optional target."""

    min = serializers.IntegerField()
    max = serializers.IntegerField()
    target = serializers.IntegerField(required=False, allow_null=True)


class QuestionSerializer(serializers.Serializer):
    """Serializer for a single assessment question with type, prompt, scoring, and optional rubric."""

    questionId = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=QuestionKind.choices)
    prompt = serializers.CharField()
    maxPoints = serializers.FloatField()
    data = serializers.DictField(required=False)  # type: ignore[assignment]
    groupClientKey = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    rubricId = serializers.IntegerField(required=False, allow_null=True)
    gradingStrategy = serializers.ChoiceField(
        choices=[("AUTO", "Auto"), ("MANUAL", "Manual")],
        required=False,
        default="AUTO",
    )


class QuestionGroupSerializer(serializers.Serializer):
    """Serializer for a named question group with an optional shared rubric."""

    clientKey = serializers.CharField()
    name = serializers.CharField(max_length=255)
    rubricId = serializers.IntegerField(required=False, allow_null=True)


class AssessmentSerializer(serializers.Serializer):
    """Top-level serializer for creating/updating an assessment with questions and groups."""

    id = serializers.IntegerField(required=False)
    title = serializers.CharField()
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gradingMode = serializers.ChoiceField(choices=GradingMode.choices)
    scoringPolicy = serializers.ChoiceField(
        choices=ScoringPolicy.choices,
        required=False,
        default=ScoringPolicy.STANDARD,
    )
    questions = QuestionSerializer(many=True, required=False)
    questionGroups = QuestionGroupSerializer(many=True, required=False)

    def validate(self, attrs):
        # Fail fast if legacy rubric fields are sent
        if self.initial_data and isinstance(self.initial_data, dict):
            legacy_fields = {"rubricId", "rubricAssessmentIds"}
            sent = legacy_fields & set(self.initial_data.keys())
            if sent:
                raise serializers.ValidationError(
                    {f: "Legacy field removed. Use per-question rubricId instead." for f in sent}
                )
        return attrs
