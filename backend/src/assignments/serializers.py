"""
Assignment serializers.

Provides DRF serializers for assignment creation and scheduling updates.
"""

from rest_framework import serializers


class AssignmentSerializer(serializers.Serializer):
    """Validates assignment creation payloads."""

    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=False, max_length=255)
    assignmentTemplateId = serializers.IntegerField()
    audienceType = serializers.ChoiceField(choices=["COURSE", "TEACHER"])
    courseId = serializers.IntegerField(required=False, allow_null=True)
    targetTeacherId = serializers.IntegerField(required=False, allow_null=True)
    openAt = serializers.DateTimeField()
    dueAt = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("audienceType") == "TEACHER":
            raise serializers.ValidationError(
                {"audienceType": "TEACHER audience type is deprecated and no longer accepted."}
            )
        due = attrs.get("dueAt")
        if due is not None and attrs["openAt"] >= due:
            raise serializers.ValidationError(
                {"openAt": "openAt must be before dueAt."}
            )
        return attrs


class AssignmentUpdateSerializer(serializers.Serializer):
    """Validates assignment scheduling update payloads (PATCH)."""

    title = serializers.CharField(required=False, allow_blank=False, max_length=255)
    openAt = serializers.DateTimeField(required=False)
    dueAt = serializers.DateTimeField(required=False, allow_null=True)


class AssignmentQuestionCreateSerializer(serializers.Serializer):
    """Validates teacher-authored assignment-local question payloads."""

    type = serializers.ChoiceField(
        choices=["MULTIPLE_CHOICE", "SHORT_ANSWER", "NUMBER_SCALE", "MOOD_METER"]
    )
    prompt = serializers.CharField(allow_blank=False)
    maxPoints = serializers.FloatField(min_value=0)
    data = serializers.DictField(required=False)  # type: ignore[assignment]
    gradingStrategy = serializers.ChoiceField(
        choices=["AUTO", "MANUAL"],
        required=False,
        default="AUTO",
    )


class AssignmentTeacherCriterionCreateSerializer(serializers.Serializer):
    """Validates teacher-authored assignment-local criterion payloads."""

    title = serializers.CharField(allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    weight = serializers.FloatField(min_value=0.01)


class AssignmentOrderedIdsSerializer(serializers.Serializer):
    """Validates reorder payloads that supply a full ordered ID list."""

    orderedIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class AssignmentTeacherCriterionLevelCreateSerializer(serializers.Serializer):
    """Validates teacher-authored rubric levels layered onto a local criterion."""

    label = serializers.CharField(allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    points = serializers.FloatField(min_value=0)
