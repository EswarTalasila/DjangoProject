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
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid(), s.errors
        assert s.validated_data["assignmentTemplateId"] == 1
        assert s.validated_data["audienceType"] == "COURSE"
        assert s.validated_data["courseId"] == 10
        assert s.validated_data["title"] == "Week 1 reflection"

    def test_teacher_audience_type_rejected(self):
        """Rejects TEACHER audience type (deprecated)."""
        data = {
            "title": "Teacher self assignment",
            "assignmentTemplateId": 2,
            "audienceType": "TEACHER",
            "targetTeacherId": 42,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "audienceType" in s.errors

    def test_rejects_missing_assignment_template_id(self):
        """Rejects payload without assignmentTemplateId."""
        data = {"title": "Week 1 reflection", "audienceType": "COURSE", "openAt": "2025-06-01T12:00:00Z"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "assignmentTemplateId" in s.errors

    def test_rejects_missing_title(self):
        """Rejects payload without title."""
        data = {
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "title" in s.errors

    def test_rejects_missing_audience_type(self):
        """Rejects payload without audienceType."""
        data = {"title": "Week 1 reflection", "assignmentTemplateId": 1, "openAt": "2025-06-01T12:00:00Z"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "audienceType" in s.errors

    def test_rejects_missing_open_at(self):
        """Rejects payload without openAt."""
        data = {"title": "Week 1 reflection", "assignmentTemplateId": 1, "audienceType": "COURSE"}
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "openAt" in s.errors

    def test_rejects_invalid_audience_type(self):
        """Rejects invalid audience type value."""
        data = {
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "INVALID",
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "audienceType" in s.errors

    def test_rejects_invalid_date_format(self):
        """Rejects invalid date format for openAt."""
        data = {
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "openAt": "not-a-date",
        }
        s = AssignmentSerializer(data=data)
        assert not s.is_valid()
        assert "openAt" in s.errors

    def test_id_is_optional(self):
        """id field is optional."""
        data = {
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
        assert "id" not in s.validated_data

    def test_course_id_is_optional_and_nullable(self):
        """courseId is optional and allows null."""
        data = {
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "courseId": None,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["courseId"] is None

    def test_due_at_is_optional_and_nullable(self):
        """dueAt is optional and allows null."""
        data = {
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
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
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
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
            "title": "Week 1 reflection",
            "assignmentTemplateId": 1,
            "audienceType": "COURSE",
            "courseId": 10,
            "targetTeacherId": None,
            "openAt": "2025-06-01T12:00:00Z",
        }
        s = AssignmentSerializer(data=data)
        assert s.is_valid()
