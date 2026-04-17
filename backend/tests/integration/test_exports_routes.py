"""Integration tests for FR-10 Export endpoints."""

import csv
import io
import json

import pytest
from django.utils import timezone

from accounts.models import SudoGrant, SudoPermission
from assignment_templates.models import GradingMode
from courses.models import EnrollmentStatus
from exports.models import ExportAuditLog
from submissions.models import (
    AnswerType,
    ShortAnswerAnswer,
    SubmissionStatus,
)
from tests.factories import (
    AnswerFactory,
    AssignmentTemplateFactory,
    AssignmentFactory,
    CourseFactory,
    EnrollmentFactory,
    QuestionFactory,
    StudentProfileFactory,
    SubmissionFactory,
)

ROSTER_URL = "/api/v1/exports/courses/{}/roster"
COURSE_SUBS_URL = "/api/v1/exports/courses/{}/submissions"


def _parse_csv(response) -> list[dict]:
    """Consume a streaming response and parse CSV rows."""
    raw = b"".join(response.streaming_content)
    # Strip UTF-8 BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _seed_course(teacher_user, *, n_students=3, admin_user=None, consent=False):
    """Create a course with enrollments."""
    course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
    students = []
    for i in range(n_students):
        sp = StudentProfileFactory(
            created_by=admin_user or teacher_user,
            consent=consent if isinstance(consent, bool) else (i % 2 == 0),
        )
        EnrollmentFactory(course=course, student_profile=sp)
        students.append(sp)
    return course, students


def _seed_submissions(teacher_user, course, students, *, admin_user=None, category="General"):
    """Create assignment_template → assignment → submissions for a course."""
    assignment_template = AssignmentTemplateFactory(
        grading_mode=GradingMode.AUTO,
        created_by_admin=admin_user or teacher_user,
        category=category,
    )
    question = QuestionFactory(
        assignment_template=assignment_template,
        kind="SHORT_ANSWER",
        question_type="SHORT_ANSWER",
        prompt="What is your answer?",
    )
    assignment = AssignmentFactory(
        assignment_template=assignment_template,
        course=course,
        created_by=teacher_user,
    )
    subs = []
    for sp in students:
        sub = SubmissionFactory(
            assignment=assignment,
            student=sp.user,
            status=SubmissionStatus.SUBMITTED,
            score=85.0,
            submitted_at=timezone.now(),
        )
        ans = AnswerFactory(
            submission=sub,
            question=question,
            answer_type=AnswerType.SHORT_ANSWER,
            score=85.0,
        )
        ShortAnswerAnswer.objects.create(answer=ans, text="My answer text")
        subs.append(sub)
    return assignment_template, assignment, question, subs


# ===========================================================================
# EXP-UC-01 — Course Roster Export
# ===========================================================================


@pytest.mark.django_db
class TestRosterExport:
    def test_EXP_UC_01_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin can export any course roster (identifiable)."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3
        assert "studentId" in rows[0]
        assert "studentName" in rows[0]
        assert resp["X-Export-Anonymized"] == "false"
        assert resp["X-Export-Row-Count"] == "3"
        assert "X-Export-Generated-At" in resp

    def test_EXP_UC_01_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can export own course roster."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3
        assert "studentId" in rows[0]

    def test_EXP_UC_01_RESEARCHER(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher gets anonymized roster by default."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3
        assert "studentId" not in rows[0]
        assert "consent" in rows[0]
        assert resp["X-Export-Anonymized"] == "true"

    def test_EXP_UC_01_RESEARCHER_anonymized(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher without sudo: anonymized even if identifiable=false."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ROSTER_URL.format(course.id) + "?identifiable=false")
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert "studentId" not in rows[0]

    def test_EXP_UC_01_RESEARCHER_identifiable(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher with EXPORT_IDENTIFIABLE sudo + identifiable=true sees PII."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.EXPORT_IDENTIFIABLE],
        )
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ROSTER_URL.format(course.id) + "?identifiable=true")
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert "studentId" in rows[0]
        assert resp["X-Export-Anonymized"] == "false"

    def test_EXP_UC_01_TEACHER_filter_by_status(self, api_client, teacher_user, admin_user):
        """Status filter on roster export works."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        sp1 = StudentProfileFactory(created_by=admin_user)
        sp2 = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp1, status=EnrollmentStatus.ACTIVE)
        EnrollmentFactory(course=course, student_profile=sp2, status=EnrollmentStatus.DROPPED)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ROSTER_URL.format(course.id) + "?status=ACTIVE")
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 1

    def test_EXP_UC_01_E1(self, api_client, admin_user):
        """404 for non-existent course."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(99999))
        assert resp.status_code == 404

    def test_EXP_UC_01_E2(self, api_client, teacher_user, admin_user):
        """Teacher cannot export another teacher's course."""
        from tests.factories import UserFactory
        from accounts.models import TeacherProfile, UserRole, Role

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        course = CourseFactory(teacher_profile=other_teacher.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert resp.status_code == 403

    def test_EXP_UC_01_E3(self, api_client, student_user):
        """Student is forbidden from roster export."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(ROSTER_URL.format(1))
        assert resp.status_code == 403

    def test_EXP_UC_01_E5(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher without sudo requesting identifiable=true gets 403."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ROSTER_URL.format(course.id) + "?identifiable=true")
        assert resp.status_code == 403

    def test_EXP_UC_01_E4_invalid_identifiable_param(self, api_client, admin_user, teacher_user):
        """Invalid identifiable boolean returns 400."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id) + "?identifiable=maybe")
        assert resp.status_code == 400

    def test_EXP_CN_01_anonymization(self, api_client, researcher_user, teacher_user, admin_user):
        """Verify anonymized columns are omitted, not nulled."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        rows = _parse_csv(resp)
        # Anonymized: only consent, enrollmentStatus, enrolledAt
        assert set(rows[0].keys()) == {"consent", "enrollmentStatus", "enrolledAt"}

    def test_EXP_CN_06_audit_roster(self, api_client, admin_user, teacher_user):
        """Audit log created for roster export."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        api_client.get(ROSTER_URL.format(course.id))
        logs = ExportAuditLog.objects.filter(user=admin_user)
        assert logs.count() == 1
        log = logs.first()
        assert log.export_type == "roster"
        assert log.scope_course == course
        assert log.identifiable is True

    def test_EXP_CN_05_streaming_headers(self, api_client, admin_user, teacher_user):
        """Verify streaming CSV headers."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert "attachment" in resp["Content-Disposition"]
        assert f"roster-{course.id}" in resp["Content-Disposition"]
        assert resp["Content-Type"] == "text/csv; charset=utf-8"

    def test_EXP_CN_07_utf8_bom(self, api_client, admin_user, teacher_user):
        """CSV starts with UTF-8 BOM."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        raw = b"".join(resp.streaming_content)
        assert raw.startswith(b"\xef\xbb\xbf")

    def test_EXP_CN_08_consent(self, api_client, admin_user, teacher_user):
        """Consent column present for all students regardless of value."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        sp1 = StudentProfileFactory(created_by=admin_user, consent=True)
        sp2 = StudentProfileFactory(created_by=admin_user, consent=False)
        EnrollmentFactory(course=course, student_profile=sp1)
        EnrollmentFactory(course=course, student_profile=sp2)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        rows = _parse_csv(resp)
        consents = {r["consent"] for r in rows}
        assert consents == {"true", "false"}

    def test_EXP_CN_06_audit_roster_on_cap_rejection(
        self, api_client, admin_user, teacher_user, monkeypatch
    ):
        """Row-cap rejection still writes audit log entry."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user, n_students=3)
        monkeypatch.setattr("exports.views.COURSE_SCOPED_CAP", 1)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ROSTER_URL.format(course.id))
        assert resp.status_code == 422
        log = ExportAuditLog.objects.filter(user=admin_user).first()
        assert log is not None
        assert log.export_type == "roster"
        assert log.row_count == 3


# ===========================================================================
# EXP-UC-02 — Course Submission Export
# ===========================================================================


@pytest.mark.django_db
class TestCourseSubmissionExport:
    def test_EXP_UC_02_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin can export course submissions (identifiable)."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3
        assert "studentId" in rows[0]
        assert "assignmentTemplateTitle" in rows[0]
        assert resp["X-Export-Anonymized"] == "false"

    def test_EXP_UC_02_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can export own course submissions."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3

    def test_EXP_UC_02_RESEARCHER(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher gets anonymized submission data by default."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id))
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert "studentId" not in rows[0]
        assert "consent" in rows[0]
        assert resp["X-Export-Anonymized"] == "true"

    def test_EXP_UC_02_RESEARCHER_anonymized(self, api_client, researcher_user, teacher_user, admin_user):
        """Anonymized submissions omit identity columns."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id))
        rows = _parse_csv(resp)
        assert set(rows[0].keys()) == {
            "consent", "assignmentTemplateCategory", "gradingMode", "status", "score", "submittedAt"
        }

    def test_EXP_UC_02_RESEARCHER_identifiable(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher with sudo + identifiable=true sees PII."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.EXPORT_IDENTIFIABLE],
        )
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?identifiable=true")
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert "studentId" in rows[0]

    def test_EXP_UC_02_TEACHER_filter_by_category(self, api_client, teacher_user, admin_user):
        """Category filter works."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user, category="math")
        _seed_submissions(teacher_user, course, students, admin_user=admin_user, category="science")
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?category=math")
        rows = _parse_csv(resp)
        assert all(r["assignmentTemplateCategory"] == "math" for r in rows)

    def test_EXP_UC_02_TEACHER_filter_by_date_range(self, api_client, teacher_user, admin_user):
        """Date range filter works."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        today = timezone.now().strftime("%Y-%m-%d")
        resp = api_client.get(
            COURSE_SUBS_URL.format(course.id) + f"?startDate={today}&endDate={today}"
        )
        assert resp.status_code == 200
        rows = _parse_csv(resp)
        assert len(rows) == 3

    def test_EXP_UC_02_TEACHER_include_answers(self, api_client, teacher_user, admin_user):
        """includeAnswers=true adds answers JSON column."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?includeAnswers=true")
        rows = _parse_csv(resp)
        assert "answers" in rows[0]
        answers_data = json.loads(rows[0]["answers"])
        assert isinstance(answers_data, list)
        assert "questionPrompt" in answers_data[0]  # identifiable
        assert "answerType" in answers_data[0]

    def test_EXP_UC_02_include_answers_anonymized(self, api_client, researcher_user, teacher_user, admin_user):
        """Anonymized includeAnswers omits questionPrompt."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?includeAnswers=true")
        rows = _parse_csv(resp)
        assert "answers" in rows[0]
        answers_data = json.loads(rows[0]["answers"])
        assert "questionPrompt" not in answers_data[0]

    def test_EXP_UC_02_E1(self, api_client, admin_user):
        """404 for non-existent course."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(COURSE_SUBS_URL.format(99999))
        assert resp.status_code == 404

    def test_EXP_UC_02_E2(self, api_client, teacher_user, admin_user):
        """Teacher cannot export another teacher's course submissions."""
        from tests.factories import UserFactory
        from accounts.models import TeacherProfile, UserRole, Role

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        course = CourseFactory(teacher_profile=other_teacher.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id))
        assert resp.status_code == 403

    def test_EXP_UC_02_E5(self, api_client, researcher_user, teacher_user, admin_user):
        """Invalid date format returns 400."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?startDate=not-a-date")
        assert resp.status_code == 400

    def test_EXP_UC_02_E6(self, api_client, researcher_user, teacher_user, admin_user):
        """identifiable=true without sudo returns 403."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?identifiable=true")
        assert resp.status_code == 403

    def test_EXP_UC_02_E5_invalid_include_answers_boolean(
        self, api_client, teacher_user, admin_user
    ):
        """Invalid includeAnswers boolean returns 400."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?includeAnswers=maybe")
        assert resp.status_code == 400

    def test_EXP_UC_02_E5_invalid_status_value(self, api_client, teacher_user, admin_user):
        """Invalid submission status filter returns 400."""
        course, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_SUBS_URL.format(course.id) + "?status=BAD_STATUS")
        assert resp.status_code == 400

    def test_EXP_CN_06_audit_submissions(self, api_client, admin_user, teacher_user):
        """Audit log created for course submission export."""
        course, students = _seed_course(teacher_user, admin_user=admin_user)
        _seed_submissions(teacher_user, course, students, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        api_client.get(COURSE_SUBS_URL.format(course.id))
        logs = ExportAuditLog.objects.filter(user=admin_user, export_type="submissions")
        assert logs.count() == 1
        log = logs.first()
        assert log.scope_course == course


# ===========================================================================
# EXP-UC-03 — Cross-Course Submission Export (removed)
# ===========================================================================


@pytest.mark.django_db
class TestCrossCourseSubmissionExportRemoved:
    def test_EXP_UC_03_removed_endpoint_returns_404(self, api_client, admin_user):
        """Cross-course submissions export endpoint is removed by product decision."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/exports/submissions")
        assert resp.status_code == 404
