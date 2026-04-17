"""Unit tests for exports.services — streaming CSV generation for FR-10.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.core.exceptions import ObjectDoesNotExist

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _patch_transaction_atomic(monkeypatch):
    monkeypatch.setattr("django.db.transaction.Atomic.__enter__", lambda self: None)
    monkeypatch.setattr("django.db.transaction.Atomic.__exit__", lambda self, exc_type, exc, tb: False)
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, using=None: func())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(is_staff=False, is_teacher=False, is_researcher=False, has_export_sudo=False):
    u = MagicMock()
    u.id = 1
    u.is_staff = is_staff
    return u


def _course(id=1, name="CS101"):
    c = MagicMock()
    c.id = id
    c.name = name
    return c


def _enrollment(student_id=10, student_name="Alice", student_username="alice",
                consent=True, status="ACTIVE", enrolled_at=None):
    sp = MagicMock()
    sp.consent = consent
    sp.user = MagicMock()
    sp.user.id = student_id
    sp.user.name = student_name
    sp.user.username = student_username

    e = MagicMock()
    e.student_profile = sp
    e.status = status
    e.enrolled_at = enrolled_at
    return e


def _submission(student_id=10, student_name="Alice", student_username="alice",
                consent=True, assignment_id=1, assessment_title="Quiz",
                assessment_category="FORMATIVE", grading_mode="AUTO",
                status="SUBMITTED", score=85, submitted_at=None,
                has_student=True):
    sub = MagicMock()
    if has_student:
        sub.student = MagicMock()
        sub.student.id = student_id
        sub.student.name = student_name
        sub.student.username = student_username
        sub.student.student_profile = MagicMock()
        sub.student.student_profile.consent = consent
    else:
        sub.student = None

    sub.assignment_id = assignment_id
    sub.assignment = MagicMock()
    sub.assignment.assignment_template = MagicMock()
    sub.assignment.assignment_template.title = assessment_title
    sub.assignment.assignment_template.category = assessment_category
    sub.assignment.assignment_template.grading_mode = grading_mode
    sub.status = status
    sub.score = score
    sub.submitted_at = submitted_at
    return sub


# ---------------------------------------------------------------------------
# _Echo
# ---------------------------------------------------------------------------

class TestEcho:
    def test_write_returns_value(self):
        """Returns the written value unchanged."""
        from exports.services import _Echo
        e = _Echo()
        assert e.write("hello") == "hello"


# ---------------------------------------------------------------------------
# _csv_val
# ---------------------------------------------------------------------------

class TestCsvVal:
    def test_none(self):
        """Converts None to empty string."""
        from exports.services import _csv_val
        assert _csv_val(None) == ""

    def test_bool_true(self):
        """Converts True to lowercase string."""
        from exports.services import _csv_val
        assert _csv_val(True) == "true"

    def test_bool_false(self):
        """Converts False to lowercase string."""
        from exports.services import _csv_val
        assert _csv_val(False) == "false"

    def test_string(self):
        """Passes string values through unchanged."""
        from exports.services import _csv_val
        assert _csv_val("hello") == "hello"

    def test_int(self):
        """Converts integer to its string representation."""
        from exports.services import _csv_val
        assert _csv_val(42) == "42"


# ---------------------------------------------------------------------------
# resolve_anonymization
# ---------------------------------------------------------------------------

class TestResolveAnonymization:
    @patch("exports.services.has_sudo_permission", return_value=False)
    @patch("exports.services.has_role", return_value=False)
    def test_admin_always_identifiable(self, mock_role, mock_sudo):
        """Grants identifiable access to admin users unconditionally."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=True)
        ident, err = resolve_anonymization(user, False)
        assert ident is True
        assert err is None

    @patch("exports.services.has_sudo_permission", return_value=False)
    @patch("exports.services.has_role", return_value=True)
    def test_teacher_always_identifiable(self, mock_role, mock_sudo):
        """Grants identifiable access to teacher users unconditionally."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=False)
        ident, err = resolve_anonymization(user, False)
        assert ident is True
        assert err is None

    @patch("exports.services.has_sudo_permission", return_value=True)
    @patch("exports.services.has_role", return_value=False)
    def test_researcher_with_sudo_identifiable(self, mock_role, mock_sudo):
        """Grants identifiable access to researcher with EXPORT_IDENTIFIABLE sudo permission."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=False)
        ident, err = resolve_anonymization(user, True)
        assert ident is True
        assert err is None

    @patch("exports.services.has_sudo_permission", return_value=False)
    @patch("exports.services.has_role", return_value=False)
    def test_researcher_without_sudo_identifiable_denied(self, mock_role, mock_sudo):
        """Denies identifiable access to researcher lacking EXPORT_IDENTIFIABLE permission."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=False)
        ident, err = resolve_anonymization(user, True)
        assert ident is False
        assert err is not None
        assert "EXPORT_IDENTIFIABLE" in err

    @patch("exports.services.has_sudo_permission", return_value=False)
    @patch("exports.services.has_role", return_value=False)
    def test_researcher_anonymized(self, mock_role, mock_sudo):
        """Allows researcher to export anonymized data without special permissions."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=False)
        ident, err = resolve_anonymization(user, False)
        assert ident is False
        assert err is None

    @patch("exports.services.has_sudo_permission", return_value=True)
    @patch("exports.services.has_role", return_value=False)
    def test_researcher_with_sudo_not_requesting_identifiable(self, mock_role, mock_sudo):
        """Returns anonymized when researcher with sudo does not request identifiable."""
        from exports.services import resolve_anonymization
        user = _user(is_staff=False)
        ident, err = resolve_anonymization(user, False)
        assert ident is False
        assert err is None


# ---------------------------------------------------------------------------
# _log_audit / log_export_audit
# ---------------------------------------------------------------------------

class TestAuditLogging:
    @patch("exports.services.ExportAuditLog.objects.create")
    def test_log_audit(self, mock_create):
        """Creates an audit log record with the correct fields."""
        from exports.services import _log_audit
        user = _user()
        course = _course()
        _log_audit(user, "roster", course, {"status": None}, True, 10)
        mock_create.assert_called_once_with(
            user=user,
            export_type="roster",
            scope_course=course,
            filters={"status": None},
            identifiable=True,
            row_count=10,
        )

    @patch("exports.services.ExportAuditLog.objects.create")
    def test_log_export_audit(self, mock_create):
        """Delegates to the underlying audit log creation."""
        from exports.services import log_export_audit
        user = _user()
        course = _course()
        log_export_audit(user, "submissions", course, {"x": 1}, identifiable=True, row_count=5)
        mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# _answer_value
# ---------------------------------------------------------------------------

class TestAnswerValue:
    def test_multiple_choice(self):
        """Extracts selected indices from a multiple choice answer."""
        from exports.services import _answer_value
        from types import SimpleNamespace
        answer = MagicMock()
        answer.answer_type = "MULTIPLE_CHOICE"
        answer.multiple_choice.selected.all.return_value = [
            SimpleNamespace(choice_index=0), SimpleNamespace(choice_index=2),
        ]
        result = _answer_value(answer)
        assert result == {"selected": [0, 2]}

    def test_multiple_choice_exception(self):
        """Returns empty dict when multiple choice sub-record is missing."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "MULTIPLE_CHOICE"
        answer.id = 99
        answer.multiple_choice.selected.all.side_effect = ObjectDoesNotExist("err")
        result = _answer_value(answer)
        assert result == {}

    def test_short_answer(self):
        """Extracts text from a short answer response."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "SHORT_ANSWER"
        answer.short_answer.text = "My answer"
        result = _answer_value(answer)
        assert result == {"text": "My answer"}

    def test_short_answer_exception(self):
        """Returns empty dict when short answer sub-record is missing."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "SHORT_ANSWER"
        answer.id = 99
        type(answer).short_answer = PropertyMock(side_effect=ObjectDoesNotExist("err"))
        result = _answer_value(answer)
        assert result == {}

    def test_number_scale(self):
        """Extracts val from a number scale answer."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "NUMBER_SCALE"
        answer.number_scale.val = 7
        result = _answer_value(answer)
        assert result == {"val": 7}

    def test_number_scale_exception(self):
        """Returns empty dict when number scale sub-record is missing."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "NUMBER_SCALE"
        answer.id = 99
        type(answer).number_scale = PropertyMock(side_effect=ObjectDoesNotExist("err"))
        result = _answer_value(answer)
        assert result == {}

    def test_unknown_type(self):
        """Returns empty dict for an unrecognized answer type."""
        from exports.services import _answer_value
        answer = MagicMock()
        answer.answer_type = "UNKNOWN"
        result = _answer_value(answer)
        assert result == {}


# ---------------------------------------------------------------------------
# _serialize_answers
# ---------------------------------------------------------------------------

class TestSerializeAnswers:
    def test_identifiable(self):
        """Includes question prompts in serialized output when identifiable."""
        import json
        from exports.services import _serialize_answers
        answer = MagicMock()
        answer.answer_type = "SHORT_ANSWER"
        answer.short_answer.text = "response"
        answer.score = 10
        answer.skipped = False
        answer.question = MagicMock()
        answer.question.prompt = "What is X?"

        sub = MagicMock()
        sub.answers.all.return_value = [answer]

        result = _serialize_answers(sub, identifiable=True)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["questionPrompt"] == "What is X?"
        assert parsed[0]["value"] == {"text": "response"}

    def test_anonymized(self):
        """Excludes question prompts from serialized output when anonymized."""
        import json
        from exports.services import _serialize_answers
        answer = MagicMock()
        answer.answer_type = "NUMBER_SCALE"
        answer.number_scale.val = 5
        answer.score = 5
        answer.skipped = False
        answer.question = MagicMock()
        answer.question.prompt = "Rate this"

        sub = MagicMock()
        sub.answers.all.return_value = [answer]

        result = _serialize_answers(sub, identifiable=False)
        parsed = json.loads(result)
        assert "questionPrompt" not in parsed[0]


# ---------------------------------------------------------------------------
# export_roster
# ---------------------------------------------------------------------------

class TestExportRoster:
    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Enrollment.objects.filter")
    def test_roster_identifiable(self, mock_filter, mock_audit):
        """Exports identifiable roster CSV with student IDs and BOM header."""
        from exports.services import export_roster, UTF8_BOM
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs

        enrollment = _enrollment(enrolled_at=MagicMock(isoformat=MagicMock(return_value="2025-01-01")))
        mock_qs.iterator.return_value = [enrollment]

        user = _user()
        course = _course()
        gen, count, is_anon = export_roster(user, course, identifiable=True)
        assert count == 1
        assert is_anon is False
        rows = list(gen)
        assert len(rows) == 2  # header + 1 data row
        assert rows[0].startswith(UTF8_BOM)

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Enrollment.objects.filter")
    def test_roster_anonymized(self, mock_filter, mock_audit):
        """Exports anonymized roster CSV without student identity columns."""
        from exports.services import export_roster
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs

        enrollment = _enrollment(enrolled_at=None)
        mock_qs.iterator.return_value = [enrollment]

        user = _user()
        course = _course()
        gen, count, is_anon = export_roster(user, course, identifiable=False)
        assert is_anon is True
        rows = list(gen)
        # Anonymized has fewer columns (no student ID/name/username)
        header = rows[0].decode("utf-8").lstrip("\ufeff")
        assert "studentId" not in header

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Enrollment.objects.filter")
    def test_roster_with_status_filter(self, mock_filter, mock_audit):
        """Applies enrollment status filter to roster query."""
        from exports.services import export_roster
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 0
        mock_qs.filter.return_value = mock_qs
        mock_qs.iterator.return_value = []

        user = _user()
        course = _course()
        gen, count, is_anon = export_roster(user, course, status_filter="ACTIVE", identifiable=True)
        assert count == 0
        # Ensure filter was called with status
        mock_qs.filter.assert_called()


# ---------------------------------------------------------------------------
# export_course_submissions
# ---------------------------------------------------------------------------

class TestExportCourseSubmissions:
    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_identifiable(self, mock_filter, mock_audit):
        """Exports identifiable submissions CSV with student IDs and BOM header."""
        from exports.services import export_course_submissions, UTF8_BOM
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        sub = _submission(submitted_at=MagicMock(isoformat=MagicMock(return_value="2025-01-01")))
        mock_qs.iterator.return_value = [sub]

        user = _user()
        course = _course()
        gen, count, is_anon = export_course_submissions(
            user, course, identifiable=True
        )
        assert count == 1
        assert is_anon is False
        rows = list(gen)
        assert len(rows) == 2
        assert rows[0].startswith(UTF8_BOM)

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_anonymized(self, mock_filter, mock_audit):
        """Exports anonymized submissions CSV without student identity columns."""
        from exports.services import export_course_submissions
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs

        sub = _submission(submitted_at=None)
        mock_qs.iterator.return_value = [sub]

        user = _user()
        course = _course()
        gen, count, is_anon = export_course_submissions(
            user, course, identifiable=False
        )
        assert is_anon is True
        rows = list(gen)
        header = rows[0].decode("utf-8").lstrip("\ufeff")
        assert "studentId" not in header

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_with_all_filters(self, mock_filter, mock_audit):
        """Applies all optional filters to the submissions query."""
        from exports.services import export_course_submissions
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 0
        mock_qs.filter.return_value = mock_qs
        mock_qs.iterator.return_value = []

        user = _user()
        course = _course()
        gen, count, is_anon = export_course_submissions(
            user, course,
            start_date="2025-01-01",
            end_date="2025-12-31",
            category="FORMATIVE",
            assignment_template_id=5,
            assignment_id=10,
            status_filter="SUBMITTED",
            identifiable=True,
        )
        assert count == 0

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_include_answers(self, mock_filter, mock_audit):
        """Includes answers column in CSV when include_answers is True."""
        from exports.services import export_course_submissions
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        answer = MagicMock()
        answer.answer_type = "SHORT_ANSWER"
        answer.short_answer.text = "ans"
        answer.score = 10
        answer.skipped = False
        answer.question = MagicMock()
        answer.question.prompt = "Q?"

        sub = _submission(submitted_at=MagicMock(isoformat=MagicMock(return_value="2025-01-01")))
        sub.answers = MagicMock()
        sub.answers.all.return_value = [answer]
        mock_qs.iterator.return_value = [sub]

        user = _user()
        course = _course()
        gen, count, is_anon = export_course_submissions(
            user, course, include_answers=True, identifiable=True
        )
        rows = list(gen)
        # Header should contain "answers" column
        header = rows[0].decode("utf-8").lstrip("\ufeff")
        assert "answers" in header

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_no_student(self, mock_filter, mock_audit):
        """Produces a data row even when submission has no linked student."""
        from exports.services import export_course_submissions
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs

        sub = _submission(has_student=False)
        mock_qs.iterator.return_value = [sub]

        user = _user()
        course = _course()
        gen, count, is_anon = export_course_submissions(
            user, course, identifiable=True
        )
        rows = list(gen)
        assert len(rows) == 2  # header + 1 row

    @patch("exports.services.ExportAuditLog.objects.create")
    @patch("exports.services.Submission.objects.filter")
    def test_submissions_consent_exception(self, mock_filter, mock_audit):
        """Handles missing student profile gracefully and still produces a row."""
        from exports.services import export_course_submissions
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.filter.return_value = mock_qs

        sub = _submission()
        # Make student_profile raise ObjectDoesNotExist (simulates RelatedObjectDoesNotExist)
        type(sub.student).student_profile = PropertyMock(side_effect=ObjectDoesNotExist("no profile"))
        mock_qs.iterator.return_value = [sub]

        user = _user()
        course = _course()
        gen, count, _ = export_course_submissions(user, course, identifiable=True)
        rows = list(gen)
        assert len(rows) == 2  # Should still produce a row, consent = ""


# ---------------------------------------------------------------------------
# _make_writer
# ---------------------------------------------------------------------------

class TestMakeWriter:
    def test_make_writer(self):
        """Returns a buffer and writer that produce CSV-formatted output."""
        from exports.services import _make_writer
        buf, writer = _make_writer()
        result = writer.writerow(["a", "b"])
        assert "a" in result
        assert "b" in result
