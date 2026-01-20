"""
Assignment serializers.

This module provides DRF serializers for assignment creation and scheduling.
Assignments link assessments to courses and define when students can access them.

Audience Types:
    COURSE: All students in a course receive the assignment
    TEACHER: Self-assessment for the specified teacher
"""

from rest_framework import serializers


class AssignmentSerializer(serializers.Serializer):
    """
    Validates assignment creation payloads.

    Creates a link between an assessment and a course (or teacher for
    self-assessments) with scheduling information.

    Fields:
        id: Optional assignment ID (for updates)
        assessmentId: The assessment template to assign (required)
        audienceType: "COURSE" or "TEACHER" (required)
        courseId: Target course (required for COURSE type)
        targetTeacherId: Target teacher (required for TEACHER type)
        openAt: When the assignment becomes available (required)
        dueAt: Optional deadline

    Validation Rules:
        - COURSE type requires courseId
        - TEACHER type requires targetTeacherId
        - openAt must be before dueAt (if dueAt provided)
    """

    id = serializers.IntegerField(required=False)
    assessmentId = serializers.IntegerField()
    audienceType = serializers.ChoiceField(choices=["COURSE", "TEACHER"])
    courseId = serializers.IntegerField(required=False, allow_null=True)
    targetTeacherId = serializers.IntegerField(required=False, allow_null=True)
    openAt = serializers.DateTimeField()
    dueAt = serializers.DateTimeField(required=False, allow_null=True)
