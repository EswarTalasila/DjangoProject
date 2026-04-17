"""
Visualization query-param serializers (FR-09).

Replaces the legacy VisualizationFilterSerializer. Each endpoint gets its
own param serializer for query string validation.
"""

from rest_framework import serializers


class CourseSummaryParamsSerializer(serializers.Serializer):
    """Query params for VIZ-UC-02."""

    startDate = serializers.DateField(required=False, allow_null=True, default=None)
    endDate = serializers.DateField(required=False, allow_null=True, default=None)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    assignmentTemplateId = serializers.IntegerField(required=False, allow_null=True, default=None)


class AssignmentSummaryParamsSerializer(serializers.Serializer):
    """Query params for VIZ-UC-03."""

    startDate = serializers.DateField(required=False, allow_null=True, default=None)
    endDate = serializers.DateField(required=False, allow_null=True, default=None)
