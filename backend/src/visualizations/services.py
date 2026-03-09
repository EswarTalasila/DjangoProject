"""
Visualization aggregate service layer (FR-09).

All VIZ queries use DB-level aggregation (Count, Avg, Max, Min) per VIZ-CN-08.
Anonymization is applied as a response-level transform per VIZ-CN-01.
"""

import statistics
from datetime import date, datetime, time

from django.db.models import Avg, Case, CharField, Count, F, FloatField, IntegerField, Max, Min, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce, Round
from django.utils import timezone

from accounts.models import Role, SudoPermission
from assessments.models import QuestionKind
from assignments.models import Assignment
from core.permissions import has_role, has_sudo_permission
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import AnswerType, NumberScaleAnswer, Submission, SubmissionStatus


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
        courses = Course.objects.all().select_related("teacher_profile")
    else:
        courses = Course.objects.filter(teacher_profile=user.teacher_profile).select_related(
            "teacher_profile"
        )

    anonymize = _is_researcher_without_viz(user)

    active_enrollments_sq = (
        Enrollment.objects.filter(course=OuterRef("pk"), status=EnrollmentStatus.ACTIVE)
        .values("course")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    assignment_count_sq = (
        Assignment.objects.filter(course=OuterRef("pk"))
        .values("course")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    submitted_count_sq = (
        Submission.objects.filter(
            assignment__course=OuterRef("pk"),
            status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED],
        )
        .values("assignment__course")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    pending_count_sq = (
        Submission.objects.filter(
            assignment__course=OuterRef("pk"),
            status=SubmissionStatus.SUBMITTED,
        )
        .values("assignment__course")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    graded_avg_sq = (
        Submission.objects.filter(
            assignment__course=OuterRef("pk"),
            status=SubmissionStatus.GRADED,
        )
        .values("assignment__course")
        .annotate(v=Avg("score"))
        .values("v")[:1]
    )

    courses = courses.annotate(
        active_enrollments=Coalesce(
            Subquery(active_enrollments_sq, output_field=IntegerField()),
            Value(0),
        ),
        assignment_count=Coalesce(
            Subquery(assignment_count_sq, output_field=IntegerField()),
            Value(0),
        ),
        submitted_count=Coalesce(
            Subquery(submitted_count_sq, output_field=IntegerField()),
            Value(0),
        ),
        pending_count=Coalesce(
            Subquery(pending_count_sq, output_field=IntegerField()),
            Value(0),
        ),
        graded_avg=Subquery(graded_avg_sq, output_field=FloatField()),
    )

    result_courses = []
    for course in courses:
        enrolled_count = course.active_enrollments
        assignment_count = course.assignment_count
        submitted_count = course.submitted_count

        denominator = assignment_count * enrolled_count
        avg_completion = round(submitted_count / denominator, 4) if denominator > 0 else None

        avg_score = round(course.graded_avg, 2) if course.graded_avg is not None else None
        pending_grades = course.pending_count

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
    enrolled_count = Enrollment.objects.filter(
        course=course,
        status=EnrollmentStatus.ACTIVE,
    ).count()

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

    submitted_count_sq = (
        Submission.objects.filter(
            assignment=OuterRef("pk"),
            status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED],
        )
        .values("assignment")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    graded_count_sq = (
        Submission.objects.filter(
            assignment=OuterRef("pk"),
            status=SubmissionStatus.GRADED,
        )
        .values("assignment")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    pending_count_sq = (
        Submission.objects.filter(
            assignment=OuterRef("pk"),
            status=SubmissionStatus.SUBMITTED,
        )
        .values("assignment")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )
    avg_score_sq = (
        Submission.objects.filter(
            assignment=OuterRef("pk"),
            status=SubmissionStatus.GRADED,
        )
        .values("assignment")
        .annotate(v=Avg("score"))
        .values("v")[:1]
    )

    assignments = assignments.annotate(
        submitted_count=Coalesce(Subquery(submitted_count_sq, output_field=IntegerField()), Value(0)),
        graded_count=Coalesce(Subquery(graded_count_sq, output_field=IntegerField()), Value(0)),
        pending_count=Coalesce(Subquery(pending_count_sq, output_field=IntegerField()), Value(0)),
        avg_score=Subquery(avg_score_sq, output_field=FloatField()),
    )

    items = []
    for asgn in assignments:
        submitted_count = asgn.submitted_count
        graded_count = asgn.graded_count
        completion_pct = round(submitted_count / enrolled_count, 4) if enrolled_count > 0 else None

        avg_score = round(asgn.avg_score, 2) if asgn.avg_score is not None else None
        pending = asgn.pending_count

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


def _distribution_from_graded_queryset(graded_qs) -> list[dict]:
    """Build VIZ-CN-02 distribution bins from DB-side bucketization."""
    bucketed = (
        graded_qs.annotate(
            clamped_score=Case(
                When(score__lt=0, then=Value(0.0)),
                When(score__gt=100, then=Value(100.0)),
                default=F("score"),
                output_field=FloatField(),
            )
        )
        .annotate(rounded_score=Round("clamped_score"))
        .annotate(
            score_bucket=Case(
                When(rounded_score__lte=59, then=Value("0-59")),
                When(rounded_score__lte=69, then=Value("60-69")),
                When(rounded_score__lte=79, then=Value("70-79")),
                When(rounded_score__lte=89, then=Value("80-89")),
                default=Value("90-100"),
                output_field=CharField(),
            )
        )
        .values("score_bucket")
        .annotate(count=Count("id"))
    )
    bucket_counts = {item["score_bucket"]: item["count"] for item in bucketed}
    return [
        {"range": label, "count": bucket_counts.get(label, 0)}
        for label, _, _ in DISTRIBUTION_BINS
    ]


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

    distribution = _distribution_from_graded_queryset(graded_qs)

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

def mood_meter_summary(user, assignment: Assignment) -> dict:
    """Quadrant distribution for mood meter assignments."""
    anonymize = _is_researcher_without_viz(user)

    graded_subs = Submission.objects.filter(
        assignment=assignment,
        status=SubmissionStatus.GRADED,
    )

    ns_question_cfg = list(
        assignment.assessment.questions.filter(kind=QuestionKind.NUMBER_SCALE)
        .select_related("number_scale")
        .order_by("id")[:2]
    )
    if len(ns_question_cfg) == 2:
        row_cfg, col_cfg = ns_question_cfg
        mid_r = (row_cfg.number_scale.min + row_cfg.number_scale.max) / 2
        mid_c = (col_cfg.number_scale.min + col_cfg.number_scale.max) / 2
    else:
        # Backward-safe fallback for legacy mood-meter templates.
        mid_r, mid_c = 3, 3

    row_val_sq = Subquery(
        NumberScaleAnswer.objects.filter(
            answer__submission=OuterRef("pk"),
            answer__answer_type=AnswerType.NUMBER_SCALE,
        )
        .order_by("answer__question_id", "answer_id")
        .values("val")[:1],
        output_field=IntegerField(),
    )
    col_val_sq = Subquery(
        NumberScaleAnswer.objects.filter(
            answer__submission=OuterRef("pk"),
            answer__answer_type=AnswerType.NUMBER_SCALE,
        )
        .order_by("answer__question_id", "answer_id")
        .values("val")[1:2],
        output_field=IntegerField(),
    )

    classified = graded_subs.annotate(row_val=row_val_sq, col_val=col_val_sq).filter(
        row_val__isnull=False,
        col_val__isnull=False,
    )
    agg = classified.aggregate(
        total=Count("id"),
        high_positive=Count("id", filter=Q(row_val__gte=mid_r, col_val__gte=mid_c)),
        high_negative=Count("id", filter=Q(row_val__gte=mid_r, col_val__lt=mid_c)),
        low_positive=Count("id", filter=Q(row_val__lt=mid_r, col_val__gte=mid_c)),
        low_negative=Count("id", filter=Q(row_val__lt=mid_r, col_val__lt=mid_c)),
    )
    total = agg["total"] or 0
    quadrants = [
        {
            "label": "High Energy / Positive",
            "count": agg["high_positive"] or 0,
            "pct": round((agg["high_positive"] or 0) / total, 2) if total > 0 else 0,
        },
        {
            "label": "High Energy / Negative",
            "count": agg["high_negative"] or 0,
            "pct": round((agg["high_negative"] or 0) / total, 2) if total > 0 else 0,
        },
        {
            "label": "Low Energy / Positive",
            "count": agg["low_positive"] or 0,
            "pct": round((agg["low_positive"] or 0) / total, 2) if total > 0 else 0,
        },
        {
            "label": "Low Energy / Negative",
            "count": agg["low_negative"] or 0,
            "pct": round((agg["low_negative"] or 0) / total, 2) if total > 0 else 0,
        },
    ]

    result = {
        "generatedAt": _now_iso(),
        "totalResponses": total,
        "quadrants": quadrants,
    }
    if not anonymize:
        result["assignmentId"] = assignment.id

    return result
