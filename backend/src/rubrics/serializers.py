"""Rubric serializers."""

from rest_framework import serializers


class RubricLevelSerializer(serializers.Serializer):
    """Serializer for a single rubric performance level with label, points, and description."""

    label = serializers.CharField(max_length=255)
    points = serializers.FloatField(min_value=0)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    orderIndex = serializers.IntegerField(required=False)


class RubricCriterionSerializer(serializers.Serializer):
    """Serializer for a rubric criterion with weighted scoring levels."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    orderIndex = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False, min_value=0.01, default=1.0)
    levels = RubricLevelSerializer(many=True, required=False)


class RubricSerializer(serializers.Serializer):
    """Top-level serializer for creating/updating a rubric with nested criteria."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    criteria = RubricCriterionSerializer(many=True, required=False)
