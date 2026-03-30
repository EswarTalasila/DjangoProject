"""
Export domain services — streaming CSV generation for FR-10.

Each public function returns a tuple of (csv_generator, row_count, is_anonymized)
so the view layer can set response headers before streaming begins.
"""

import csv
import json

from accounts.models import Role, SudoPermission
from core.permissions import has_role, has_sudo_permission
from courses.models import Course, Enrollment
from submissions.models import AnswerType, Submission

from .models import ExportAuditLog

# ── Row caps (EXP-CN-03 / EXP-CN-04) ────────────────────────────────
COURSE_SCOPED_CAP = 10_000

# ── CSV pseudo-buffer (one-row-at-a-time pattern) ────────────────────
UTF8_BOM = b"\xef\xbb\xbf"


class _Echo:
    """Pseudo-buffer that returns whatever is written to it."""

    def write(self, value):
        return value


# ── Column sets ───────────────────────────────────────────────────────
ROSTER_COLS_IDENTIFIABLE = [
    "studentId", "studentName", "studentUsername", "consent",
    "enrollmentStatus", "enrolledAt", "courseId", "courseName",
]
ROSTER_COLS_ANONYMIZED = ["consent", "enrollmentStatus", "enrolledAt"]

COURSE_SUB_COLS_IDENTIFIABLE = [
    "studentId", "studentName", "studentUsername", "consent",
    "assignmentId", "assessmentTitle", "assessmentCategory",
    "gradingMode", "status", "score", "submittedAt",
]
COURSE_SUB_COLS_ANONYMIZED = [
    "consent", "assessmentCategory", "gradingMode", "status",
    "score", "submittedAt",
]



# ── Anonymization resolver (EXP-CN-01) ───────────────────────────────

def resolve_anonymization(user, identifiable_param: bool | None):
    """
    Return (is_identifiable: bool, error_msg: str | None).

    - ADMIN/TEACHER: always identifiable; param ignored.
    - RESEARCHER + sudo + identifiable=true: identifiable.
    - RESEARCHER + sudo + identifiable omitted/false: anonymized.
    - RESEARCHER without sudo + identifiable=true: 403.
    - RESEARCHER without sudo + identifiable omitted/false: anonymized.
    """
    if user.is_staff:
        return True, None
    if has_role(user, Role.TEACHER):
        return True, None

    # Researcher path
    has_export_sudo = has_sudo_permission(user, SudoPermission.EXPORT_IDENTIFIABLE)
    if identifiable_param:
        if not has_export_sudo:
            return False, "EXPORT_IDENTIFIABLE permission required"
        return True, None
    return False, None


# ── Audit logging (EXP-CN-06) ────────────────────────────────────────

def _log_audit(user, export_type, scope_course, filters, identifiable, row_count):
    ExportAuditLog.objects.create(
        user=user,
        export_type=export_type,
        scope_course=scope_course,
        filters=filters,
        identifiable=identifiable,
        row_count=row_count,
    )


def log_export_audit(user, export_type, scope_course, filters, identifiable=False, row_count=0):
    """Public wrapper for audit entries used by early-return branches in views."""
    _log_audit(
        user=user,
        export_type=export_type,
        scope_course=scope_course,
        filters=filters,
        identifiable=identifiable,
        row_count=row_count,
    )


# ── Answer serialization for includeAnswers ──────────────────────────

def _serialize_answers(submission, identifiable: bool) -> str:
    """Serialize answers to JSON string for CSV column."""
    result = []
    for answer in submission.answers.all():
        obj = {
            "answerType": answer.answer_type,
            "value": _answer_value(answer),
            "score": answer.score,
            "skipped": answer.skipped,
        }
        if identifiable:
            obj["questionPrompt"] = answer.question.prompt
        result.append(obj)
    return json.dumps(result, default=str)


def _answer_value(answer) -> dict:
    if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
        try:
            # Use .all() to leverage prefetch cache instead of values_list().
            selected = [sel.choice_index for sel in answer.multiple_choice.selected.all()]
            return {"selected": selected}
        except Exception:
            return {}
    elif answer.answer_type == AnswerType.SHORT_ANSWER:
        try:
            return {"text": answer.short_answer.text}
        except Exception:
            return {}
    elif answer.answer_type == AnswerType.NUMBER_SCALE:
        try:
            return {"val": answer.number_scale.val}
        except Exception:
            return {}
    return {}


# ── CSV row helpers ──────────────────────────────────────────────────

def _csv_val(val):
    """Normalize a value for CSV output (EXP-CN-07)."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


def _make_writer():
    buf = _Echo()
    writer = csv.writer(buf)
    return buf, writer


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API — called from views
# ══════════════════════════════════════════════════════════════════════


def export_roster(user, course: Course, *, status_filter=None, identifiable=True):
    """
    Generate streaming CSV for course roster (EXP-UC-01).

    Returns (generator, row_count, is_anonymized).
    """
    qs = Enrollment.objects.filter(course=course).select_related(
        "student_profile__user"
    )
    if status_filter:
        qs = qs.filter(status=status_filter)

    row_count = qs.count()

    cols = ROSTER_COLS_IDENTIFIABLE if identifiable else ROSTER_COLS_ANONYMIZED

    _log_audit(
        user=user,
        export_type="roster",
        scope_course=course,
        filters={"status": status_filter},
        identifiable=identifiable,
        row_count=row_count,
    )

    def _generate():
        buf, writer = _make_writer()
        # BOM + header
        yield UTF8_BOM + writer.writerow(cols).encode("utf-8")
        for enrollment in qs.iterator(chunk_size=2000):
            sp = enrollment.student_profile
            u = sp.user
            data = {
                "studentId": u.id,
                "studentName": u.name,
                "studentUsername": u.username,
                "consent": sp.consent,
                "enrollmentStatus": enrollment.status,
                "enrolledAt": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else "",
                "courseId": course.id,
                "courseName": course.name,
            }
            row_str = writer.writerow([_csv_val(data.get(c)) for c in cols])
            yield row_str.encode("utf-8")

    return _generate(), row_count, not identifiable


def export_course_submissions(
    user,
    course: Course,
    *,
    start_date=None,
    end_date=None,
    category=None,
    assessment_id=None,
    assignment_id=None,
    status_filter=None,
    include_answers=False,
    identifiable=True,
):
    """
    Generate streaming CSV for course submission export (EXP-UC-02).

    Returns (generator, row_count, is_anonymized).
    """
    qs = Submission.objects.filter(
        assignment__course=course,
    ).select_related(
        "assignment__assessment", "assignment__course",
        "student__student_profile",
    )

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

    if include_answers:
        qs = qs.prefetch_related(
            "answers__question",
            "answers__multiple_choice__selected",
            "answers__short_answer",
            "answers__number_scale",
        )

    row_count = qs.count()

    cols = COURSE_SUB_COLS_IDENTIFIABLE if identifiable else COURSE_SUB_COLS_ANONYMIZED
    if include_answers:
        cols = [*cols, "answers"]

    _log_audit(
        user=user,
        export_type="submissions",
        scope_course=course,
        filters={
            "startDate": str(start_date) if start_date else None,
            "endDate": str(end_date) if end_date else None,
            "category": category,
            "assessmentId": assessment_id,
            "assignmentId": assignment_id,
            "status": status_filter,
            "includeAnswers": include_answers,
        },
        identifiable=identifiable,
        row_count=row_count,
    )

    def _generate():
        buf, writer = _make_writer()
        yield UTF8_BOM + writer.writerow(cols).encode("utf-8")
        for sub in qs.iterator(chunk_size=2000):
            student = sub.student
            assessment = sub.assignment.assessment
            # Resolve student profile for consent
            consent = ""
            if student:
                try:
                    consent = student.student_profile.consent
                except Exception:
                    consent = ""
            data = {
                "studentId": student.id if student else "",
                "studentName": student.name if student else "",
                "studentUsername": student.username if student else "",
                "consent": consent,
                "assignmentId": sub.assignment_id,
                "assessmentTitle": assessment.title if assessment else "",
                "assessmentCategory": assessment.category if assessment else "",
                "gradingMode": assessment.grading_mode if assessment else "",
                "status": sub.status,
                "score": sub.score,
                "submittedAt": sub.submitted_at.isoformat() if sub.submitted_at else "",
            }
            if include_answers:
                data["answers"] = _serialize_answers(sub, identifiable)
            row_str = writer.writerow([_csv_val(data.get(c)) for c in cols])
            yield row_str.encode("utf-8")

    return _generate(), row_count, not identifiable

