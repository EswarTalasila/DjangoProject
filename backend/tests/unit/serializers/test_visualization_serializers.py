"""Unit tests for visualizations.serializers validation logic.

No database access required -- serializer validation is purely in-memory.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ============================================================================
# CourseSummaryParamsSerializer
# ============================================================================


class TestCourseSummaryParamsSerializer:
    """Tests for CourseSummaryParamsSerializer field validation."""

    def test_empty_body_is_valid(self):
        """All filter fields are optional so an empty dict is valid."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={})
        assert s.is_valid(), s.errors

    def test_start_date_filter(self):
        """startDate is accepted as a date string."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"startDate": "2026-01-01"})
        assert s.is_valid()

    def test_end_date_filter(self):
        """endDate is accepted as a date string."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"endDate": "2026-12-31"})
        assert s.is_valid()

    def test_category_filter(self):
        """category is accepted as a string."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"category": "Math"})
        assert s.is_valid()
        assert s.validated_data["category"] == "Math"

    def test_category_allows_blank(self):
        """category accepts blank strings."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"category": ""})
        assert s.is_valid()

    def test_category_allows_null(self):
        """category accepts null values."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"category": None})
        assert s.is_valid()

    def test_assessment_id_filter(self):
        """assessmentId is accepted as an integer."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"assessmentId": 15})
        assert s.is_valid()
        assert s.validated_data["assessmentId"] == 15

    def test_multiple_filters_combined(self):
        """Multiple filters can be combined in a single request."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        data = {"startDate": "2026-01-01", "endDate": "2026-12-31", "category": "SEL", "assessmentId": 3}
        s = CourseSummaryParamsSerializer(data=data)
        assert s.is_valid()
        assert s.validated_data["category"] == "SEL"
        assert s.validated_data["assessmentId"] == 3

    def test_null_date_fields(self):
        """Null values are accepted for optional date fields."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        data = {"startDate": None, "endDate": None, "assessmentId": None}
        s = CourseSummaryParamsSerializer(data=data)
        assert s.is_valid()

    def test_string_rejected_for_integer_field(self):
        """Non-numeric string is rejected for integer fields."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"assessmentId": "not-a-number"})
        assert not s.is_valid()
        assert "assessmentId" in s.errors

    def test_invalid_date_format_rejected(self):
        """Invalid date format is rejected."""
        from visualizations.serializers import CourseSummaryParamsSerializer

        s = CourseSummaryParamsSerializer(data={"startDate": "not-a-date"})
        assert not s.is_valid()
        assert "startDate" in s.errors


# ============================================================================
# AssignmentSummaryParamsSerializer
# ============================================================================


class TestAssignmentSummaryParamsSerializer:
    """Tests for AssignmentSummaryParamsSerializer field validation."""

    def test_empty_body_is_valid(self):
        """All filter fields are optional so an empty dict is valid."""
        from visualizations.serializers import AssignmentSummaryParamsSerializer

        s = AssignmentSummaryParamsSerializer(data={})
        assert s.is_valid(), s.errors

    def test_start_date_filter(self):
        """startDate is accepted as a date string."""
        from visualizations.serializers import AssignmentSummaryParamsSerializer

        s = AssignmentSummaryParamsSerializer(data={"startDate": "2026-01-01"})
        assert s.is_valid()

    def test_end_date_filter(self):
        """endDate is accepted as a date string."""
        from visualizations.serializers import AssignmentSummaryParamsSerializer

        s = AssignmentSummaryParamsSerializer(data={"endDate": "2026-12-31"})
        assert s.is_valid()

    def test_null_date_fields(self):
        """Null values are accepted for optional date fields."""
        from visualizations.serializers import AssignmentSummaryParamsSerializer

        data = {"startDate": None, "endDate": None}
        s = AssignmentSummaryParamsSerializer(data=data)
        assert s.is_valid()

    def test_invalid_date_format_rejected(self):
        """Invalid date format is rejected."""
        from visualizations.serializers import AssignmentSummaryParamsSerializer

        s = AssignmentSummaryParamsSerializer(data={"startDate": "not-a-date"})
        assert not s.is_valid()
        assert "startDate" in s.errors
