"""
Visualization API views (FR-09).

Four read-only GET endpoints returning backend-computed aggregates.
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import Role
from assessments.models import GradingMode
from assignments.models import Assignment
from core.permissions import IsTeacherOrAbove, has_role, teacher_owns_course
from courses.models import Course

from .serializers import AssignmentSummaryParamsSerializer, CourseSummaryParamsSerializer
from .services import (
    assignment_grade_summary,
    course_summary,
    dashboard_overview,
    mood_meter_summary,
)

logger = logging.getLogger(__name__)


def _is_teacher(user) -> bool:
    return not user.is_staff and not has_role(user, Role.RESEARCHER) and has_role(user, Role.TEACHER)


# ---------------------------------------------------------------------------
# VIZ-UC-01 — Dashboard Overview
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def viz_dashboard(request):
    """GET /api/v1/visualizations/dashboard"""
    data = dashboard_overview(request.user)
    return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# VIZ-UC-02 — Course Summary
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def viz_course_summary(request, course_id):
    """GET /api/v1/visualizations/courses/{courseId}/summary"""
    try:
        course = Course.objects.select_related("teacher_profile").get(pk=course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

    if _is_teacher(request.user) and not teacher_owns_course(request.user, course):
        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    ser = CourseSummaryParamsSerializer(data=request.query_params)
    if not ser.is_valid():
        return Response({"detail": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
    params = ser.validated_data

    data = course_summary(
        request.user,
        course,
        start_date=params.get("startDate"),
        end_date=params.get("endDate"),
        category=params.get("category"),
        assessment_id=params.get("assessmentId"),
    )
    return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# VIZ-UC-03 — Assignment Grade Summary
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def viz_assignment_summary(request, assignment_id):
    """GET /api/v1/visualizations/assignments/{assignmentId}/summary"""
    try:
        assignment = Assignment.objects.select_related("course__teacher_profile", "assessment").get(
            pk=assignment_id
        )
    except Assignment.DoesNotExist:
        return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

    if _is_teacher(request.user):
        if not assignment.course or not teacher_owns_course(request.user, assignment.course):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    ser = AssignmentSummaryParamsSerializer(data=request.query_params)
    if not ser.is_valid():
        return Response({"detail": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
    params = ser.validated_data

    data = assignment_grade_summary(
        request.user,
        assignment,
        start_date=params.get("startDate"),
        end_date=params.get("endDate"),
    )
    return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# VIZ-UC-04 — Mood Meter Summary
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def viz_mood_meter(request, assignment_id):
    """GET /api/v1/visualizations/assignments/{assignmentId}/mood-meter"""
    try:
        assignment = Assignment.objects.select_related("course__teacher_profile", "assessment").get(
            pk=assignment_id
        )
    except Assignment.DoesNotExist:
        return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

    # VIZ-CN-04: mood meter type gate
    if assignment.assessment.grading_mode != GradingMode.MOOD_METER:
        return Response(
            {"detail": "Incompatible assessment type."},
            status=status.HTTP_409_CONFLICT,
        )

    if _is_teacher(request.user):
        if not assignment.course or not teacher_owns_course(request.user, assignment.course):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    data = mood_meter_summary(request.user, assignment)
    return Response(data, status=status.HTTP_200_OK)
