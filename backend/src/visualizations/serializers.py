"""
Visualization serializers.

This module provides DRF serializers for the teacher dashboard visualization
endpoints. The visualization service aggregates submission data for charts
and graphs based on filter criteria.

All filter fields are optional, allowing flexible aggregation:
    - By course: Performance across all students in a course
    - By assessment: Response patterns for a specific assessment
    - By student: Individual progress tracking
    - Mood meter: Emotional trends over time
"""

from rest_framework import serializers


class VisualizationFilterSerializer(serializers.Serializer):
    """
    Validates filter parameters for visualization data requests.

    All fields are optional - omitting a filter means "include all."
    Multiple filters can be combined for more specific queries.

    Fields:
        studentId: Filter to a specific student's submissions
        courseId: Filter to a specific course's data
        category: Filter by assessment category
        assessmentId: Filter to a specific assessment's responses
        teacherId: Filter by teacher who created assignments
        isMoodMeter: If True, return mood meter specific aggregations

    Example Combinations:
        courseId only: All submissions for a course (for teacher dashboard)
        studentId + courseId: One student's work in a specific course
        isMoodMeter=True: Mood meter trends across all data
    """

    studentId = serializers.IntegerField(required=False, allow_null=True)
    courseId = serializers.IntegerField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    assessmentId = serializers.IntegerField(required=False, allow_null=True)
    teacherId = serializers.IntegerField(required=False, allow_null=True)
    isMoodMeter = serializers.BooleanField(required=False)
