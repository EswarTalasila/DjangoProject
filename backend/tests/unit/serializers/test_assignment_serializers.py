"""Pure unit tests for assignment serializer validation (no database)."""

from __future__ import annotations

import pytest

from assignments.serializers import AssignmentSerializer

pytestmark = pytest.mark.unit



class TestAssignmentSerializer:
    """Tests for AssignmentSerializer validation."""

    def test_valid_course_assignment(self):
        """Accepts valid COURSE-type assignment payload."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid(), s.errors
        assert s.validated_data["assessmentId"] == 1
        assert s.validated_data["audienceType"] == "COURSE"
        assert s.validated_data["courseId"] == 10

    def test_valid_teacher_assignment(self):
        """Accepts valid TEACHER-type assignment payload."""
        data = {
            "assessmentId": 2,
            "audienceType": "TEACHER",
            "targetTeacherId": 42,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_rejects_missing_assessment_id(self):
        """Rejects payload without assessmentId."""
        data = {"audienceType": "COURSE", "openAt": "2025-06-01T12:00:00Z"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "assessmentId" in s.errors

    def test_rejects_missing_audience_type(self):
        """Rejects payload without audienceType."""
        data = {"assessmentId": 1, "openAt": "2025-06-01T12:00:00Z"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "audienceType" in s.errors

    def test_rejects_missing_open_at(self):
        """Rejects payload without openAt."""
        data = {"assessmentId": 1, "audienceType": "COURSE"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "openAt" in s.errors

    def test_rejects_invalid_audience_type(self):
        """Rejects invalid audience type value."""
        data = {
            "assessmentId": 1,
            "audienceType": "INVALID",
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "audienceType" in s.errors

    def test_rejects_invalid_date_format(self):
        """Rejects invalid date format for openAt."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "openAt": "not-a-date",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "openAt" in s.errors

    def test_id_is_optional(self):
        """id field is optional."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
        assert "id" not in s.validated_data

    def test_course_id_is_optional_and_nullable(self):
        """courseId is optional and allows null."""
        data = {
            "assessmentId": 1,
            "audienceType": "TEACHER",
            "courseId": None,
            "targetTeacherId": 42,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["courseId"] is None

    def test_due_at_is_optional_and_nullable(self):
        """dueAt is optional and allows null."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "openAt": "2025-06-01T12:00:00Z",
            "dueAt": None,
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()

    def test_accepts_valid_due_at(self):
        """Accepts a valid dueAt datetime."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "openAt": "2025-06-01T12:00:00Z",
            "dueAt": "2025-06-30T23:59:59Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["dueAt"] is not None

    def test_target_teacher_id_is_optional_and_nullable(self):
        """targetTeacherId is optional and allows null."""
        data = {
            "assessmentId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "targetTeacherId": None,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
