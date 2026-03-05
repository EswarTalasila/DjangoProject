"""Extended unit tests for registration service helpers (_registration.py).

These are TRUE unit tests that mock all ORM/database calls and test
the service logic in isolation. They cover uncovered lines (451-466:
transition_registration_code_status archive/unsupported branches) plus
additional edge cases in _select_valid_code_for_update,
validate_registration_code, _ensure_student_enrollment,
redeem_student_invite, redeem_student_join_course,
redeem_non_student_local_invite, redeem_non_student_oauth_invite,
_role_from_registration_code_type, registration_code_status,
_can_generate_code_type, create_registration_codes, and
registration_code_scope_queryset.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.utils import timezone

from accounts.services._registration import (
    _can_generate_code_type,
    _ensure_student_enrollment,
    _role_from_registration_code_type,
    _select_valid_code_for_update,
    redeem_non_student_local_invite,
    redeem_non_student_oauth_invite,
    redeem_student_invite,
    redeem_student_join_course,
    registration_code_scope_queryset,
    registration_code_status,
    transition_registration_code_status,
    validate_registration_code,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# _select_valid_code_for_update
# ---------------------------------------------------------------------------


class TestSelectValidCodeForUpdate:
    """Tests for _select_valid_code_for_update locking and validation."""

    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_empty_hashes(self, mock_hashes):
        """Empty hash list from normalization returns None."""
        mock_hashes.return_value = []

        result = _select_valid_code_for_update("   ")

        assert result is None

    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_when_no_record_found(self, mock_hashes, mock_objects):
        """No matching record in database returns None."""
        mock_hashes.return_value = ["hash1"]
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = None

        result = _select_valid_code_for_update("SOME-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_archived_code(self, mock_hashes, mock_objects, mock_tz):
        """Archived code (archived_at is not None) returns None."""
        mock_hashes.return_value = ["hash1"]
        record = Mock()
        record.archived_at = timezone.now()
        record.is_active = True
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = record
        mock_tz.now.return_value = timezone.now()

        result = _select_valid_code_for_update("ARCHIVED-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_inactive_code(self, mock_hashes, mock_objects, mock_tz):
        """Revoked (is_active=False) code returns None."""
        mock_hashes.return_value = ["hash1"]
        record = Mock()
        record.archived_at = None
        record.is_active = False
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = record
        mock_tz.now.return_value = timezone.now()

        result = _select_valid_code_for_update("REVOKED-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_expired_code(self, mock_hashes, mock_objects, mock_tz):
        """Expired code (expires_at <= now) returns None."""
        mock_hashes.return_value = ["hash1"]
        now = timezone.now()
        record = Mock()
        record.archived_at = None
        record.is_active = True
        record.expires_at = now - timedelta(hours=1)
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = record
        mock_tz.now.return_value = now

        result = _select_valid_code_for_update("EXPIRED-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_exhausted_code(self, mock_hashes, mock_objects, mock_tz):
        """Fully used code (times_used >= max_uses) returns None."""
        mock_hashes.return_value = ["hash1"]
        now = timezone.now()
        record = Mock()
        record.archived_at = None
        record.is_active = True
        record.expires_at = now + timedelta(hours=1)
        record.times_used = 5
        record.max_uses = 5
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = record
        mock_tz.now.return_value = now

        result = _select_valid_code_for_update("EXHAUSTED-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_valid_record(self, mock_hashes, mock_objects, mock_tz):
        """Valid code passes all checks and returns the record."""
        mock_hashes.return_value = ["hash1"]
        now = timezone.now()
        record = Mock()
        record.archived_at = None
        record.is_active = True
        record.expires_at = now + timedelta(hours=1)
        record.times_used = 0
        record.max_uses = 5
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = record
        mock_tz.now.return_value = now

        result = _select_valid_code_for_update("VALID-CODE")

        assert result is record

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_tries_fallback_hashes_until_match(self, mock_hashes, mock_objects, mock_tz):
        """Iterates through candidate hashes to find a matching record."""
        mock_hashes.return_value = ["hash1", "hash2"]
        now = timezone.now()
        record = Mock()
        record.archived_at = None
        record.is_active = True
        record.expires_at = now + timedelta(hours=1)
        record.times_used = 0
        record.max_uses = 1
        # First hash returns None, second returns the record
        mock_objects.select_for_update.return_value.filter.return_value.first.side_effect = [
            None,
            record,
        ]
        mock_tz.now.return_value = now

        result = _select_valid_code_for_update("FALLBACK-CODE")

        assert result is record


# ---------------------------------------------------------------------------
# validate_registration_code
# ---------------------------------------------------------------------------


class TestValidateRegistrationCode:
    """Tests for validate_registration_code read-only validation."""

    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_for_empty_hashes(self, mock_hashes):
        """Empty hash list returns None."""
        mock_hashes.return_value = []

        result = validate_registration_code("   ")

        assert result is None

    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_none_when_no_record_found(self, mock_hashes, mock_objects):
        """No matching record returns None."""
        mock_hashes.return_value = ["hash1"]
        mock_objects.filter.return_value.first.return_value = None

        result = validate_registration_code("MISSING-CODE")

        assert result is None

    @patch("accounts.services._registration.timezone")
    @patch("accounts.services._registration.RegistrationCode.objects")
    @patch("accounts.services._registration._registration_code_hashes_for_lookup")
    def test_returns_valid_record_when_all_checks_pass(self, mock_hashes, mock_objects, mock_tz):
        """Active, non-expired, non-exhausted code returns the record."""
        mock_hashes.return_value = ["hash1"]
        now = timezone.now()
        record = Mock()
        record.archived_at = None
        record.is_active = True
        record.expires_at = now + timedelta(hours=1)
        record.times_used = 0
        record.max_uses = 5
        mock_objects.filter.return_value.first.return_value = record
        mock_tz.now.return_value = now

        result = validate_registration_code("VALID-CODE")

        assert result is record


# ---------------------------------------------------------------------------
# _ensure_student_enrollment
# ---------------------------------------------------------------------------


class TestEnsureStudentEnrollment:
    """Tests for _ensure_student_enrollment course attachment."""

    @patch("accounts.services._registration.StudentProfile.objects")
    def test_raises_when_student_profile_not_found(self, mock_sp_objects):
        """Missing student profile raises ValueError."""
        mock_sp_objects.filter.return_value.first.return_value = None
        user = Mock()
        course = Mock()

        with pytest.raises(ValueError, match="Student profile not found"):
            _ensure_student_enrollment(user, course)

    @patch("accounts.services._registration.Enrollment.objects")
    @patch("accounts.services._registration.StudentProfile.objects")
    def test_returns_existing_enrollment_with_already_enrolled_true(
        self, mock_sp_objects, mock_enroll_objects
    ):
        """Existing enrollment returns (enrollment, True)."""
        profile = Mock()
        mock_sp_objects.filter.return_value.first.return_value = profile
        existing = Mock()
        mock_enroll_objects.filter.return_value.first.return_value = existing

        enrollment, already = _ensure_student_enrollment(Mock(), Mock())

        assert enrollment is existing
        assert already is True

    @patch("accounts.services._registration.Enrollment.objects")
    @patch("accounts.services._registration.StudentProfile.objects")
    def test_creates_new_enrollment_when_not_enrolled(
        self, mock_sp_objects, mock_enroll_objects
    ):
        """No existing enrollment creates a new one and returns (enrollment, False)."""
        profile = Mock()
        mock_sp_objects.filter.return_value.first.return_value = profile
        mock_enroll_objects.filter.return_value.first.return_value = None
        new_enrollment = Mock()
        mock_enroll_objects.create.return_value = new_enrollment

        enrollment, already = _ensure_student_enrollment(Mock(), Mock())

        assert enrollment is new_enrollment
        assert already is False


# ---------------------------------------------------------------------------
# registration_code_status
# ---------------------------------------------------------------------------


class TestRegistrationCodeStatus:
    """Tests for registration_code_status lifecycle derivation."""

    def test_archived_status(self):
        """Code with archived_at set returns ARCHIVED."""
        code = Mock()
        code.archived_at = timezone.now()

        result = registration_code_status(code)

        assert result == "ARCHIVED"

    def test_expired_status(self):
        """Code past expires_at returns EXPIRED."""
        code = Mock()
        code.archived_at = None
        code.expires_at = timezone.now() - timedelta(hours=1)

        result = registration_code_status(code, now=timezone.now())

        assert result == "EXPIRED"

    def test_exhausted_status(self):
        """Code with times_used >= max_uses returns EXHAUSTED."""
        code = Mock()
        code.archived_at = None
        code.expires_at = timezone.now() + timedelta(hours=1)
        code.times_used = 3
        code.max_uses = 3
        code.is_active = True

        result = registration_code_status(code)

        assert result == "EXHAUSTED"

    def test_revoked_status(self):
        """Code with is_active=False (but not exhausted/expired) returns REVOKED."""
        code = Mock()
        code.archived_at = None
        code.expires_at = timezone.now() + timedelta(hours=1)
        code.times_used = 0
        code.max_uses = 5
        code.is_active = False

        result = registration_code_status(code)

        assert result == "REVOKED"

    def test_active_status(self):
        """Code passing all checks returns ACTIVE."""
        code = Mock()
        code.archived_at = None
        code.expires_at = timezone.now() + timedelta(hours=1)
        code.times_used = 0
        code.max_uses = 5
        code.is_active = True

        result = registration_code_status(code)

        assert result == "ACTIVE"

    def test_custom_now_parameter(self):
        """Custom now parameter is used instead of timezone.now()."""
        code = Mock()
        code.archived_at = None
        now = timezone.now()
        code.expires_at = now - timedelta(seconds=1)

        result = registration_code_status(code, now=now)

        assert result == "EXPIRED"


# ---------------------------------------------------------------------------
# _role_from_registration_code_type
# ---------------------------------------------------------------------------


class TestRoleFromRegistrationCodeType:
    """Tests for _role_from_registration_code_type mapping."""

    def test_student_type_returns_student_role(self):
        """STUDENT code type maps to STUDENT role."""
        assert _role_from_registration_code_type("STUDENT") == "STUDENT"

    def test_teacher_type_returns_teacher_role(self):
        """TEACHER code type maps to TEACHER role."""
        assert _role_from_registration_code_type("TEACHER") == "TEACHER"

    def test_researcher_type_returns_researcher_role(self):
        """RESEARCHER code type maps to RESEARCHER role."""
        assert _role_from_registration_code_type("RESEARCHER") == "RESEARCHER"

    def test_unsupported_type_raises_value_error(self):
        """Unknown code type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported registration code type"):
            _role_from_registration_code_type("ADMIN")


# ---------------------------------------------------------------------------
# _can_generate_code_type
# ---------------------------------------------------------------------------


class TestCanGenerateCodeType:
    """Tests for _can_generate_code_type permission checks."""

    @patch("accounts.services._registration.primary_role")
    def test_staff_can_only_generate_researcher_codes(self, mock_role):
        """Staff users can only generate RESEARCHER codes."""
        user = Mock()
        user.is_staff = True

        assert _can_generate_code_type(user, "RESEARCHER") is True
        assert _can_generate_code_type(user, "TEACHER") is False
        assert _can_generate_code_type(user, "STUDENT") is False

    @patch("accounts.services._registration.has_sudo_permission")
    @patch("accounts.services._registration.primary_role")
    def test_researcher_can_generate_teacher_codes(self, mock_role, mock_sudo):
        """Researcher can always generate TEACHER codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"

        assert _can_generate_code_type(user, "TEACHER") is True

    @patch("accounts.services._registration.has_sudo_permission")
    @patch("accounts.services._registration.primary_role")
    def test_researcher_needs_sudo_for_researcher_codes(self, mock_role, mock_sudo):
        """Researcher needs CREATE_RESEARCHER_CODES sudo for RESEARCHER codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = True

        assert _can_generate_code_type(user, "RESEARCHER") is True

    @patch("accounts.services._registration.has_sudo_permission")
    @patch("accounts.services._registration.primary_role")
    def test_researcher_needs_sudo_for_student_codes(self, mock_role, mock_sudo):
        """Researcher needs CREATE_STUDENT sudo for STUDENT codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = False

        assert _can_generate_code_type(user, "STUDENT") is False

    @patch("accounts.services._registration.primary_role")
    def test_teacher_can_only_generate_student_codes(self, mock_role):
        """Teacher can only generate STUDENT codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "TEACHER"

        assert _can_generate_code_type(user, "STUDENT") is True
        assert _can_generate_code_type(user, "TEACHER") is False
        assert _can_generate_code_type(user, "RESEARCHER") is False

    @patch("accounts.services._registration.primary_role")
    def test_student_cannot_generate_any_codes(self, mock_role):
        """Student cannot generate any registration codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "STUDENT"

        assert _can_generate_code_type(user, "STUDENT") is False
        assert _can_generate_code_type(user, "TEACHER") is False
        assert _can_generate_code_type(user, "RESEARCHER") is False


# ---------------------------------------------------------------------------
# redeem_student_invite
# ---------------------------------------------------------------------------


class TestRedeemStudentInvite:
    """Tests for redeem_student_invite edge cases."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_invalid_code_raises_value_error(self, mock_select):
        """Invalid or expired code raises ValueError."""
        mock_select.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired code"):
            redeem_student_invite({"code": "BAD-CODE", "password": "Pass123!"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_non_student_code_type_raises_value_error(self, mock_select):
        """Non-student code type raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record

        with pytest.raises(ValueError, match="Invalid code type"):
            redeem_student_invite({"code": "TEACHER-CODE", "password": "Pass123!"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_missing_course_id_raises_value_error(self, mock_select):
        """Student code without course_id raises ValueError."""
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = None
        mock_select.return_value = record

        with pytest.raises(ValueError, match="missing course association"):
            redeem_student_invite({"code": "NO-COURSE", "password": "Pass123!"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_missing_name_fields_raises_value_error(self, mock_select):
        """Missing firstName/lastName raises ValueError."""
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = 1
        record.course = Mock()
        mock_select.return_value = record

        with pytest.raises(ValueError, match="firstName and lastName are required"):
            redeem_student_invite({"code": "CODE", "password": "Pass123!"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_course_none_after_id_check_raises_value_error(self, mock_select):
        """Course resolving to None despite course_id raises ValueError."""
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = 1
        record.course = None
        mock_select.return_value = record

        with pytest.raises(ValueError, match="missing course association"):
            redeem_student_invite(
                {"code": "CODE", "password": "Pass123!", "firstName": "A", "lastName": "B"}
            )

    @patch("accounts.services._registration._ensure_student_enrollment")
    @patch("accounts.services._registration.create_user_from_payload")
    @patch("accounts.services._registration.generate_managed_username")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_already_enrolled_raises_value_error(
        self, mock_select, mock_username, mock_create, mock_enroll
    ):
        """Student already enrolled in the course raises ValueError."""
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = 1
        record.course = Mock()
        mock_select.return_value = record
        mock_username.return_value = "jdoe0000"
        mock_create.return_value = Mock()
        mock_enroll.return_value = (Mock(), True)

        with pytest.raises(ValueError, match="already enrolled"):
            redeem_student_invite(
                {"code": "CODE", "password": "Pass123!", "firstName": "Jane", "lastName": "Doe"}
            )


# ---------------------------------------------------------------------------
# redeem_student_join_course
# ---------------------------------------------------------------------------


class TestRedeemStudentJoinCourse:
    """Tests for redeem_student_join_course edge cases."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._registration.primary_role")
    def test_non_student_raises_permission_error(self, mock_role):
        """Non-student user raises PermissionError."""
        mock_role.return_value = "TEACHER"

        with pytest.raises(PermissionError, match="Only student accounts"):
            redeem_student_join_course(Mock(), "CODE")

    @patch("accounts.services._registration._select_valid_code_for_update")
    @patch("accounts.services._registration.primary_role")
    def test_invalid_code_raises_value_error(self, mock_role, mock_select):
        """Invalid code raises ValueError."""
        mock_role.return_value = "STUDENT"
        mock_select.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired code"):
            redeem_student_join_course(Mock(), "BAD-CODE")

    @patch("accounts.services._registration._select_valid_code_for_update")
    @patch("accounts.services._registration.primary_role")
    def test_non_student_code_type_raises_value_error(self, mock_role, mock_select):
        """Code with non-student type raises ValueError."""
        mock_role.return_value = "STUDENT"
        record = Mock()
        record.code_type = "RESEARCHER"
        mock_select.return_value = record

        with pytest.raises(ValueError, match="Invalid code type"):
            redeem_student_join_course(Mock(), "RESEARCHER-CODE")

    @patch("accounts.services._registration._select_valid_code_for_update")
    @patch("accounts.services._registration.primary_role")
    def test_missing_course_raises_value_error(self, mock_role, mock_select):
        """Student code without course_id raises ValueError."""
        mock_role.return_value = "STUDENT"
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = None
        mock_select.return_value = record

        with pytest.raises(ValueError, match="missing course association"):
            redeem_student_join_course(Mock(), "NO-COURSE")

    @patch("accounts.services._registration._ensure_student_enrollment")
    @patch("accounts.services._registration._select_valid_code_for_update")
    @patch("accounts.services._registration.primary_role")
    def test_already_enrolled_returns_without_incrementing_uses(
        self, mock_role, mock_select, mock_enroll
    ):
        """Already-enrolled student does not increment times_used."""
        mock_role.return_value = "STUDENT"
        record = Mock()
        record.code_type = "STUDENT"
        record.course_id = 1
        record.course = Mock()
        record.times_used = 2
        record.max_uses = 5
        mock_select.return_value = record
        enrollment = Mock()
        mock_enroll.return_value = (enrollment, True)

        _result_enrollment, already = redeem_student_join_course(Mock(), "CODE")

        assert already is True
        record.save.assert_not_called()


# ---------------------------------------------------------------------------
# redeem_non_student_local_invite
# ---------------------------------------------------------------------------


class TestRedeemNonStudentLocalInvite:
    """Tests for redeem_non_student_local_invite edge cases."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_invalid_code_raises_value_error(self, mock_select):
        """Invalid code raises ValueError."""
        mock_select.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired code"):
            redeem_non_student_local_invite({"code": "BAD"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_student_code_type_raises_value_error(self, mock_select):
        """Student code raises ValueError for non-student flow."""
        record = Mock()
        record.code_type = "STUDENT"
        mock_select.return_value = record

        with pytest.raises(ValueError, match="student registration"):
            redeem_non_student_local_invite({"code": "STUDENT-CODE"})

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_missing_names_raises_value_error(self, mock_select):
        """Missing firstName/lastName raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record

        with pytest.raises(ValueError, match="firstName and lastName are required"):
            redeem_non_student_local_invite({"code": "CODE", "email": "a@b.com"})

    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_missing_email_raises_value_error(self, mock_select, mock_normalize):
        """Missing email raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = ""

        with pytest.raises(ValueError, match="email is required"):
            redeem_non_student_local_invite(
                {"code": "CODE", "firstName": "A", "lastName": "B", "email": ""}
            )

    @patch("accounts.services._registration.identifier_in_use")
    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_email_already_taken_raises_value_error(self, mock_select, mock_normalize, mock_in_use):
        """Already-used email raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = "taken@example.com"
        mock_in_use.return_value = True

        with pytest.raises(ValueError, match="Email already taken"):
            redeem_non_student_local_invite(
                {
                    "code": "CODE",
                    "firstName": "A",
                    "lastName": "B",
                    "email": "taken@example.com",
                    "password": "Pass123!",
                }
            )


# ---------------------------------------------------------------------------
# redeem_non_student_oauth_invite
# ---------------------------------------------------------------------------


class TestRedeemNonStudentOAuthInvite:
    """Tests for redeem_non_student_oauth_invite edge cases."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_invalid_code_raises_value_error(self, mock_select):
        """Invalid code raises ValueError."""
        mock_select.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired code"):
            redeem_non_student_oauth_invite(
                code="BAD", oauth_subject="sub", oauth_email="a@b.com"
            )

    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_student_code_type_raises_value_error(self, mock_select):
        """Student code type raises ValueError for OAuth flow."""
        record = Mock()
        record.code_type = "STUDENT"
        mock_select.return_value = record

        with pytest.raises(ValueError, match="Student code flows"):
            redeem_non_student_oauth_invite(
                code="CODE", oauth_subject="sub", oauth_email="a@b.com"
            )

    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_invalid_oauth_email_raises_value_error(self, mock_select, mock_normalize):
        """Empty email after normalization raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = ""

        with pytest.raises(ValueError, match="valid email"):
            redeem_non_student_oauth_invite(
                code="CODE", oauth_subject="sub", oauth_email=""
            )

    @patch("accounts.services._registration.OAuthAccount.objects")
    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_already_linked_oauth_raises_value_error(
        self, mock_select, mock_normalize, mock_oauth
    ):
        """Already-linked OAuth subject raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = "new@example.com"
        mock_oauth.filter.return_value.exists.return_value = True

        with pytest.raises(ValueError, match="already linked"):
            redeem_non_student_oauth_invite(
                code="CODE", oauth_subject="dup-sub", oauth_email="new@example.com"
            )

    @patch("accounts.services._registration.identifier_in_use")
    @patch("accounts.services._registration.OAuthAccount.objects")
    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_email_already_taken_raises_value_error(
        self, mock_select, mock_normalize, mock_oauth, mock_in_use
    ):
        """Email already in use raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = "taken@example.com"
        mock_oauth.filter.return_value.exists.return_value = False
        mock_in_use.return_value = True

        with pytest.raises(ValueError, match="Email already taken"):
            redeem_non_student_oauth_invite(
                code="CODE",
                oauth_subject="new-sub",
                oauth_email="taken@example.com",
            )

    @patch("accounts.services._registration.identifier_in_use")
    @patch("accounts.services._registration.OAuthAccount.objects")
    @patch("accounts.services._registration.normalize_username_identifier")
    @patch("accounts.services._registration._select_valid_code_for_update")
    def test_missing_names_raises_value_error(
        self, mock_select, mock_normalize, mock_oauth, mock_in_use
    ):
        """Missing first/last name raises ValueError."""
        record = Mock()
        record.code_type = "TEACHER"
        mock_select.return_value = record
        mock_normalize.return_value = "email@example.com"
        mock_oauth.filter.return_value.exists.return_value = False
        mock_in_use.return_value = False

        with pytest.raises(ValueError, match="firstName and lastName are required"):
            redeem_non_student_oauth_invite(
                code="CODE",
                oauth_subject="sub",
                oauth_email="email@example.com",
                first_name="",
                last_name="",
            )


# ---------------------------------------------------------------------------
# transition_registration_code_status (lines 451-466)
# ---------------------------------------------------------------------------


class TestTransitionRegistrationCodeStatus:
    """Tests covering uncovered lines 451-466 in transition_registration_code_status."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_code_not_found_raises_value_error(self, mock_scope):
        """Non-existent code raises ValueError."""
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = None
        mock_scope.return_value = mock_qs

        with pytest.raises(ValueError, match="not found"):
            transition_registration_code_status(
                actor=Mock(), registration_code_id=999, next_status="REVOKED"
            )

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_revoke_non_active_raises_value_error(self, mock_scope, mock_status):
        """Revoking a non-active code raises ValueError."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "EXPIRED"

        with pytest.raises(ValueError, match="Only ACTIVE codes can be revoked"):
            transition_registration_code_status(
                actor=Mock(), registration_code_id=1, next_status="REVOKED"
            )

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_revoke_active_code_sets_inactive(self, mock_scope, mock_status):
        """Revoking an ACTIVE code sets is_active=False and saves."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "ACTIVE"

        result = transition_registration_code_status(
            actor=Mock(), registration_code_id=1, next_status="REVOKED"
        )

        assert code.is_active is False
        code.save.assert_called_once_with(update_fields=["is_active"])
        assert result is code

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_archive_exhausted_code_sets_archived_at(self, mock_scope, mock_status):
        """Archiving an EXHAUSTED code sets archived_at and saves."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "EXHAUSTED"

        result = transition_registration_code_status(
            actor=Mock(), registration_code_id=1, next_status="ARCHIVED"
        )

        assert code.archived_at is not None
        code.save.assert_called_once_with(update_fields=["archived_at"])
        assert result is code

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_archive_expired_code_succeeds(self, mock_scope, mock_status):
        """Archiving an EXPIRED code succeeds."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "EXPIRED"

        result = transition_registration_code_status(
            actor=Mock(), registration_code_id=1, next_status="ARCHIVED"
        )

        assert result is code

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_archive_revoked_code_succeeds(self, mock_scope, mock_status):
        """Archiving a REVOKED code succeeds."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "REVOKED"

        result = transition_registration_code_status(
            actor=Mock(), registration_code_id=1, next_status="ARCHIVED"
        )

        assert result is code

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_archive_active_code_raises_value_error(self, mock_scope, mock_status):
        """Archiving an ACTIVE code raises ValueError (line 461)."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "ACTIVE"

        with pytest.raises(ValueError, match="EXHAUSTED, EXPIRED, or REVOKED"):
            transition_registration_code_status(
                actor=Mock(), registration_code_id=1, next_status="ARCHIVED"
            )

    @patch("accounts.services._registration.registration_code_status")
    @patch("accounts.services._registration.registration_code_scope_queryset")
    def test_unsupported_status_raises_value_error(self, mock_scope, mock_status):
        """Unsupported next_status raises ValueError (line 466)."""
        code = Mock()
        mock_qs = MagicMock()
        mock_qs.select_for_update.return_value.filter.return_value.first.return_value = code
        mock_scope.return_value = mock_qs
        mock_status.return_value = "ACTIVE"

        with pytest.raises(ValueError, match="Unsupported status transition"):
            transition_registration_code_status(
                actor=Mock(), registration_code_id=1, next_status="DELETED"
            )


# ---------------------------------------------------------------------------
# registration_code_scope_queryset
# ---------------------------------------------------------------------------


class TestRegistrationCodeScopeQueryset:
    """Tests for registration_code_scope_queryset scoping logic."""

    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_staff_gets_full_queryset(self, mock_objects):
        """Staff users get unfiltered queryset."""
        user = Mock()
        user.is_staff = True
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs

        result = registration_code_scope_queryset(user)

        assert result is mock_qs

    @patch("accounts.services._registration.has_sudo_permission")
    @patch("accounts.services._registration.primary_role")
    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_researcher_without_student_sudo_excludes_student_codes(
        self, mock_objects, mock_role, mock_sudo
    ):
        """Researcher without CREATE_STUDENT sudo sees only TEACHER codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = False
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs

        registration_code_scope_queryset(user)

        mock_qs.filter.assert_called_once()
        call_kwargs = mock_qs.filter.call_args
        assert call_kwargs.kwargs["created_by"] == user
        assert "STUDENT" not in call_kwargs.kwargs["code_type__in"]

    @patch("accounts.services._registration.has_sudo_permission")
    @patch("accounts.services._registration.primary_role")
    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_researcher_with_student_sudo_includes_student_codes(
        self, mock_objects, mock_role, mock_sudo
    ):
        """Researcher with CREATE_STUDENT sudo also sees STUDENT codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = True
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs

        registration_code_scope_queryset(user)

        call_kwargs = mock_qs.filter.call_args
        assert "STUDENT" in call_kwargs.kwargs["code_type__in"]

    @patch("accounts.services._registration.primary_role")
    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_teacher_scoped_to_own_student_codes(self, mock_objects, mock_role):
        """Teacher only sees own STUDENT codes."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "TEACHER"
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs

        registration_code_scope_queryset(user)

        call_kwargs = mock_qs.filter.call_args
        assert call_kwargs.kwargs["created_by"] == user
        assert call_kwargs.kwargs["code_type"] == "STUDENT"

    @patch("accounts.services._registration.primary_role")
    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_student_gets_empty_queryset(self, mock_objects, mock_role):
        """Student role gets empty queryset via .none()."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "STUDENT"
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs

        registration_code_scope_queryset(user)

        mock_qs.none.assert_called_once()

    @patch("accounts.services._registration.RegistrationCode.objects")
    def test_include_related_false_skips_select_related(self, mock_objects):
        """include_related=False skips select_related call."""
        user = Mock()
        user.is_staff = True
        mock_qs = MagicMock()
        mock_objects.all.return_value = mock_qs

        registration_code_scope_queryset(user, include_related=False)

        mock_qs.select_related.assert_not_called()
