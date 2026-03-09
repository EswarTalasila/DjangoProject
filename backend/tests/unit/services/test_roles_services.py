"""Unit tests for role management service helpers (_roles.py).

These are TRUE unit tests that mock all ORM/database calls and test
the service logic in isolation. They cover _get_role_value,
set_single_role, ensure_profiles_for_role, can_create_user,
teacher_owns_student, can_edit_user, can_delete_user, and
create_user_from_payload including line 283 (email required for
non-student).
"""

from __future__ import annotations

from unittest.mock import Mock, PropertyMock, patch

import pytest

from accounts.services._roles import (
    _get_role_value,
    can_create_user,
    can_delete_user,
    can_edit_user,
    create_user_from_payload,
    ensure_profiles_for_role,
    set_single_role,
    teacher_owns_student,
)

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# _get_role_value
# ---------------------------------------------------------------------------


class TestGetRoleValue:
    """Tests for _get_role_value role normalization."""

    def test_none_defaults_to_student(self):
        """None input returns STUDENT as default."""
        assert _get_role_value(None) == "STUDENT"

    def test_empty_string_defaults_to_student(self):
        """Empty string returns STUDENT as default."""
        assert _get_role_value("") == "STUDENT"

    def test_strips_role_prefix(self):
        """Legacy ROLE_ prefix is stripped correctly."""
        assert _get_role_value("ROLE_TEACHER") == "TEACHER"

    def test_strips_role_prefix_researcher(self):
        """ROLE_RESEARCHER prefix returns RESEARCHER."""
        assert _get_role_value("ROLE_RESEARCHER") == "RESEARCHER"

    def test_strips_role_prefix_student(self):
        """ROLE_STUDENT prefix returns STUDENT."""
        assert _get_role_value("ROLE_STUDENT") == "STUDENT"

    def test_direct_role_values(self):
        """Direct Role enum values are accepted."""
        assert _get_role_value("RESEARCHER") == "RESEARCHER"
        assert _get_role_value("TEACHER") == "TEACHER"
        assert _get_role_value("STUDENT") == "STUDENT"

    def test_invalid_role_raises_value_error(self):
        """Unknown role string raises ValueError with valid roles listed."""
        with pytest.raises(ValueError, match="Invalid role"):
            _get_role_value("SUPERADMIN")

    def test_invalid_role_after_prefix_strip_raises_value_error(self):
        """Invalid role after stripping ROLE_ prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            _get_role_value("ROLE_ADMIN")

    def test_only_first_role_prefix_stripped(self):
        """Only the first ROLE_ prefix is stripped."""
        with pytest.raises(ValueError, match="Invalid role"):
            _get_role_value("ROLE_ROLE_TEACHER")


# ---------------------------------------------------------------------------
# set_single_role
# ---------------------------------------------------------------------------


class TestSetSingleRole:
    """Tests for set_single_role role replacement logic."""

    @patch("accounts.services._roles.UserRole.objects")
    def test_deletes_existing_roles_and_creates_new(self, mock_userrole):
        """Existing roles are deleted before the new one is created."""
        user = Mock()

        set_single_role(user, "TEACHER")

        mock_userrole.filter.assert_called_once_with(user=user)
        mock_userrole.filter.return_value.delete.assert_called_once()
        mock_userrole.create.assert_called_once_with(user=user, role="TEACHER")

    @patch("accounts.services._roles.UserRole.objects")
    def test_normalizes_role_before_setting(self, mock_userrole):
        """Role string is normalized (e.g., ROLE_ prefix stripped)."""
        user = Mock()

        set_single_role(user, "ROLE_RESEARCHER")

        mock_userrole.create.assert_called_once_with(user=user, role="RESEARCHER")


# ---------------------------------------------------------------------------
# ensure_profiles_for_role
# ---------------------------------------------------------------------------


class TestEnsureProfilesForRole:
    """Tests for ensure_profiles_for_role profile provisioning."""

    @patch("accounts.services._roles.ResearcherProfile.objects")
    def test_creates_researcher_profile_if_missing(self, mock_rp):
        """Creates ResearcherProfile when user has RESEARCHER role and no profile."""
        mock_rp.filter.return_value.exists.return_value = False
        user = Mock()

        ensure_profiles_for_role(user, "RESEARCHER")

        mock_rp.create.assert_called_once_with(user=user)

    @patch("accounts.services._roles.ResearcherProfile.objects")
    def test_skips_researcher_profile_if_exists(self, mock_rp):
        """Does not create ResearcherProfile when one already exists."""
        mock_rp.filter.return_value.exists.return_value = True
        user = Mock()

        ensure_profiles_for_role(user, "RESEARCHER")

        mock_rp.create.assert_not_called()

    @patch("accounts.services._roles.TeacherProfile.objects")
    def test_creates_teacher_profile_if_missing(self, mock_tp):
        """Creates TeacherProfile when user has TEACHER role and no profile."""
        mock_tp.filter.return_value.exists.return_value = False
        user = Mock()

        ensure_profiles_for_role(user, "TEACHER")

        mock_tp.create.assert_called_once_with(user=user)

    @patch("accounts.services._roles.TeacherProfile.objects")
    def test_skips_teacher_profile_if_exists(self, mock_tp):
        """Does not create TeacherProfile when one already exists."""
        mock_tp.filter.return_value.exists.return_value = True
        user = Mock()

        ensure_profiles_for_role(user, "TEACHER")

        mock_tp.create.assert_not_called()

    @patch("accounts.services._roles.StudentProfile.objects")
    def test_creates_student_profile_with_creator(self, mock_sp):
        """Creates StudentProfile with creator reference when provided."""
        mock_sp.filter.return_value.exists.return_value = False
        user = Mock()
        creator = Mock()

        ensure_profiles_for_role(user, "STUDENT", creator=creator)

        mock_sp.create.assert_called_once_with(user=user, created_by=creator, consent=False)

    @patch("accounts.services._roles.StudentProfile.objects")
    def test_creates_student_profile_self_reference_when_no_creator(self, mock_sp):
        """Uses user as created_by when no creator is specified."""
        mock_sp.filter.return_value.exists.return_value = False
        user = Mock()

        ensure_profiles_for_role(user, "STUDENT")

        mock_sp.create.assert_called_once_with(user=user, created_by=user, consent=False)

    @patch("accounts.services._roles.StudentProfile.objects")
    def test_skips_student_profile_if_exists(self, mock_sp):
        """Does not create StudentProfile when one already exists."""
        mock_sp.filter.return_value.exists.return_value = True
        user = Mock()

        ensure_profiles_for_role(user, "STUDENT")

        mock_sp.create.assert_not_called()


# ---------------------------------------------------------------------------
# can_create_user
# ---------------------------------------------------------------------------


class TestCanCreateUser:
    """Tests for can_create_user permission matrix."""

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_create_researcher(self, mock_role):
        """Admin can create researcher accounts."""
        user = Mock()
        user.is_staff = True

        assert can_create_user(user, "RESEARCHER") is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_create_teacher(self, mock_role):
        """Admin can create teacher accounts."""
        user = Mock()
        user.is_staff = True

        assert can_create_user(user, "TEACHER") is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_cannot_create_student(self, mock_role):
        """Admin cannot create student accounts directly."""
        user = Mock()
        user.is_staff = True

        assert can_create_user(user, "STUDENT") is False

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_create_teacher_sudo(self, mock_role, mock_sudo):
        """Researcher with CREATE_TEACHER sudo can create teachers."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = True

        assert can_create_user(user, "TEACHER") is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_create_student_sudo(self, mock_role, mock_sudo):
        """Researcher with CREATE_STUDENT sudo can create students."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.side_effect = lambda u, p: p == "CREATE_STUDENT"

        assert can_create_user(user, "STUDENT") is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_without_sudo_cannot_create_teacher(self, mock_role, mock_sudo):
        """Researcher without sudo cannot create teachers."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = False

        assert can_create_user(user, "TEACHER") is False

    @patch("accounts.services._roles.primary_role")
    def test_teacher_can_create_student(self, mock_role):
        """Teacher can create student accounts."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "TEACHER"

        assert can_create_user(user, "STUDENT") is True

    @patch("accounts.services._roles.primary_role")
    def test_teacher_cannot_create_teacher(self, mock_role):
        """Teacher cannot create teacher accounts."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "TEACHER"

        assert can_create_user(user, "TEACHER") is False

    @patch("accounts.services._roles.primary_role")
    def test_student_cannot_create_any(self, mock_role):
        """Student cannot create any user accounts."""
        user = Mock()
        user.is_staff = False
        mock_role.return_value = "STUDENT"

        assert can_create_user(user, "STUDENT") is False
        assert can_create_user(user, "TEACHER") is False
        assert can_create_user(user, "RESEARCHER") is False


# ---------------------------------------------------------------------------
# teacher_owns_student
# ---------------------------------------------------------------------------


class TestTeacherOwnsStudent:
    """Tests for teacher_owns_student ownership check."""

    @patch("accounts.services._roles.primary_role")
    def test_non_teacher_returns_false(self, mock_role):
        """Non-teacher requesting user returns False."""
        mock_role.return_value = "RESEARCHER"

        assert teacher_owns_student(Mock(), Mock()) is False

    @patch("accounts.services._roles.primary_role")
    def test_target_non_student_returns_false(self, mock_role):
        """Teacher checking non-student target returns False."""
        mock_role.side_effect = ["TEACHER", "TEACHER"]

        assert teacher_owns_student(Mock(), Mock()) is False

    @patch("accounts.services._roles.primary_role")
    def test_missing_student_profile_returns_false(self, mock_role):
        """Student user without StudentProfile returns False."""
        from accounts.models import StudentProfile

        mock_role.side_effect = ["TEACHER", "STUDENT"]
        student = Mock()
        type(student).student_profile = PropertyMock(
            side_effect=StudentProfile.DoesNotExist
        )

        assert teacher_owns_student(Mock(), student) is False

    @patch("accounts.services._roles.Enrollment.objects")
    @patch("accounts.services._roles.primary_role")
    def test_enrolled_student_returns_true(self, mock_role, mock_enrollment):
        """Student enrolled in teacher's course returns True."""
        mock_role.side_effect = ["TEACHER", "STUDENT"]
        student = Mock()
        student.student_profile = Mock()
        teacher = Mock()
        mock_enrollment.filter.return_value.exists.return_value = True

        assert teacher_owns_student(teacher, student) is True

    @patch("accounts.services._roles.Enrollment.objects")
    @patch("accounts.services._roles.primary_role")
    def test_unenrolled_student_returns_false(self, mock_role, mock_enrollment):
        """Student not enrolled in teacher's course returns False."""
        mock_role.side_effect = ["TEACHER", "STUDENT"]
        student = Mock()
        student.student_profile = Mock()
        teacher = Mock()
        mock_enrollment.filter.return_value.exists.return_value = False

        assert teacher_owns_student(teacher, student) is False


# ---------------------------------------------------------------------------
# can_edit_user
# ---------------------------------------------------------------------------


class TestCanEditUser:
    """Tests for can_edit_user permission checks."""

    def test_staff_target_always_returns_false(self):
        """Staff/admin accounts cannot be edited through role flows."""
        target = Mock()
        target.is_staff = True
        admin = Mock()
        admin.is_staff = True

        assert can_edit_user(admin, target, "RESEARCHER") is False

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_edit_researcher(self, mock_role):
        """Admin can edit researcher targets."""
        target = Mock()
        target.is_staff = False
        admin = Mock()
        admin.is_staff = True

        assert can_edit_user(admin, target, "RESEARCHER") is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_edit_teacher(self, mock_role):
        """Admin can edit teacher targets."""
        target = Mock()
        target.is_staff = False
        admin = Mock()
        admin.is_staff = True

        assert can_edit_user(admin, target, "TEACHER") is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_cannot_edit_to_student_role(self, mock_role):
        """Admin cannot set a user to student role via edit."""
        target = Mock()
        target.is_staff = False
        admin = Mock()
        admin.is_staff = True

        assert can_edit_user(admin, target, "STUDENT") is False

    def test_invalid_requested_role_returns_false(self):
        """Invalid role string returns False without raising."""
        target = Mock()
        target.is_staff = False
        admin = Mock()
        admin.is_staff = True

        assert can_edit_user(admin, target, "INVALID_ROLE") is False

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_edit_sudo_can_edit_teacher(self, mock_role, mock_sudo):
        """Researcher with EDIT_USER sudo can edit teacher targets."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = True

        assert can_edit_user(request_user, target, "TEACHER") is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_edit_sudo_can_edit_student(self, mock_role, mock_sudo):
        """Researcher with EDIT_USER sudo can edit student targets."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = True

        assert can_edit_user(request_user, target, "STUDENT") is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_without_sudo_cannot_edit(self, mock_role, mock_sudo):
        """Researcher without EDIT_USER sudo cannot edit anyone."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "RESEARCHER"
        mock_sudo.return_value = False

        assert can_edit_user(request_user, target, "TEACHER") is False

    @patch("accounts.services._roles.teacher_owns_student")
    @patch("accounts.services._roles.primary_role")
    def test_teacher_can_edit_owned_student(self, mock_role, mock_owns):
        """Teacher can edit students they own."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "TEACHER"
        mock_owns.return_value = True

        assert can_edit_user(request_user, target, "STUDENT") is True

    @patch("accounts.services._roles.teacher_owns_student")
    @patch("accounts.services._roles.primary_role")
    def test_teacher_cannot_edit_unowned_student(self, mock_role, mock_owns):
        """Teacher cannot edit students they do not own."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "TEACHER"
        mock_owns.return_value = False

        assert can_edit_user(request_user, target, "STUDENT") is False

    @patch("accounts.services._roles.primary_role")
    def test_teacher_cannot_edit_non_student_role(self, mock_role):
        """Teacher cannot edit users to non-student roles."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "TEACHER"

        assert can_edit_user(request_user, target, "TEACHER") is False

    @patch("accounts.services._roles.primary_role")
    def test_student_cannot_edit_anyone(self, mock_role):
        """Student users cannot edit anyone."""
        target = Mock()
        target.is_staff = False
        request_user = Mock()
        request_user.is_staff = False
        mock_role.return_value = "STUDENT"

        assert can_edit_user(request_user, target, "STUDENT") is False


# ---------------------------------------------------------------------------
# can_delete_user
# ---------------------------------------------------------------------------


class TestCanDeleteUser:
    """Tests for can_delete_user permission checks."""

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_delete_researcher(self, mock_role):
        """Admin can delete researcher targets."""
        mock_role.return_value = "RESEARCHER"
        request_user = Mock()
        request_user.is_staff = True

        assert can_delete_user(request_user, Mock()) is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_can_delete_teacher(self, mock_role):
        """Admin can delete teacher targets."""
        mock_role.return_value = "TEACHER"
        request_user = Mock()
        request_user.is_staff = True

        assert can_delete_user(request_user, Mock()) is True

    @patch("accounts.services._roles.primary_role")
    def test_admin_cannot_delete_student(self, mock_role):
        """Admin cannot delete student targets."""
        mock_role.return_value = "STUDENT"
        request_user = Mock()
        request_user.is_staff = True

        assert can_delete_user(request_user, Mock()) is False

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_delete_sudo_can_delete_teacher(self, mock_role, mock_sudo):
        """Researcher with DELETE_USER sudo can delete teachers."""
        mock_role.side_effect = ["RESEARCHER", "TEACHER"]
        request_user = Mock()
        request_user.is_staff = False
        mock_sudo.return_value = True

        assert can_delete_user(request_user, Mock()) is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_with_delete_sudo_can_delete_student(self, mock_role, mock_sudo):
        """Researcher with DELETE_USER sudo can delete students."""
        mock_role.side_effect = ["RESEARCHER", "STUDENT"]
        request_user = Mock()
        request_user.is_staff = False
        mock_sudo.return_value = True

        assert can_delete_user(request_user, Mock()) is True

    @patch("accounts.services._roles.has_sudo_permission")
    @patch("accounts.services._roles.primary_role")
    def test_researcher_without_sudo_cannot_delete(self, mock_role, mock_sudo):
        """Researcher without DELETE_USER sudo cannot delete."""
        mock_role.side_effect = ["RESEARCHER", "TEACHER"]
        request_user = Mock()
        request_user.is_staff = False
        mock_sudo.return_value = False

        assert can_delete_user(request_user, Mock()) is False

    @patch("accounts.services._roles.teacher_owns_student")
    @patch("accounts.services._roles.primary_role")
    def test_teacher_can_delete_owned_student(self, mock_role, mock_owns):
        """Teacher can delete students they own."""
        mock_role.side_effect = ["TEACHER", "STUDENT"]
        request_user = Mock()
        request_user.is_staff = False
        mock_owns.return_value = True

        assert can_delete_user(request_user, Mock()) is True

    @patch("accounts.services._roles.teacher_owns_student")
    @patch("accounts.services._roles.primary_role")
    def test_teacher_cannot_delete_unowned_student(self, mock_role, mock_owns):
        """Teacher cannot delete students they do not own."""
        mock_role.side_effect = ["TEACHER", "STUDENT"]
        request_user = Mock()
        request_user.is_staff = False
        mock_owns.return_value = False

        assert can_delete_user(request_user, Mock()) is False

    @patch("accounts.services._roles.primary_role")
    def test_student_cannot_delete_anyone(self, mock_role):
        """Student users cannot delete anyone."""
        mock_role.side_effect = ["STUDENT", "TEACHER"]
        request_user = Mock()
        request_user.is_staff = False

        assert can_delete_user(request_user, Mock()) is False


# ---------------------------------------------------------------------------
# create_user_from_payload (line 283: email required for non-student)
# ---------------------------------------------------------------------------


class TestCreateUserFromPayload:
    """Tests for create_user_from_payload covering line 283."""

    @pytest.fixture(autouse=True)
    def _mock_db_connection(self):
        """Mock database connection so transaction.atomic works without a real DB."""
        with patch("django.db.connection.ensure_connection"), \
             patch("django.db.connection.cursor"):
            yield

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_non_student_without_email_raises_value_error(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """Non-student user creation without email raises ValueError (line 283)."""
        mock_normalize.return_value = "teacher1"

        with pytest.raises(ValueError, match="email is required for non-student"):
            create_user_from_payload(
                {"username": "teacher1", "name": "Teacher", "password": "Pass123!"},
                role_override="TEACHER",
            )

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_student_without_email_succeeds(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """Student user creation without email succeeds."""
        mock_normalize.return_value = "student1"
        user = Mock()
        mock_objects.create_user.return_value = user

        result = create_user_from_payload(
            {"username": "student1", "name": "Student", "password": "Pass123!"},
            role_override="STUDENT",
        )

        assert result is user

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_non_student_with_email_succeeds(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """Non-student creation with email succeeds."""
        mock_normalize.side_effect = lambda x: x.strip().lower() if x else ""
        user = Mock()
        mock_objects.create_user.return_value = user

        result = create_user_from_payload(
            {
                "username": "teacher1",
                "name": "Teacher",
                "password": "Pass123!",
                "email": "teacher@example.com",
            },
            role_override="TEACHER",
        )

        assert result is user
        mock_set_role.assert_called_once_with(user, "TEACHER")
        mock_ensure.assert_called_once()

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_role_override_takes_precedence(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """role_override parameter overrides payload role value."""
        mock_normalize.side_effect = lambda x: x.strip().lower() if x else ""
        user = Mock()
        mock_objects.create_user.return_value = user

        create_user_from_payload(
            {
                "username": "user1",
                "name": "User",
                "password": "Pass!",
                "role": "RESEARCHER",
                "email": "r@example.com",
            },
            role_override="TEACHER",
        )

        mock_set_role.assert_called_once_with(user, "TEACHER")

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_creator_passed_to_ensure_profiles(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """Creator is forwarded to ensure_profiles_for_role."""
        mock_normalize.return_value = "student1"
        user = Mock()
        creator = Mock()
        mock_objects.create_user.return_value = user

        create_user_from_payload(
            {"username": "student1", "name": "Student", "password": "Pass123!"},
            role_override="STUDENT",
            creator=creator,
        )

        mock_ensure.assert_called_once_with(user, "STUDENT", creator=creator)

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_defaults_to_student_when_no_role_specified(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """When no role_override or payload role, defaults to STUDENT."""
        mock_normalize.return_value = "newuser"
        user = Mock()
        mock_objects.create_user.return_value = user

        create_user_from_payload(
            {"username": "newuser", "name": "New User", "password": "Pass123!"}
        )

        mock_set_role.assert_called_once_with(user, "STUDENT")

    @patch("accounts.services._roles.ensure_profiles_for_role")
    @patch("accounts.services._roles.set_single_role")
    @patch("accounts.services._roles.User.objects")
    @patch("accounts.services._roles.normalize_username_identifier")
    def test_password_none_is_passed_through(
        self, mock_normalize, mock_objects, mock_set_role, mock_ensure
    ):
        """None password (for OAuth users) is passed through to create_user."""
        mock_normalize.return_value = "oauthuser"
        user = Mock()
        mock_objects.create_user.return_value = user

        create_user_from_payload(
            {"username": "oauthuser", "name": "OAuth User", "password": None}
        )

        create_call_kwargs = mock_objects.create_user.call_args
        assert create_call_kwargs.kwargs["password"] is None
