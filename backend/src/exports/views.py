"""
FR-10 Export endpoints — streaming CSV exports for roster and submissions.

Endpoints:
    GET /api/v1/exports/courses/{courseId}/roster      (EXP-UC-01)
    GET /api/v1/exports/courses/{courseId}/submissions  (EXP-UC-02)
    GET /api/v1/exports/submissions                    (EXP-UC-03)
"""

import datetime as dt

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import Role
from core.permissions import IsResearcherOrAdmin, IsTeacherOrAbove, has_role
from courses.models import Course

from .services import (
    COURSE_SCOPED_CAP,
    CROSS_COURSE_CAP,
    export_course_submissions,
    export_cross_course_submissions,
    export_roster,
    resolve_anonymization,
)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    return None


def _parse_date(value: str | None, *, end_of_day=False):
    if not value:
        return None
    try:
        d = dt.date.fromisoformat(value)
        t = dt.time.max if end_of_day else dt.time.min
        return dt.datetime.combine(d, t, tzinfo=dt.timezone.utc)
    except (ValueError, TypeError):
        return "invalid"


def _parse_int(value: str | None):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return "invalid"


def _check_course_access(user, course):
    """Return error Response if teacher doesn't own the course, else None."""
    if user.is_staff or has_role(user, Role.RESEARCHER):
        return None
    # Teacher must own the course
    try:
        if course.teacher_profile != user.teacher_profile:
            return Response(
                {"detail": "You do not own this course"},
                status=status.HTTP_403_FORBIDDEN,
            )
    except Exception:
        return Response(
            {"detail": "You do not own this course"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _streaming_response(generator, row_count, is_anonymized, filename):
    """Wrap a CSV generator in a StreamingHttpResponse with metadata headers."""
    response = StreamingHttpResponse(generator, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Export-Generated-At"] = timezone.now().isoformat()
    response["X-Export-Anonymized"] = "true" if is_anonymized else "false"
    response["X-Export-Row-Count"] = str(row_count)
    return response


# ── EXP-UC-01 — Course Roster Export ─────────────────────────────────

@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def course_roster(request, course_id):
    """GET /api/v1/exports/courses/{courseId}/roster"""
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_course_access(request.user, course)
    if access_err:
        return access_err

    # Anonymization
    identifiable_param = _parse_bool(request.query_params.get("identifiable"))
    is_identifiable, anon_err = resolve_anonymization(request.user, identifiable_param)
    if anon_err:
        return Response({"detail": anon_err}, status=status.HTTP_403_FORBIDDEN)

    # Status filter
    status_filter = request.query_params.get("status")

    # Row cap (EXP-CN-03)
    from courses.models import Enrollment

    qs = Enrollment.objects.filter(course=course)
    if status_filter:
        qs = qs.filter(status=status_filter)
    count = qs.count()
    if count > COURSE_SCOPED_CAP:
        return Response(
            {"detail": "Export too large. Apply filters to reduce dataset."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    generator, row_count, is_anonymized = export_roster(
        request.user, course,
        status_filter=status_filter,
        identifiable=is_identifiable,
    )

    today = timezone.now().strftime("%Y-%m-%d")
    return _streaming_response(
        generator, row_count, is_anonymized,
        f"roster-{course_id}-{today}.csv",
    )


# ── EXP-UC-02 — Course Submission Export ─────────────────────────────

@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def course_submissions(request, course_id):
    """GET /api/v1/exports/courses/{courseId}/submissions"""
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_course_access(request.user, course)
    if access_err:
        return access_err

    # Anonymization
    identifiable_param = _parse_bool(request.query_params.get("identifiable"))
    is_identifiable, anon_err = resolve_anonymization(request.user, identifiable_param)
    if anon_err:
        return Response({"detail": anon_err}, status=status.HTTP_403_FORBIDDEN)

    # Parse filters
    params = request.query_params
    start_date = _parse_date(params.get("startDate"))
    end_date = _parse_date(params.get("endDate"), end_of_day=True)
    assessment_id = _parse_int(params.get("assessmentId"))
    assignment_id = _parse_int(params.get("assignmentId"))

    # Validate param types
    if start_date == "invalid" or end_date == "invalid":
        return Response(
            {"detail": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if assessment_id == "invalid" or assignment_id == "invalid":
        return Response(
            {"detail": "Invalid integer parameter."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    category = params.get("category")
    status_filter = params.get("status")
    include_answers = _parse_bool(params.get("includeAnswers")) or False

    # Row cap (EXP-CN-03) — estimate with same filters
    from submissions.models import Submission

    qs = Submission.objects.filter(assignment__course=course)
    if start_date:
        qs = qs.filter(submitted_at__gte=start_date)
    if end_date:
        qs = qs.filter(submitted_at__lte=end_date)
    if category:
        qs = qs.filter(assignment__assessment__category=category)
    if assessment_id:
        qs = qs.filter(assignment__assessment_id=assessment_id)
    if assignment_id:
        qs = qs.filter(assignment_id=assignment_id)
    if status_filter:
        qs = qs.filter(status=status_filter)

    count = qs.count()
    if count > COURSE_SCOPED_CAP:
        return Response(
            {"detail": "Export too large. Apply filters to reduce dataset."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    generator, row_count, is_anonymized = export_course_submissions(
        request.user, course,
        start_date=start_date,
        end_date=end_date,
        category=category,
        assessment_id=assessment_id,
        assignment_id=assignment_id,
        status_filter=status_filter,
        include_answers=include_answers,
        identifiable=is_identifiable,
    )

    today = timezone.now().strftime("%Y-%m-%d")
    return _streaming_response(
        generator, row_count, is_anonymized,
        f"submissions-course-{course_id}-{today}.csv",
    )


# ── EXP-UC-03 — Cross-Course Submission Export ───────────────────────

@api_view(["GET"])
@permission_classes([IsResearcherOrAdmin])
def cross_course_submissions(request):
    """GET /api/v1/exports/submissions"""
    params = request.query_params

    # Required date range (EXP-CN-04)
    raw_start = params.get("startDate")
    raw_end = params.get("endDate")
    if not raw_start or not raw_end:
        return Response(
            {"detail": "Cross-course export requires startDate and endDate filters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_date = _parse_date(raw_start)
    end_date = _parse_date(raw_end, end_of_day=True)
    if start_date == "invalid" or end_date == "invalid":
        return Response(
            {"detail": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    assessment_id = _parse_int(params.get("assessmentId"))
    if assessment_id == "invalid":
        return Response(
            {"detail": "Invalid integer parameter."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Anonymization
    identifiable_param = _parse_bool(params.get("identifiable"))
    is_identifiable, anon_err = resolve_anonymization(request.user, identifiable_param)
    if anon_err:
        return Response({"detail": anon_err}, status=status.HTTP_403_FORBIDDEN)

    category = params.get("category")
    status_filter = params.get("status")
    include_answers = _parse_bool(params.get("includeAnswers")) or False

    # Row cap (EXP-CN-04) — estimate with same filters
    from submissions.models import Submission

    qs = Submission.objects.filter(
        submitted_at__gte=start_date,
        submitted_at__lte=end_date,
    )
    if category:
        qs = qs.filter(assignment__assessment__category=category)
    if assessment_id:
        qs = qs.filter(assignment__assessment_id=assessment_id)
    if status_filter:
        qs = qs.filter(status=status_filter)

    count = qs.count()
    if count > CROSS_COURSE_CAP:
        return Response(
            {"detail": "Export too large. Narrow date range or apply additional filters."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    generator, row_count, is_anonymized = export_cross_course_submissions(
        request.user,
        start_date=start_date,
        end_date=end_date,
        category=category,
        assessment_id=assessment_id,
        status_filter=status_filter,
        include_answers=include_answers,
        identifiable=is_identifiable,
    )

    today = timezone.now().strftime("%Y-%m-%d")
    return _streaming_response(
        generator, row_count, is_anonymized,
        f"submissions-cross-course-{today}.csv",
    )
