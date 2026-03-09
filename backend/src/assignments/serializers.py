"""
Assignment serializers.

Provides DRF serializers for assignment creation and scheduling updates.
"""

from rest_framework import serializers


class AssignmentSerializer(serializers.Serializer):
    """Validates assignment creation payloads."""

    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=False, max_length=255)
    assessmentId = serializers.IntegerField()
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
