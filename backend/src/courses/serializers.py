"""
Course and student serializers.

This module provides DRF serializers for course and student management.
Courses contain enrolled students, and students are always created within
the context of a course.

Input Serializers (for request validation):
    CourseInputSerializer: Course creation/update
    StudentInputSerializer: Student creation with course enrollment

Output Serializers (for response formatting):
    CourseOutputSerializer: Full course details with student list
    StudentOutputSerializer: Student details with enrollment info
"""

from collections.abc import Mapping

from rest_framework import serializers


class StrictFieldsSerializer(serializers.Serializer):
    """Serializer base that rejects undeclared input fields."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = sorted(set(data.keys()) - set(self.fields.keys()))
            if unknown_fields:
                raise serializers.ValidationError(
                    {field: ["Unknown field."] for field in unknown_fields}
                )
        return super().to_internal_value(data)


class CourseInputSerializer(serializers.Serializer):
    """
    Validates course creation/update payloads.

    Fields:
        name: Course display name (e.g., "Math 101 - Period 3")
    """

    name = serializers.CharField(max_length=255)


class StudentNestedInputSerializer(StrictFieldsSerializer):
    """
    Validates student creation payloads for the nested course endpoint.

    courseId comes from the URL path parameter, not the request body.
    """

    name = serializers.CharField(max_length=255)
    consent = serializers.BooleanField(required=False)
    password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class CourseOutputSerializer(serializers.Serializer):
    """
    Formats course data for API responses.

    Includes enrolled students and associated assignments.

    Fields:
        id: Course database ID
        name: Display name
        students: List of enrolled student objects
        studentCount: Number of enrolled students
        assignmentIds: IDs of assignments for this course
        teacherId: ID of the teacher who owns this course
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    students = serializers.ListField(child=serializers.DictField())
    studentCount = serializers.IntegerField()
    assignmentIds = serializers.ListField(child=serializers.IntegerField())
    teacherId = serializers.IntegerField(allow_null=True)


class StudentInputSerializer(StrictFieldsSerializer):
    """
    Validates student creation payloads.

    Students are always created within the context of a course,
    so courseId is required.

    Fields:
        name: Student's display name
        consent: Data collection consent flag
        courseId: Course to enroll the student in (required)
        password: Optional password (generated if not provided)
    """

    name = serializers.CharField(max_length=255)
    consent = serializers.BooleanField(required=False)
    courseId = serializers.IntegerField()
    password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class StudentOutputSerializer(serializers.Serializer):
    """
    Formats student data for API responses.

    Fields:
        id: Student's user ID
        name: Display name
        username: Student login identifier
        role: Always "STUDENT" for students
        consent: Data collection consent status
        courseId: ID of the course they're enrolled in (context-dependent)
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    username = serializers.CharField()
    role = serializers.CharField()
    consent = serializers.BooleanField()
    courseId = serializers.IntegerField(allow_null=True)
