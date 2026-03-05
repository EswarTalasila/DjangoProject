"""Pure unit tests for course serializer validation (no database)."""

from __future__ import annotations

import pytest

from courses.serializers import (
    CourseInputSerializer,
    CourseOutputSerializer,
    StudentInputSerializer,
    StudentOutputSerializer,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# CourseInputSerializer
# ---------------------------------------------------------------------------


class TestCourseInputSerializer:
    """Tests for CourseInputSerializer validation."""

    def test_valid_name(self):
        """Accepts a valid course name."""
        s = CourseInputSerializer(data={"name": "Math 101"})
        assert s.is_valid()
        assert s.validated_data["name"] == "Math 101"

    def test_rejects_empty_name(self):
        """Rejects empty course name."""
        s = CourseInputSerializer(data={"name": ""})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_rejects_missing_name(self):
        """Rejects payload without name field."""
        s = CourseInputSerializer(data={})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_rejects_name_exceeding_max_length(self):
        """Rejects name exceeding 255 characters."""
        s = CourseInputSerializer(data={"name": "x" * 256})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_accepts_max_length_name(self):
        """Accepts name at exactly 255 characters."""
        s = CourseInputSerializer(data={"name": "x" * 255})
        assert s.is_valid()


# ---------------------------------------------------------------------------
# CourseOutputSerializer
# ---------------------------------------------------------------------------


class TestCourseOutputSerializer:
    """Tests for CourseOutputSerializer output formatting."""

    def test_serializes_full_course_output(self):
        """Serializes all CourseOutputSerializer fields."""
        data = {
            "id": 1,
            "name": "Science 202",
            "students": [{"id": 10, "name": "Alice"}],
            "studentCount": 1,
            "assignmentIds": [5, 6],
            "teacherId": 42,
        }
        s = CourseOutputSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_accepts_null_teacher_id(self):
        """Accepts null teacherId value."""
        data = {
            "id": 1,
            "name": "Course",
            "students": [],
            "studentCount": 0,
            "assignmentIds": [],
            "teacherId": None,
        }
        s = CourseOutputSerializer(data=data)
        assert s.is_valid()

    def test_rejects_missing_required_fields(self):
        """Rejects payload missing required output fields."""
        s = CourseOutputSerializer(data={})
        assert not s.is_valid()
        assert "id" in s.errors
        assert "name" in s.errors


# ---------------------------------------------------------------------------
# StudentInputSerializer (extends StrictFieldsSerializer)
# ---------------------------------------------------------------------------


class TestStudentInputSerializer:
    """Tests for StudentInputSerializer validation."""

    def test_valid_minimal_payload(self):
        """Accepts minimal valid student payload."""
        s = StudentInputSerializer(data={"name": "Alice", "courseId": 1})
        assert s.is_valid()
        assert s.validated_data["name"] == "Alice"
        assert s.validated_data["courseId"] == 1

    def test_valid_full_payload(self):
        """Accepts full student payload with all optional fields."""
        data = {
            "name": "Bob",
            "courseId": 2,
            "consent": True,
            "password": "secret123",
        }
        s = StudentInputSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["consent"] is True
        assert s.validated_data["password"] == "secret123"

    def test_rejects_missing_name(self):
        """Rejects payload without name."""
        s = StudentInputSerializer(data={"courseId": 1})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_rejects_missing_course_id(self):
        """Rejects payload without courseId."""
        s = StudentInputSerializer(data={"name": "Alice"})
        assert not s.is_valid()
        assert "courseId" in s.errors

    def test_rejects_unknown_fields(self):
        """StrictFieldsSerializer rejects undeclared fields."""
        data = {"name": "Alice", "courseId": 1, "extraField": "bad"}
        s = StudentInputSerializer(data=data)
        assert not s.is_valid()
        assert "extraField" in s.errors

    def test_rejects_multiple_unknown_fields(self):
        """StrictFieldsSerializer rejects all undeclared fields."""
        data = {"name": "Alice", "courseId": 1, "bad1": "x", "bad2": "y"}
        s = StudentInputSerializer(data=data)
        assert not s.is_valid()
        assert "bad1" in s.errors
        assert "bad2" in s.errors

    def test_password_allows_blank(self):
        """Password field allows blank values."""
        data = {"name": "Alice", "courseId": 1, "password": ""}
        s = StudentInputSerializer(data=data)
        assert s.is_valid()

    def test_consent_is_optional(self):
        """Consent field is not required."""
        data = {"name": "Alice", "courseId": 1}
        s = StudentInputSerializer(data=data)
        assert s.is_valid()
        assert "consent" not in s.validated_data


# ---------------------------------------------------------------------------
# StudentOutputSerializer
# ---------------------------------------------------------------------------


class TestStudentOutputSerializer:
    """Tests for StudentOutputSerializer output formatting."""

    def test_serializes_student_output(self):
        """Serializes all StudentOutputSerializer fields."""
        data = {
            "id": 42,
            "name": "Alice",
            "username": "alice123",
            "role": "STUDENT",
            "consent": True,
            "courseId": 10,
        }
        s = StudentOutputSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_accepts_null_course_id(self):
        """Accepts null courseId value."""
        data = {
            "id": 42,
            "name": "Bob",
            "username": "bob456",
            "role": "STUDENT",
            "consent": False,
            "courseId": None,
        }
        s = StudentOutputSerializer(data=data)
        assert s.is_valid()


# ---------------------------------------------------------------------------
# StrictFieldsSerializer base class
# ---------------------------------------------------------------------------


class TestStrictFieldsSerializer:
    """Tests for StrictFieldsSerializer base behavior."""

    def test_passes_through_with_known_fields_only(self):
        """Passes validation when only known fields are present."""
        # Use StudentInputSerializer as a concrete implementation
        s = StudentInputSerializer(data={"name": "Test", "courseId": 1})
        assert s.is_valid()

    def test_non_mapping_data_does_not_reject_fields(self):
        """Non-mapping data skips unknown field check (falls through to parent)."""
        # Pass a non-dict type; the parent to_internal_value will handle errors
        s = StudentInputSerializer(data="not a dict")
        assert not s.is_valid()
