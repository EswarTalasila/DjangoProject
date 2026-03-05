"""Extended pure unit tests for password reset service functions.

All ORM calls are mocked. No database access is required. These tests
cover the uncovered lines in src/accounts/services/_password_reset.py:
  - _expire_open_reset_requests (lines 30-31)
  - _teacher_can_issue_for_student (lines 43-46)
  - _authorize_reset_issuance (lines 55-88)
  - issue_password_reset_code (lines 98-125)
  - verify_password_reset_code (lines 130-151)
  - complete_password_reset (lines 161-194)
  - cleanup_temporary_reset_codes (lines 206-223)
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.utils import timezone

from accounts.models import Role, SudoPermission

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helper: neutralise @transaction.atomic
# ---------------------------------------------------------------------------


class _NoopAtomicMixin:
    """Mixin that patches transaction.Atomic so it never touches the database."""

    def setup_method(self):
        self._p_enter = patch(
            "django.db.transaction.Atomic.__enter__", return_value=None
        )
        self._p_exit = patch(
            "django.db.transaction.Atomic.__exit__", return_value=False
        )
        self._p_enter.start()
        self._p_exit.start()

    def teardown_method(self):
        self._p_exit.stop()
        self._p_enter.stop()


# ---------------------------------------------------------------------------
# _expire_open_reset_requests
# ---------------------------------------------------------------------------


class TestExpireOpenResetRequests:
    """Tests for _expire_open_reset_requests helper."""

    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset.PasswordResetRequest")
    def test_updates_pending_and_approved_requests(self, mock_pr_model, mock_tz):
        """Expires open requests for the target user and sets reviewer."""
        from accounts.services._password_reset import _expire_open_reset_requests

        now = timezone.now()
        mock_tz.now.return_value = now
        mock_qs = MagicMock()
        mock_pr_model.objects.select_for_update.return_value.filter.return_value = mock_qs

        target = Mock(spec=["pk"])
        reviewer = Mock(spec=["pk"])

        _expire_open_reset_requests(target_user=target, reviewer=reviewer)

        mock_pr_model.objects.select_for_update.return_value.filter.assert_called_once()
        mock_qs.update.assert_called_once()
        call_kwargs = mock_qs.update.call_args.kwargs
        assert call_kwargs["reviewed_by"] is reviewer
        assert call_kwargs["reviewed_at"] is now


# ---------------------------------------------------------------------------
# _teacher_can_issue_for_student
# ---------------------------------------------------------------------------


class TestTeacherCanIssueForStudent:
    """Tests for _teacher_can_issue_for_student helper."""

    @patch("accounts.services._password_reset.Enrollment")
    @patch("accounts.services._password_reset.StudentProfile")
    def test_returns_false_when_no_student_profile(self, mock_sp, mock_enroll):
        """Returns False when the student has no StudentProfile."""
        from accounts.services._password_reset import _teacher_can_issue_for_student

        mock_sp.objects.filter.return_value.first.return_value = None

        result = _teacher_can_issue_for_student(teacher=Mock(), student=Mock())

        assert result is False
        mock_enroll.objects.filter.assert_not_called()

    @patch("accounts.services._password_reset.Enrollment")
    @patch("accounts.services._password_reset.StudentProfile")
    def test_returns_true_when_actively_enrolled(self, mock_sp, mock_enroll):
        """Returns True when student is actively enrolled in a teacher course."""
        from accounts.services._password_reset import _teacher_can_issue_for_student

        mock_profile = Mock()
        mock_sp.objects.filter.return_value.first.return_value = mock_profile
        mock_enroll.objects.filter.return_value.exists.return_value = True

        result = _teacher_can_issue_for_student(teacher=Mock(), student=Mock())

        assert result is True

    @patch("accounts.services._password_reset.Enrollment")
    @patch("accounts.services._password_reset.StudentProfile")
    def test_returns_false_when_not_enrolled(self, mock_sp, mock_enroll):
        """Returns False when student is not enrolled in any teacher course."""
        from accounts.services._password_reset import _teacher_can_issue_for_student

        mock_profile = Mock()
        mock_sp.objects.filter.return_value.first.return_value = mock_profile
        mock_enroll.objects.filter.return_value.exists.return_value = False

        result = _teacher_can_issue_for_student(teacher=Mock(), student=Mock())

        assert result is False


# ---------------------------------------------------------------------------
# _authorize_reset_issuance
# ---------------------------------------------------------------------------


class TestAuthorizeResetIssuance:
    """Tests for _authorize_reset_issuance permission logic."""

    def test_self_issuance_raises(self):
        """Self-issuance is always denied."""
        from accounts.services._password_reset import _authorize_reset_issuance

        user = Mock()
        user.pk = 1

        with pytest.raises(PermissionError, match="Permission denied"):
            _authorize_reset_issuance(issuer=user, target=user)

    def test_admin_target_raises(self):
        """Reset codes cannot be issued for admin accounts."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        target = Mock()
        target.pk = 2
        target.is_staff = True

        with pytest.raises(PermissionError, match="admin accounts"):
            _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.primary_role")
    def test_ineligible_target_role_raises(self, mock_role):
        """Target role not in eligible set raises PermissionError."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = True
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.return_value = "UNKNOWN_ROLE"

        with pytest.raises(PermissionError, match="not eligible"):
            _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.primary_role")
    def test_admin_issuer_passes(self, mock_role):
        """Admin issuer can issue for any eligible target role."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = True
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.return_value = Role.STUDENT

        # Should not raise
        _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset._teacher_can_issue_for_student")
    @patch("accounts.services._password_reset.primary_role")
    def test_teacher_can_issue_for_enrolled_student(self, mock_role, mock_teacher_check):
        """Teacher can issue reset for their enrolled student."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.STUDENT, Role.TEACHER]
        mock_teacher_check.return_value = True

        _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.primary_role")
    def test_teacher_cannot_issue_for_non_student(self, mock_role):
        """Teacher cannot issue reset for non-student roles."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.TEACHER, Role.TEACHER]

        with pytest.raises(PermissionError, match="only issue reset codes for students"):
            _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset._teacher_can_issue_for_student")
    @patch("accounts.services._password_reset.primary_role")
    def test_teacher_cannot_issue_for_unenrolled_student(self, mock_role, mock_teacher_check):
        """Teacher cannot issue for student not in their courses."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.STUDENT, Role.TEACHER]
        mock_teacher_check.return_value = False

        with pytest.raises(PermissionError, match="not enrolled"):
            _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.primary_role")
    def test_researcher_can_issue_for_teacher(self, mock_role):
        """Researcher can issue reset for teachers without sudo."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.TEACHER, Role.RESEARCHER]

        _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.has_sudo_permission")
    @patch("accounts.services._password_reset.primary_role")
    def test_researcher_with_sudo_can_issue_for_student(self, mock_role, mock_sudo):
        """Researcher with ISSUE_STUDENT_RESET_CODE sudo can issue for students."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.STUDENT, Role.RESEARCHER]
        mock_sudo.return_value = True

        _authorize_reset_issuance(issuer=issuer, target=target)
        mock_sudo.assert_called_once_with(issuer, SudoPermission.ISSUE_STUDENT_RESET_CODE)

    @patch("accounts.services._password_reset.has_sudo_permission")
    @patch("accounts.services._password_reset.primary_role")
    def test_researcher_with_sudo_can_issue_for_researcher(self, mock_role, mock_sudo):
        """Researcher with ISSUE_RESEARCHER_RESET_CODE sudo can issue for researchers."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.RESEARCHER, Role.RESEARCHER]
        mock_sudo.return_value = True

        _authorize_reset_issuance(issuer=issuer, target=target)
        mock_sudo.assert_called_once_with(issuer, SudoPermission.ISSUE_RESEARCHER_RESET_CODE)

    @patch("accounts.services._password_reset.has_sudo_permission")
    @patch("accounts.services._password_reset.primary_role")
    def test_researcher_without_sudo_cannot_issue_for_student(self, mock_role, mock_sudo):
        """Researcher without sudo cannot issue for students."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.STUDENT, Role.RESEARCHER]
        mock_sudo.return_value = False

        with pytest.raises(PermissionError, match="Not authorized"):
            _authorize_reset_issuance(issuer=issuer, target=target)

    @patch("accounts.services._password_reset.primary_role")
    def test_student_issuer_raises(self, mock_role):
        """Student role cannot issue reset codes."""
        from accounts.services._password_reset import _authorize_reset_issuance

        issuer = Mock()
        issuer.pk = 1
        issuer.is_staff = False
        target = Mock()
        target.pk = 2
        target.is_staff = False
        mock_role.side_effect = [Role.STUDENT, Role.STUDENT]

        with pytest.raises(PermissionError, match="Not authorized"):
            _authorize_reset_issuance(issuer=issuer, target=target)


# ---------------------------------------------------------------------------
# issue_password_reset_code
# ---------------------------------------------------------------------------


class TestIssuePasswordResetCode(_NoopAtomicMixin):
    """Tests for issue_password_reset_code transactional function."""

    @patch("accounts.services._password_reset.User")
    def test_raises_when_target_not_found(self, mock_user_model):
        """Raises ValueError when target user does not exist."""
        from accounts.services._password_reset import issue_password_reset_code

        mock_user_model.objects.select_for_update.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Target user not found"):
            issue_password_reset_code(issuer=Mock(), target_user_id=999)

    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.PasswordResetRequest")
    @patch("accounts.services._password_reset._generate_secret_token")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.normalize_username_identifier")
    @patch("accounts.services._password_reset.primary_role")
    @patch("accounts.services._password_reset._expire_open_reset_requests")
    @patch("accounts.services._password_reset._authorize_reset_issuance")
    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset.User")
    def test_happy_path_creates_request_and_code(
        self, mock_user_model, mock_tz, mock_auth, mock_expire,
        mock_primary_role, mock_normalize, mock_hash, mock_gen,
        mock_pr_model, mock_code_model,
    ):
        """Successful issuance creates a request and code, returns both."""
        from accounts.services._password_reset import issue_password_reset_code

        target = Mock()
        target.username = "student1"
        mock_user_model.objects.select_for_update.return_value.filter.return_value.first.return_value = target

        now = timezone.now()
        mock_tz.now.return_value = now
        mock_primary_role.return_value = Role.STUDENT
        mock_normalize.return_value = "student1"
        mock_hash.return_value = "hashed"
        mock_gen.side_effect = ["REQ-TOKEN", "RESET-CODE"]

        fake_request = Mock()
        fake_request.expires_at = now + timedelta(minutes=30)
        mock_pr_model.objects.create.return_value = fake_request

        result_request, result_code = issue_password_reset_code(
            issuer=Mock(), target_user_id=42,
        )

        assert result_request is fake_request
        assert result_code == "RESET-CODE"
        mock_auth.assert_called_once()
        mock_expire.assert_called_once()
        mock_pr_model.objects.create.assert_called_once()
        mock_code_model.objects.create.assert_called_once()


# ---------------------------------------------------------------------------
# verify_password_reset_code
# ---------------------------------------------------------------------------


class TestVerifyPasswordResetCode:
    """Tests for verify_password_reset_code lookup and validation."""

    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_returns_none_when_user_not_found(self, mock_find):
        """Returns None when identifier resolves to no user."""
        from accounts.services._password_reset import verify_password_reset_code

        mock_find.return_value = None

        result = verify_password_reset_code("unknown@example.com", "RESET-XYZ")

        assert result is None

    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_returns_none_when_no_matching_code(self, mock_find, mock_code_model, mock_hash):
        """Returns None when no matching code exists."""
        from accounts.services._password_reset import verify_password_reset_code

        mock_find.return_value = Mock()
        mock_hash.return_value = "hashed"
        mock_code_model.objects.select_related.return_value.filter.return_value.first.return_value = None

        result = verify_password_reset_code("user@example.com", "RESET-BAD")

        assert result is None

    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_returns_none_and_expires_when_code_expired(
        self, mock_find, mock_code_model, mock_hash, mock_tz
    ):
        """Returns None and marks request as EXPIRED when code is past expiry."""
        from accounts.services._password_reset import verify_password_reset_code

        mock_find.return_value = Mock()
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now - timedelta(minutes=1)
        code.request = Mock()
        mock_code_model.objects.select_related.return_value.filter.return_value.first.return_value = code

        result = verify_password_reset_code("user@example.com", "RESET-EXPIRED")

        assert result is None
        code.request.save.assert_called_once_with(update_fields=["status", "reviewed_at"])

    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_returns_code_when_valid(self, mock_find, mock_code_model, mock_hash, mock_tz):
        """Returns the code object when code is valid and not expired."""
        from accounts.services._password_reset import verify_password_reset_code

        mock_find.return_value = Mock()
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now + timedelta(minutes=10)
        mock_code_model.objects.select_related.return_value.filter.return_value.first.return_value = code

        result = verify_password_reset_code("user@example.com", "RESET-GOOD")

        assert result is code


# ---------------------------------------------------------------------------
# complete_password_reset
# ---------------------------------------------------------------------------


class TestCompletePasswordReset(_NoopAtomicMixin):
    """Tests for complete_password_reset atomic function."""

    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_raises_when_user_not_found(self, mock_find):
        """Raises PermissionError when identifier resolves to no user."""
        from accounts.services._password_reset import complete_password_reset

        mock_find.return_value = None

        with pytest.raises(PermissionError, match="Invalid reset code"):
            complete_password_reset("unknown", "RESET-X", "NewPass123!")

    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_raises_when_no_matching_code(self, mock_find, mock_code_model, mock_hash):
        """Raises PermissionError when no matching code found."""
        from accounts.services._password_reset import complete_password_reset

        mock_find.return_value = Mock()
        mock_hash.return_value = "hashed"
        mock_code_model.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = None

        with pytest.raises(PermissionError, match="Invalid reset code"):
            complete_password_reset("user", "RESET-BAD", "NewPass123!")

    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_raises_when_code_expired(self, mock_find, mock_code_model, mock_hash, mock_tz):
        """Raises PermissionError and marks request EXPIRED when code is past expiry."""
        from accounts.services._password_reset import complete_password_reset

        mock_find.return_value = Mock()
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now - timedelta(minutes=1)
        code.request = Mock()
        mock_code_model.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = code

        with pytest.raises(PermissionError, match="expired"):
            complete_password_reset("user", "RESET-EXPIRED", "NewPass123!")

        code.request.save.assert_called_once_with(update_fields=["status", "reviewed_at"])

    @patch("accounts.services._password_reset.password_strength_errors")
    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_raises_when_password_too_weak(
        self, mock_find, mock_code_model, mock_hash, mock_tz, mock_strength
    ):
        """Raises ValueError when new password fails strength check."""
        from accounts.services._password_reset import complete_password_reset

        user = Mock()
        mock_find.return_value = user
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now + timedelta(minutes=10)
        mock_code_model.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = code

        mock_strength.return_value = ["Password too short"]

        with pytest.raises(ValueError, match="Password too short"):
            complete_password_reset("user", "RESET-CODE", "weak")

    @patch("accounts.services._password_reset.password_strength_errors")
    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_raises_when_same_as_current_password(
        self, mock_find, mock_code_model, mock_hash, mock_tz, mock_strength
    ):
        """Raises ValueError when new password matches current."""
        from accounts.services._password_reset import complete_password_reset

        user = Mock()
        user.check_password.return_value = True
        mock_find.return_value = user
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now + timedelta(minutes=10)
        mock_code_model.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = code

        mock_strength.return_value = []

        with pytest.raises(ValueError, match="different from current password"):
            complete_password_reset("user", "RESET-CODE", "SamePass123!")

    @patch("accounts.services._password_reset.password_strength_errors")
    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset._hash_secret_token")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.find_user_by_identifier")
    def test_successful_reset_updates_password_and_marks_code_used(
        self, mock_find, mock_code_model, mock_hash, mock_tz, mock_strength
    ):
        """Successful reset sets new password, saves user, and marks code used."""
        from accounts.services._password_reset import complete_password_reset

        user = Mock()
        user.check_password.return_value = False
        mock_find.return_value = user
        mock_hash.return_value = "hashed"

        now = timezone.now()
        mock_tz.now.return_value = now

        code = Mock()
        code.expires_at = now + timedelta(minutes=10)
        mock_code_model.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = code

        mock_strength.return_value = []

        result = complete_password_reset("user", "RESET-CODE", "BrandNewPass123!")

        assert result is user
        user.set_password.assert_called_once_with("BrandNewPass123!")
        user.save.assert_called_once_with(update_fields=["password"])
        code.save.assert_called_once_with(update_fields=["used_at"])


# ---------------------------------------------------------------------------
# cleanup_temporary_reset_codes
# ---------------------------------------------------------------------------


class TestCleanupTemporaryResetCodes(_NoopAtomicMixin):
    """Tests for cleanup_temporary_reset_codes batch operation."""

    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.PasswordResetRequest")
    def test_expires_requests_and_deletes_codes(self, mock_pr_model, mock_code_model):
        """Expires approved requests with expired codes and deletes code artifacts."""
        from accounts.services._password_reset import cleanup_temporary_reset_codes

        now = timezone.now()
        mock_code_model.objects.filter.return_value.values_list.return_value = [10, 20]
        mock_code_model.objects.filter.return_value.delete.return_value = (3, {})

        result = cleanup_temporary_reset_codes(now=now)

        assert result["codesDeleted"] == 3
        assert result["requestsExpired"] == 2
        mock_pr_model.objects.filter.assert_called_once_with(id__in=[10, 20])

    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.PasswordResetRequest")
    def test_skips_request_update_when_no_expired_codes(self, mock_pr_model, mock_code_model):
        """Does not update requests when no expired codes found."""
        from accounts.services._password_reset import cleanup_temporary_reset_codes

        now = timezone.now()
        mock_code_model.objects.filter.return_value.values_list.return_value = []
        mock_code_model.objects.filter.return_value.delete.return_value = (0, {})

        result = cleanup_temporary_reset_codes(now=now)

        assert result["codesDeleted"] == 0
        assert result["requestsExpired"] == 0
        mock_pr_model.objects.filter.assert_not_called()

    @patch("accounts.services._password_reset.timezone")
    @patch("accounts.services._password_reset.PasswordResetCode")
    @patch("accounts.services._password_reset.PasswordResetRequest")
    def test_uses_current_time_when_now_not_provided(self, mock_pr_model, mock_code_model, mock_tz):
        """Uses timezone.now() when no explicit time is provided."""
        from accounts.services._password_reset import cleanup_temporary_reset_codes

        now = timezone.now()
        mock_tz.now.return_value = now
        mock_code_model.objects.filter.return_value.values_list.return_value = []
        mock_code_model.objects.filter.return_value.delete.return_value = (0, {})

        cleanup_temporary_reset_codes()

        mock_tz.now.assert_called_once()
