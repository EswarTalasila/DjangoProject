"""
Visualization and dashboard data API endpoints.

This module provides aggregated submission data for the teacher dashboard,
enabling visualization of student performance, mood trends, and assessment
completion rates.

The visualization service aggregates submission data by various dimensions:
- By course: Performance across all students in a course
- By assessment: Response patterns for a specific assessment
- By student: Individual progress tracking
- Mood meter: Emotional trends over time

Endpoints:
    POST /api/v1/visualizations - Get visualization data with filters
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.errors import error_response, server_error_response
from core.permissions import IsTeacherOrAbove

from .serializers import VisualizationFilterSerializer
from .services import get_visualization_data


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def get_visualizations(request):
    """
    Get aggregated visualization data for dashboard charts.

    Accepts filter criteria and returns aggregated submission data
    suitable for rendering charts and graphs. Teachers see data for
    their own courses; admins see all data.

    Request Body:
        {
            "courseId": 123,       # Optional: filter by course
            "assessmentId": 456,   # Optional: filter by assessment
            "studentId": 789,      # Optional: filter by student
            "startDate": "2024-01-01",  # Optional: date range start
            "endDate": "2024-12-31"     # Optional: date range end
        }

    Returns:
        200: {
            "submissions": [...],  # Aggregated submission data
            "summary": {...}       # Summary statistics
        }
        400: ValueError if invalid filters
        500: Server error on processing failure
    """
    serializer = VisualizationFilterSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)
    try:
        data = get_visualization_data(serializer.validated_data, request.user)
    except ValueError as exc:
        return error_response(exc)
    except Exception:
        return server_error_response()
    return Response([d.model_dump() for d in data], status=status.HTTP_200_OK)
