"""
Visualization aggregate service layer (FR-09).

All VIZ queries use DB-level aggregation (Count, Avg, Max, Min) per VIZ-CN-08.
Anonymization is applied as a response-level transform per VIZ-CN-01.
"""

import statistics
from datetime import date, datetime, time

from django.db.models import Avg, Max, Min, Q
from django.utils import timezone

from accounts.models import Role, SudoPermission
from assignments.models import Assignment
from core.permissions import has_role, has_sudo_permission
from courses.models import Course, EnrollmentStatus
from submissions.models import Submission, SubmissionStatus


def _now_iso() -> str:
    return timezone.now().isoformat()


def _is_researcher_without_viz(user) -> bool:
    """Return True if caller is RESEARCHER without VIEW_IDENTIFIABLE_VIZ."""
    if user.is_staff:
        return False
    if not has_role(user, Role.RESEARCHER):
        return False
    return not has_sudo_permission(user, SudoPermission.VIEW_IDENTIFIABLE_VIZ)


def _date_to_datetime_range(start_date: date | None, end_date: date | None):
    """Convert date params to timezone-aware datetime range (inclusive)."""
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min)) if start_date else None
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max)) if end_date else None
    return start_dt, end_dt


# ---------------------------------------------------------------------------
# VIZ-UC-01 — Dashboard Overview
# ---------------------------------------------------------------------------


def dashboard_overview(user) -> dict:
    """Aggregate course-level summary cards for the dashboard."""
    if user.is_staff or has_role(user, Role.RESEARCHER):
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(teacher_profile=user.teacher_profile)

    anonymize = _is_researcher_without_viz(user)

    result_courses = []
    for course in courses.select_related("teacher_profile"):
        enrolled_count = course.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()
        assignment_count = course.assignments.count()

        submitted_q = Q(status=SubmissionStatus.SUBMITTED) | Q(status=SubmissionStatus.GRADED)
        subs = Submission.objects.filter(assignment__course=course)
        submitted_count = subs.filter(submitted_q).count()

        denominator = assignment_count * enrolled_count
        avg_completion = round(submitted_count / denominator, 4) if denominator > 0 else None

        graded_agg = subs.filter(status=SubmissionStatus.GRADED).aggregate(avg=Avg("score"))
        avg_score = round(graded_agg["avg"], 2) if graded_agg["avg"] is not None else None

        pending_grades = subs.filter(status=SubmissionStatus.SUBMITTED).count()

        entry = {
            "enrolledCount": enrolled_count,
            "activeEnrollments": enrolled_count,
            "assignmentCount": assignment_count,
            "avgCompletionRate": avg_completion,
            "avgScore": avg_score,
            "pendingGrades": pending_grades,
        }
        if not anonymize:
            entry["courseId"] = course.id
            entry["courseName"] = course.name

        result_courses.append(entry)

    return {
        "generatedAt": _now_iso(),
        "courses": result_courses,
    }


# ---------------------------------------------------------------------------
# VIZ-UC-02 — Course Summary
# ---------------------------------------------------------------------------


def course_summary(
    user,
    course: Course,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    assessment_id: int | None = None,
) -> dict:
    """Per-assignment completion and grade stats for a course."""
    anonymize = _is_researcher_without_viz(user)
    enrolled_count = course.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()

    assignments = course.assignments.select_related("assessment")

    if start_date or end_date:
        s, e = _date_to_datetime_range(start_date, end_date)
        if s:
            assignments = assignments.filter(open_at__gte=s)
        if e:
            assignments = assignments.filter(open_at__lte=e)

    if category:
        assignments = assignments.filter(assessment__category=category)
    if assessment_id is not None:
        assignments = assignments.filter(assessment_id=assessment_id)

    items = []
    for asgn in assignments:
        subs = Submission.objects.filter(assignment=asgn)
        submitted_q = Q(status=SubmissionStatus.SUBMITTED) | Q(status=SubmissionStatus.GRADED)
        submitted_count = subs.filter(submitted_q).count()
        graded_count = subs.filter(status=SubmissionStatus.GRADED).count()
        completion_pct = round(submitted_count / enrolled_count, 4) if enrolled_count > 0 else None

        graded_agg = subs.filter(status=SubmissionStatus.GRADED).aggregate(avg=Avg("score"))
        avg_score = round(graded_agg["avg"], 2) if graded_agg["avg"] is not None else None

        pending = subs.filter(status=SubmissionStatus.SUBMITTED).count()

        entry = {
            "assessmentCategory": asgn.assessment.category,
            "submittedCount": submitted_count,
            "totalStudents": enrolled_count,
            "completionPct": completion_pct,
            "gradedCount": graded_count,
            "avgScore": avg_score,
            "pendingGrades": pending,
        }
        if not anonymize:
            entry["assignmentId"] = asgn.id
            entry["assessmentTitle"] = asgn.assessment.title

        items.append(entry)

    result = {
        "generatedAt": _now_iso(),
        "filters": {
            "startDate": start_date.isoformat() if start_date else None,
            "endDate": end_date.isoformat() if end_date else None,
            "category": category,
            "assessmentId": assessment_id,
        },
        "enrolledCount": enrolled_count,
        "assignments": items,
    }
    if not anonymize:
        result["courseId"] = course.id
        result["courseName"] = course.name

    return result


# ---------------------------------------------------------------------------
# VIZ-UC-03 — Assignment Grade Summary
# ---------------------------------------------------------------------------

DISTRIBUTION_BINS = [
    ("0-59", 0, 59),
    ("60-69", 60, 69),
    ("70-79", 70, 79),
    ("80-89", 80, 89),
    ("90-100", 90, 100),
]


def _build_distribution(scores: list[float]) -> list[dict]:
    """Bin rounded scores per VIZ-CN-02."""
    bins = {label: 0 for label, _, _ in DISTRIBUTION_BINS}
    for raw in scores:
        rounded = round(raw)
        if rounded < 0:
            rounded = 0
        if rounded > 100:
            rounded = 100
        for label, lo, hi in DISTRIBUTION_BINS:
            if lo <= rounded <= hi:
                bins[label] += 1
                break
    return [{"range": label, "count": bins[label]} for label, _, _ in DISTRIBUTION_BINS]


def assignment_grade_summary(
    user,
    assignment: Assignment,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Grade distribution and stats for a single assignment."""
    anonymize = _is_researcher_without_viz(user)
    course = assignment.course
    total_students = (
        course.enrollments.filter(status=EnrollmentStatus.ACTIVE).count() if course else 0
    )

    subs = Submission.objects.filter(assignment=assignment)

    if start_date or end_date:
        s, e = _date_to_datetime_range(start_date, end_date)
        if s:
            subs = subs.filter(submitted_at__gte=s)
        if e:
            subs = subs.filter(submitted_at__lte=e)

    submitted_q = Q(status=SubmissionStatus.SUBMITTED) | Q(status=SubmissionStatus.GRADED)
    submitted_count = subs.filter(submitted_q).count()
    completion_pct = round(submitted_count / total_students, 4) if total_students > 0 else None

    graded_qs = subs.filter(status=SubmissionStatus.GRADED)
    graded_count = graded_qs.count()
    agg = graded_qs.aggregate(avg=Avg("score"), high=Max("score"), low=Min("score"))

    avg_score = round(agg["avg"], 2) if agg["avg"] is not None else None
    high_score = agg["high"]
    low_score = agg["low"]

    # Median computed from score list (DB doesn't have native median)
    scores = list(graded_qs.values_list("score", flat=True))
    median_score = round(statistics.median(scores), 2) if scores else None

    distribution = _build_distribution(scores)

    result = {
        "generatedAt": _now_iso(),
        "filters": {
            "startDate": start_date.isoformat() if start_date else None,
            "endDate": end_date.isoformat() if end_date else None,
        },
        "assessmentCategory": assignment.assessment.category,
        "totalStudents": total_students,
        "submittedCount": submitted_count,
        "gradedCount": graded_count,
        "completionPct": completion_pct,
        "avgScore": avg_score,
        "medianScore": median_score,
        "highScore": high_score,
        "lowScore": low_score,
        "distribution": distribution,
    }
    if not anonymize:
        result["assignmentId"] = assignment.id
        result["assessmentTitle"] = assignment.assessment.title

    return result


# ---------------------------------------------------------------------------
# VIZ-UC-04 — Mood Meter Summary
# ---------------------------------------------------------------------------

QUADRANT_LABELS = [
    ("High Energy / Positive", lambda r, c, mid_r, mid_c: r >= mid_r and c >= mid_c),
    ("High Energy / Negative", lambda r, c, mid_r, mid_c: r >= mid_r and c < mid_c),
    ("Low Energy / Positive", lambda r, c, mid_r, mid_c: r < mid_r and c >= mid_c),
    ("Low Energy / Negative", lambda r, c, mid_r, mid_c: r < mid_r and c < mid_c),
]


def mood_meter_summary(user, assignment: Assignment) -> dict:
    """Quadrant distribution for mood meter assignments."""
    anonymize = _is_researcher_without_viz(user)

    graded_subs = Submission.objects.filter(
        assignment=assignment,
        status=SubmissionStatus.GRADED,
    )

    # Mood meter answers store row/col as NumberScaleAnswer pairs.
    # For now, count graded submissions; quadrant classification requires
    # mood meter answer data (row/col) which depends on MoodMeterAnswer model.
    # Placeholder: read answers and attempt quadrant classification.
    from submissions.models import NumberScaleAnswer

    total = 0
    quadrant_counts = {label: 0 for label, _ in QUADRANT_LABELS}

    for sub in graded_subs:
        answers = sub.answers.all()
        # A mood meter submission has answers with row/col encoded.
        # Try to extract from number_scale answers: first = row, second = col.
        ns_answers = []
        for ans in answers.order_by("id"):
            try:
                ns_answers.append(ans.number_scale.val)
            except NumberScaleAnswer.DoesNotExist:
                continue

        if len(ns_answers) >= 2:
            row_val, col_val = ns_answers[0], ns_answers[1]
            total += 1
            # Midpoints: assume 1-5 scale → mid = 3
            mid_r, mid_c = 3, 3
            for label, check in QUADRANT_LABELS:
                if check(row_val, col_val, mid_r, mid_c):
                    quadrant_counts[label] += 1
                    break

    quadrants = []
    for label, _ in QUADRANT_LABELS:
        count = quadrant_counts[label]
        pct = round(count / total, 2) if total > 0 else 0
        quadrants.append({"label": label, "count": count, "pct": pct})

    result = {
        "generatedAt": _now_iso(),
        "totalResponses": total,
        "quadrants": quadrants,
    }
    if not anonymize:
        result["assignmentId"] = assignment.id

    return result
