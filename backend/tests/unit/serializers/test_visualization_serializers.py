"""Unit tests for visualizations.serializers validation logic.

No database access required -- serializer validation is purely in-memory.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ============================================================================
# VisualizationFilterSerializer
# ============================================================================


class TestVisualizationFilterSerializer:
    """Tests for VisualizationFilterSerializer field validation."""

    def test_empty_body_is_valid(self):
        """All filter fields are optional so an empty dict is valid."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={})
        assert s.is_valid(), s.errors

    def test_student_id_filter(self):
        """studentId is accepted as an integer."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"studentId": 42})
        assert s.is_valid()
        assert s.validated_data["studentId"] == 42

    def test_course_id_filter(self):
        """courseId is accepted as an integer."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"courseId": 7})
        assert s.is_valid()
        assert s.validated_data["courseId"] == 7

    def test_category_filter(self):
        """category is accepted as a string."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"category": "Math"})
        assert s.is_valid()
        assert s.validated_data["category"] == "Math"

    def test_category_allows_blank(self):
        """category accepts blank strings."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"category": ""})
        assert s.is_valid()

    def test_category_allows_null(self):
        """category accepts null values."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"category": None})
        assert s.is_valid()

    def test_assessment_id_filter(self):
        """assessmentId is accepted as an integer."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"assessmentId": 15})
        assert s.is_valid()
        assert s.validated_data["assessmentId"] == 15

    def test_teacher_id_filter(self):
        """teacherId is accepted as an integer."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"teacherId": 99})
        assert s.is_valid()
        assert s.validated_data["teacherId"] == 99

    def test_is_mood_meter_boolean(self):
        """isMoodMeter is accepted as a boolean."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"isMoodMeter": True})
        assert s.is_valid()
        assert s.validated_data["isMoodMeter"] is True

    def test_multiple_filters_combined(self):
        """Multiple filters can be combined in a single request."""
        from visualizations.serializers import VisualizationFilterSerializer

        data = {"studentId": 1, "courseId": 2, "category": "SEL", "assessmentId": 3}
        s = VisualizationFilterSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["studentId"] == 1
        assert s.validated_data["courseId"] == 2
        assert s.validated_data["category"] == "SEL"

    def test_null_integer_fields(self):
        """Null values are accepted for optional integer fields."""
        from visualizations.serializers import VisualizationFilterSerializer

        data = {"studentId": None, "courseId": None, "assessmentId": None, "teacherId": None}
        s = VisualizationFilterSerializer(data=data)
        assert s.is_valid()

    def test_string_rejected_for_integer_field(self):
        """Non-numeric string is rejected for integer fields."""
        from visualizations.serializers import VisualizationFilterSerializer

        s = VisualizationFilterSerializer(data={"studentId": "not-a-number"})
        assert not s.is_valid()
        assert "studentId" in s.errors
