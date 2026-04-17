"""Unit tests for accounts serializers.

Tests cover field validation, custom validate methods, input normalization,
and output shape for every serializer in accounts.serializers.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from accounts.models import Role
from accounts.serializers import (
    GoogleOAuthLoginSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetCodeCompleteSerializer,
    PasswordResetCodeIssueSerializer,
    PasswordResetCodeVerifySerializer,
    RefreshTokenSerializer,
    RegistrationCodeCreateSerializer,
    RegistrationCodeUpdateSerializer,
    RegistrationCodeValidateInputSerializer,
    RegistrationOAuthSerializer,
    RoleChoiceField,
    StrictFieldsSerializer,
    StudentInviteRegisterSerializer,
    StudentJoinCourseSerializer,
    UserInputSerializer,
    UserOutputSerializer,
    UserRoleSerializer,
)

# ---------------------------------------------------------------------------
# RoleChoiceField
# ---------------------------------------------------------------------------


class TestRoleChoiceField:
    """Tests for the RoleChoiceField custom ChoiceField."""

    def test_normalizes_role_prefix(self):
        """Strips ROLE_ prefix and returns plain role string."""
        field = RoleChoiceField(choices=Role.choices)
        assert field.to_internal_value("ROLE_TEACHER") == "TEACHER"

    def test_normalizes_role_prefix_researcher(self):
        """Strips ROLE_ prefix for RESEARCHER role."""
        field = RoleChoiceField(choices=Role.choices)
        assert field.to_internal_value("ROLE_RESEARCHER") == "RESEARCHER"

    def test_normalizes_role_prefix_student(self):
        """Strips ROLE_ prefix for STUDENT role."""
        field = RoleChoiceField(choices=Role.choices)
        assert field.to_internal_value("ROLE_STUDENT") == "STUDENT"

    def test_plain_role_passes_through(self):
        """Plain role string is accepted unchanged."""
        field = RoleChoiceField(choices=Role.choices)
        assert field.to_internal_value("TEACHER") == "TEACHER"

    def test_invalid_role_rejected(self):
        """Non-existent role value raises validation error."""
        field = RoleChoiceField(choices=Role.choices)
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            field.to_internal_value("ROLE_INVALID")

    def test_non_string_input_handled(self):
        """Non-string input falls through to parent validation."""
        field = RoleChoiceField(choices=Role.choices)
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            field.to_internal_value(123)

    def test_only_first_role_prefix_stripped(self):
        """Only the first ROLE_ prefix occurrence is stripped."""
        field = RoleChoiceField(choices=Role.choices)
        from rest_framework.exceptions import ValidationError

        # "ROLE_ROLE_TEACHER" -> "ROLE_TEACHER" after stripping first ROLE_,
        # which is not a valid role value.
        with pytest.raises(ValidationError):
            field.to_internal_value("ROLE_ROLE_TEACHER")


# ---------------------------------------------------------------------------
# StrictFieldsSerializer
# ---------------------------------------------------------------------------


class TestStrictFieldsSerializer:
    """Tests for the StrictFieldsSerializer base class."""

    def test_rejects_unknown_fields(self):
        """Unknown fields cause validation error listing each unknown key."""

        class SampleSerializer(StrictFieldsSerializer):
            name = __import__("rest_framework").serializers.CharField()

        ser = SampleSerializer(data={"name": "ok", "unknown_key": "bad"})
        assert ser.is_valid() is False
        assert "unknown_key" in ser.errors

    def test_accepts_declared_fields_only(self):
        """Declared fields pass validation without error."""

        class SampleSerializer(StrictFieldsSerializer):
            name = __import__("rest_framework").serializers.CharField()

        ser = SampleSerializer(data={"name": "valid"})
        assert ser.is_valid() is True

    def test_multiple_unknown_fields_listed(self):
        """Each unknown field is reported in the error response."""

        class SampleSerializer(StrictFieldsSerializer):
            name = __import__("rest_framework").serializers.CharField()

        ser = SampleSerializer(data={"name": "ok", "foo": 1, "bar": 2})
        assert ser.is_valid() is False
        assert "bar" in ser.errors
        assert "foo" in ser.errors


# ---------------------------------------------------------------------------
# UserInputSerializer
# ---------------------------------------------------------------------------


class TestUserInputSerializer:
    """Tests for UserInputSerializer field validation."""

    def test_all_fields_optional(self):
        """Empty payload is valid since all fields are optional."""
        ser = UserInputSerializer(data={})
        assert ser.is_valid() is True

    def test_valid_complete_payload(self):
        """Full valid payload passes validation."""
        data = {
            "id": 1,
            "name": "Test User",
            "username": "testuser",
            "email": "test@example.com",
            "password": "Secret123!",
            "role": "TEACHER",
        }
        ser = UserInputSerializer(data=data)
        assert ser.is_valid() is True
        assert ser.validated_data["role"] == "TEACHER"

    def test_name_blank_rejected(self):
        """Blank name string is rejected."""
        ser = UserInputSerializer(data={"name": ""})
        assert ser.is_valid() is False
        assert "name" in ser.errors

    def test_name_max_length(self):
        """Name exceeding 255 chars is rejected."""
        ser = UserInputSerializer(data={"name": "x" * 256})
        assert ser.is_valid() is False
        assert "name" in ser.errors

    def test_username_blank_rejected(self):
        """Blank username string is rejected."""
        ser = UserInputSerializer(data={"username": ""})
        assert ser.is_valid() is False
        assert "username" in ser.errors

    def test_username_max_length(self):
        """Username exceeding 320 chars is rejected."""
        ser = UserInputSerializer(data={"username": "u" * 321})
        assert ser.is_valid() is False
        assert "username" in ser.errors

    def test_email_invalid_format(self):
        """Non-email string is rejected."""
        ser = UserInputSerializer(data={"email": "not-an-email"})
        assert ser.is_valid() is False
        assert "email" in ser.errors

    def test_email_null_accepted(self):
        """Null email is accepted (allow_null=True)."""
        ser = UserInputSerializer(data={"email": None})
        assert ser.is_valid() is True
        assert ser.validated_data["email"] is None

    def test_password_blank_accepted(self):
        """Blank password is accepted (allow_blank=True)."""
        ser = UserInputSerializer(data={"password": ""})
        assert ser.is_valid() is True

    def test_password_null_accepted(self):
        """Null password is accepted (allow_null=True)."""
        ser = UserInputSerializer(data={"password": None})
        assert ser.is_valid() is True

    def test_password_whitespace_preserved(self):
        """Whitespace in password is preserved (trim_whitespace=False)."""
        ser = UserInputSerializer(data={"password": "  secret  "})
        assert ser.is_valid() is True
        assert ser.validated_data["password"] == "  secret  "

    def test_password_max_length(self):
        """Password exceeding 255 chars is rejected."""
        ser = UserInputSerializer(data={"password": "p" * 256})
        assert ser.is_valid() is False
        assert "password" in ser.errors

    def test_role_legacy_prefix_accepted(self):
        """Legacy ROLE_ prefixed role is normalized to plain role."""
        ser = UserInputSerializer(data={"role": "ROLE_STUDENT"})
        assert ser.is_valid() is True
        assert ser.validated_data["role"] == "STUDENT"

    def test_role_invalid_rejected(self):
        """Invalid role string is rejected."""
        ser = UserInputSerializer(data={"role": "SUPERADMIN"})
        assert ser.is_valid() is False
        assert "role" in ser.errors

    def test_id_non_integer_rejected(self):
        """Non-integer id is rejected."""
        ser = UserInputSerializer(data={"id": "abc"})
        assert ser.is_valid() is False
        assert "id" in ser.errors


# ---------------------------------------------------------------------------
# UserOutputSerializer
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUserOutputSerializer:
    """Tests for UserOutputSerializer output shape."""

    def _mock_user(self, roles=None, is_staff=False):
        """Build a mock user with a roles queryset."""
        user = MagicMock()
        user.id = 1
        user.name = "Test User"
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_staff = is_staff
        user.is_authenticated = True
        user._cached_role_set = None
        qs = MagicMock()
        if roles:
            qs.all.return_value = [SimpleNamespace(role=r) for r in roles]
            qs.first.return_value = SimpleNamespace(role=roles[0])
            qs.values_list.return_value = list(roles)
        else:
            qs.all.return_value = []
            qs.first.return_value = None
            qs.values_list.return_value = []
        user.roles = qs
        return user

    def test_output_fields(self):
        """Serialized output contains exactly id, name, username, email, role."""
        user = self._mock_user(roles=[Role.TEACHER])
        data = UserOutputSerializer(user).data
        assert set(data.keys()) == {"id", "name", "username", "email", "role"}

    def test_role_from_assigned_role(self):
        """Role field reflects the assigned UserRole."""
        user = self._mock_user(roles=[Role.RESEARCHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "RESEARCHER"

    def test_role_fallback_to_student(self):
        """Role falls back to STUDENT when no roles assigned."""
        user = self._mock_user(roles=[])
        data = UserOutputSerializer(user).data
        assert data["role"] == "STUDENT"

    def test_highest_priority_role_used_when_multiple(self):
        """When multiple roles exist, the highest-priority role is returned."""
        user = self._mock_user(roles=[Role.TEACHER, Role.RESEARCHER])
        data = UserOutputSerializer(user).data
        assert data["role"] == "RESEARCHER"


# ---------------------------------------------------------------------------
# RegistrationCodeValidateInputSerializer
# ---------------------------------------------------------------------------


class TestRegistrationCodeValidateInputSerializer:
    """Tests for RegistrationCodeValidateInputSerializer."""

    def test_valid_code(self):
        """Valid code string passes validation."""
        ser = RegistrationCodeValidateInputSerializer(data={"code": "ABC123"})
        assert ser.is_valid() is True
        assert ser.validated_data["code"] == "ABC123"

    def test_code_required(self):
        """Missing code field fails validation."""
        ser = RegistrationCodeValidateInputSerializer(data={})
        assert ser.is_valid() is False
        assert "code" in ser.errors

    def test_code_max_length(self):
        """Code exceeding 64 chars is rejected."""
        ser = RegistrationCodeValidateInputSerializer(data={"code": "x" * 65})
        assert ser.is_valid() is False
        assert "code" in ser.errors


# ---------------------------------------------------------------------------
# StudentInviteRegisterSerializer
# ---------------------------------------------------------------------------


class TestStudentInviteRegisterSerializer:
    """Tests for StudentInviteRegisterSerializer."""

    def _valid_payload(self, **overrides):
        base = {
            "code": "INVITE123",
            "firstName": "Alex",
            "lastName": "Torres",
            "password": "Secret123!",
            "confirmPassword": "Secret123!",
        }
        base.update(overrides)
        return base

    def test_valid_payload(self):
        """Complete valid payload passes validation."""
        ser = StudentInviteRegisterSerializer(data=self._valid_payload())
        assert ser.is_valid() is True

    def test_code_required(self):
        """Missing code fails validation."""
        data = self._valid_payload()
        del data["code"]
        ser = StudentInviteRegisterSerializer(data=data)
        assert ser.is_valid() is False
        assert "code" in ser.errors

    def test_first_name_required(self):
        """Missing firstName fails validation."""
        data = self._valid_payload()
        del data["firstName"]
        ser = StudentInviteRegisterSerializer(data=data)
        assert ser.is_valid() is False
        assert "firstName" in ser.errors

    def test_last_name_required(self):
        """Missing lastName fails validation."""
        data = self._valid_payload()
        del data["lastName"]
        ser = StudentInviteRegisterSerializer(data=data)
        assert ser.is_valid() is False
        assert "lastName" in ser.errors

    def test_password_required(self):
        """Missing password fails validation."""
        data = self._valid_payload()
        del data["password"]
        ser = StudentInviteRegisterSerializer(data=data)
        assert ser.is_valid() is False
        assert "password" in ser.errors

    def test_confirm_password_required(self):
        """Missing confirmPassword fails validation."""
        data = self._valid_payload()
        del data["confirmPassword"]
        ser = StudentInviteRegisterSerializer(data=data)
        assert ser.is_valid() is False
        assert "confirmPassword" in ser.errors

    def test_blank_first_name_rejected(self):
        """Empty firstName string is rejected."""
        ser = StudentInviteRegisterSerializer(data=self._valid_payload(firstName=""))
        assert ser.is_valid() is False
        assert "firstName" in ser.errors

    def test_password_whitespace_preserved(self):
        """Whitespace in password is preserved."""
        ser = StudentInviteRegisterSerializer(
            data=self._valid_payload(password="  pass  ", confirmPassword="  pass  ")
        )
        assert ser.is_valid() is True
        assert ser.validated_data["password"] == "  pass  "

    def test_email_optional(self):
        """Email field is optional."""
        ser = StudentInviteRegisterSerializer(data=self._valid_payload())
        assert ser.is_valid() is True
        assert "email" not in ser.validated_data

    def test_email_null_accepted(self):
        """Null email is accepted."""
        ser = StudentInviteRegisterSerializer(data=self._valid_payload(email=None))
        assert ser.is_valid() is True

    def test_email_invalid_rejected(self):
        """Invalid email format is rejected."""
        ser = StudentInviteRegisterSerializer(data=self._valid_payload(email="not-email"))
        assert ser.is_valid() is False
        assert "email" in ser.errors

    def test_rejects_unknown_fields(self):
        """Unknown fields are rejected (inherits StrictFieldsSerializer)."""
        ser = StudentInviteRegisterSerializer(
            data=self._valid_payload(extraField="bad")
        )
        assert ser.is_valid() is False
        assert "extraField" in ser.errors


# ---------------------------------------------------------------------------
# StudentJoinCourseSerializer
# ---------------------------------------------------------------------------


class TestStudentJoinCourseSerializer:
    """Tests for StudentJoinCourseSerializer."""

    def test_valid_code(self):
        """Valid code passes validation."""
        ser = StudentJoinCourseSerializer(data={"code": "JOIN123"})
        assert ser.is_valid() is True

    def test_code_required(self):
        """Missing code fails validation."""
        ser = StudentJoinCourseSerializer(data={})
        assert ser.is_valid() is False
        assert "code" in ser.errors

    def test_code_max_length(self):
        """Code exceeding 64 chars is rejected."""
        ser = StudentJoinCourseSerializer(data={"code": "c" * 65})
        assert ser.is_valid() is False


# ---------------------------------------------------------------------------
# RegistrationOAuthSerializer
# ---------------------------------------------------------------------------


class TestRegistrationOAuthSerializer:
    """Tests for RegistrationOAuthSerializer."""

    def _valid_payload(self, **overrides):
        base = {
            "code": "OAUTH-INVITE-CODE",
            "accessToken": "ya29.token",
            "firstName": "Morgan",
            "lastName": "Blake",
        }
        base.update(overrides)
        return base

    def test_valid_payload(self):
        """Complete valid payload passes validation."""
        ser = RegistrationOAuthSerializer(data=self._valid_payload())
        assert ser.is_valid() is True

    def test_code_required(self):
        """Missing code fails validation."""
        data = self._valid_payload()
        del data["code"]
        ser = RegistrationOAuthSerializer(data=data)
        assert ser.is_valid() is False
        assert "code" in ser.errors

    def test_access_token_required(self):
        """Missing accessToken fails validation."""
        data = self._valid_payload()
        del data["accessToken"]
        ser = RegistrationOAuthSerializer(data=data)
        assert ser.is_valid() is False
        assert "accessToken" in ser.errors

    def test_first_name_required(self):
        """Missing firstName fails validation."""
        data = self._valid_payload()
        del data["firstName"]
        ser = RegistrationOAuthSerializer(data=data)
        assert ser.is_valid() is False
        assert "firstName" in ser.errors

    def test_rejects_unknown_fields(self):
        """Unknown fields are rejected (inherits StrictFieldsSerializer)."""
        ser = RegistrationOAuthSerializer(data=self._valid_payload(extraField="bad"))
        assert ser.is_valid() is False
        assert "extraField" in ser.errors

    def test_blank_access_token_rejected(self):
        """Empty accessToken string is rejected."""
        ser = RegistrationOAuthSerializer(data=self._valid_payload(accessToken=""))
        assert ser.is_valid() is False
        assert "accessToken" in ser.errors


# ---------------------------------------------------------------------------
# RegistrationCodeCreateSerializer
# ---------------------------------------------------------------------------


class TestRegistrationCodeCreateSerializer:
    """Tests for RegistrationCodeCreateSerializer with custom validate."""

    def _valid_payload(self, **overrides):
        base = {
            "codeType": "STUDENT",
            "count": 5,
            "usesPerCode": 1,
            "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
        }
        base.update(overrides)
        return base

    def test_valid_payload(self):
        """Complete valid payload passes validation."""
        ser = RegistrationCodeCreateSerializer(data=self._valid_payload())
        assert ser.is_valid() is True

    def test_code_type_required(self):
        """Missing codeType fails validation."""
        data = self._valid_payload()
        del data["codeType"]
        ser = RegistrationCodeCreateSerializer(data=data)
        assert ser.is_valid() is False
        assert "codeType" in ser.errors

    def test_count_required(self):
        """Missing count fails validation."""
        data = self._valid_payload()
        del data["count"]
        ser = RegistrationCodeCreateSerializer(data=data)
        assert ser.is_valid() is False
        assert "count" in ser.errors

    def test_count_min_value(self):
        """Count below 1 is rejected."""
        ser = RegistrationCodeCreateSerializer(data=self._valid_payload(count=0))
        assert ser.is_valid() is False
        assert "count" in ser.errors

    def test_uses_per_code_min_value(self):
        """usesPerCode below 1 is rejected."""
        ser = RegistrationCodeCreateSerializer(data=self._valid_payload(usesPerCode=0))
        assert ser.is_valid() is False
        assert "usesPerCode" in ser.errors

    def test_expires_at_required(self):
        """Missing expiresAt fails validation."""
        data = self._valid_payload()
        del data["expiresAt"]
        ser = RegistrationCodeCreateSerializer(data=data)
        assert ser.is_valid() is False
        assert "expiresAt" in ser.errors

    def test_course_id_optional(self):
        """courseId is optional."""
        ser = RegistrationCodeCreateSerializer(data=self._valid_payload())
        assert ser.is_valid() is True
        assert "courseId" not in ser.validated_data

    def test_course_id_min_value(self):
        """courseId below 1 is rejected."""
        ser = RegistrationCodeCreateSerializer(data=self._valid_payload(courseId=0))
        assert ser.is_valid() is False
        assert "courseId" in ser.errors

    def test_metadata_with_count_not_one_rejected(self):
        """metadata is only valid when count is exactly 1."""
        ser = RegistrationCodeCreateSerializer(
            data=self._valid_payload(metadata={"key": "val"}, count=2)
        )
        assert ser.is_valid() is False
        assert "count" in ser.errors

    def test_metadata_with_non_teacher_rejected(self):
        """metadata is only supported for TEACHER code type."""
        ser = RegistrationCodeCreateSerializer(
            data=self._valid_payload(
                metadata={"key": "val"}, count=1, codeType="STUDENT"
            )
        )
        assert ser.is_valid() is False
        assert "metadata" in ser.errors

    def test_metadata_with_teacher_and_count_one_accepted(self):
        """metadata with codeType=TEACHER and count=1 passes validation."""
        ser = RegistrationCodeCreateSerializer(
            data=self._valid_payload(
                metadata={"key": "val"}, count=1, codeType="TEACHER"
            )
        )
        assert ser.is_valid() is True

    def test_legacy_role_prefix_in_code_type(self):
        """ROLE_TEACHER prefix is normalized for codeType field."""
        ser = RegistrationCodeCreateSerializer(
            data=self._valid_payload(codeType="ROLE_STUDENT")
        )
        assert ser.is_valid() is True
        assert ser.validated_data["codeType"] == "STUDENT"


# ---------------------------------------------------------------------------
# RegistrationCodeUpdateSerializer
# ---------------------------------------------------------------------------


class TestRegistrationCodeUpdateSerializer:
    """Tests for RegistrationCodeUpdateSerializer."""

    def test_valid_revoked(self):
        """REVOKED status passes validation."""
        ser = RegistrationCodeUpdateSerializer(data={"status": "REVOKED"})
        assert ser.is_valid() is True

    def test_invalid_status_rejected(self):
        """Status not in allowed choices is rejected."""
        ser = RegistrationCodeUpdateSerializer(data={"status": "ACTIVE"})
        assert ser.is_valid() is False
        assert "status" in ser.errors

    def test_status_required(self):
        """Missing status fails validation."""
        ser = RegistrationCodeUpdateSerializer(data={})
        assert ser.is_valid() is False
        assert "status" in ser.errors

    def test_reason_optional(self):
        """Reason field is optional."""
        ser = RegistrationCodeUpdateSerializer(data={"status": "REVOKED"})
        assert ser.is_valid() is True
        assert "reason" not in ser.validated_data

    def test_reason_blank_rejected(self):
        """Blank reason string is rejected."""
        ser = RegistrationCodeUpdateSerializer(data={"status": "REVOKED", "reason": ""})
        assert ser.is_valid() is False
        assert "reason" in ser.errors


# ---------------------------------------------------------------------------
# UserRoleSerializer
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUserRoleSerializer:
    """Tests for UserRoleSerializer output."""

    def test_output_contains_role_field(self):
        """Serialized output contains the role field."""
        role_obj = SimpleNamespace(role=Role.TEACHER)
        data = UserRoleSerializer(role_obj).data
        assert data == {"role": "TEACHER"}


# ---------------------------------------------------------------------------
# LoginSerializer
# ---------------------------------------------------------------------------


class TestLoginSerializer:
    """Tests for LoginSerializer custom validation."""

    def test_valid_with_identifier(self):
        """Payload with identifier passes validation."""
        ser = LoginSerializer(data={"identifier": "user@test.com", "password": "pass"})
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user@test.com"

    def test_valid_with_username_fallback(self):
        """Username field is accepted as identifier fallback."""
        ser = LoginSerializer(data={"username": "user@test.com", "password": "pass"})
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user@test.com"

    def test_missing_both_identifier_and_username(self):
        """Missing both identifier and username fails validation."""
        ser = LoginSerializer(data={"password": "pass"})
        assert ser.is_valid() is False
        assert "identifier" in ser.errors

    def test_password_required(self):
        """Missing password fails validation."""
        ser = LoginSerializer(data={"identifier": "user@test.com"})
        assert ser.is_valid() is False
        assert "password" in ser.errors

    def test_password_whitespace_preserved(self):
        """Whitespace in password is preserved."""
        ser = LoginSerializer(data={"identifier": "u", "password": " pass "})
        assert ser.is_valid() is True
        assert ser.validated_data["password"] == " pass "

    def test_password_blank_rejected(self):
        """Blank password string is rejected."""
        ser = LoginSerializer(data={"identifier": "u", "password": ""})
        assert ser.is_valid() is False
        assert "password" in ser.errors


# ---------------------------------------------------------------------------
# GoogleOAuthLoginSerializer
# ---------------------------------------------------------------------------


class TestGoogleOAuthLoginSerializer:
    """Tests for GoogleOAuthLoginSerializer."""

    def test_valid_token(self):
        """Valid accessToken passes validation."""
        ser = GoogleOAuthLoginSerializer(data={"accessToken": "ya29.token"})
        assert ser.is_valid() is True

    def test_access_token_required(self):
        """Missing accessToken fails validation."""
        ser = GoogleOAuthLoginSerializer(data={})
        assert ser.is_valid() is False
        assert "accessToken" in ser.errors

    def test_access_token_blank_rejected(self):
        """Blank accessToken is rejected."""
        ser = GoogleOAuthLoginSerializer(data={"accessToken": ""})
        assert ser.is_valid() is False


# ---------------------------------------------------------------------------
# RefreshTokenSerializer
# ---------------------------------------------------------------------------


class TestRefreshTokenSerializer:
    """Tests for RefreshTokenSerializer."""

    def test_valid_token(self):
        """Valid refreshToken passes validation."""
        ser = RefreshTokenSerializer(data={"refreshToken": "some-jwt-token"})
        assert ser.is_valid() is True

    def test_refresh_token_required(self):
        """Missing refreshToken fails validation."""
        ser = RefreshTokenSerializer(data={})
        assert ser.is_valid() is False
        assert "refreshToken" in ser.errors

    def test_refresh_token_blank_rejected(self):
        """Blank refreshToken is rejected."""
        ser = RefreshTokenSerializer(data={"refreshToken": ""})
        assert ser.is_valid() is False


# ---------------------------------------------------------------------------
# PasswordChangeSerializer
# ---------------------------------------------------------------------------


class TestPasswordChangeSerializer:
    """Tests for PasswordChangeSerializer."""

    def _valid_payload(self, **overrides):
        base = {
            "currentPassword": "OldPass123!",
            "newPassword": "NewPass456!",
            "confirmPassword": "NewPass456!",
        }
        base.update(overrides)
        return base

    def test_valid_payload(self):
        """Complete valid payload passes validation."""
        ser = PasswordChangeSerializer(data=self._valid_payload())
        assert ser.is_valid() is True

    def test_current_password_required(self):
        """Missing currentPassword fails validation."""
        data = self._valid_payload()
        del data["currentPassword"]
        ser = PasswordChangeSerializer(data=data)
        assert ser.is_valid() is False
        assert "currentPassword" in ser.errors

    def test_new_password_required(self):
        """Missing newPassword fails validation."""
        data = self._valid_payload()
        del data["newPassword"]
        ser = PasswordChangeSerializer(data=data)
        assert ser.is_valid() is False
        assert "newPassword" in ser.errors

    def test_confirm_password_required(self):
        """Missing confirmPassword fails validation."""
        data = self._valid_payload()
        del data["confirmPassword"]
        ser = PasswordChangeSerializer(data=data)
        assert ser.is_valid() is False
        assert "confirmPassword" in ser.errors

    def test_whitespace_preserved_in_passwords(self):
        """Whitespace is preserved in all password fields."""
        ser = PasswordChangeSerializer(
            data=self._valid_payload(
                currentPassword=" old ",
                newPassword=" new ",
                confirmPassword=" new ",
            )
        )
        assert ser.is_valid() is True
        assert ser.validated_data["currentPassword"] == " old "
        assert ser.validated_data["newPassword"] == " new "


# ---------------------------------------------------------------------------
# PasswordResetCodeIssueSerializer
# ---------------------------------------------------------------------------


class TestPasswordResetCodeIssueSerializer:
    """Tests for PasswordResetCodeIssueSerializer."""

    def test_valid_payload(self):
        """Valid targetUserId passes validation."""
        ser = PasswordResetCodeIssueSerializer(data={"targetUserId": 42})
        assert ser.is_valid() is True

    def test_target_user_id_required(self):
        """Missing targetUserId fails validation."""
        ser = PasswordResetCodeIssueSerializer(data={})
        assert ser.is_valid() is False
        assert "targetUserId" in ser.errors

    def test_target_user_id_min_value(self):
        """targetUserId below 1 is rejected."""
        ser = PasswordResetCodeIssueSerializer(data={"targetUserId": 0})
        assert ser.is_valid() is False
        assert "targetUserId" in ser.errors

    def test_rejects_unknown_fields(self):
        """Unknown fields are rejected (inherits StrictFieldsSerializer)."""
        ser = PasswordResetCodeIssueSerializer(
            data={"targetUserId": 1, "extra": "bad"}
        )
        assert ser.is_valid() is False
        assert "extra" in ser.errors


# ---------------------------------------------------------------------------
# PasswordResetCodeVerifySerializer
# ---------------------------------------------------------------------------


class TestPasswordResetCodeVerifySerializer:
    """Tests for PasswordResetCodeVerifySerializer custom validation."""

    def test_valid_with_identifier(self):
        """Payload with identifier and resetCode passes validation."""
        ser = PasswordResetCodeVerifySerializer(
            data={"identifier": "user@test.com", "resetCode": "ABC123"}
        )
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user@test.com"

    def test_username_fallback(self):
        """Username is used as identifier when identifier is absent."""
        ser = PasswordResetCodeVerifySerializer(
            data={"username": "user1", "resetCode": "ABC123"}
        )
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user1"

    def test_email_fallback(self):
        """Email is used as identifier when identifier and username absent."""
        ser = PasswordResetCodeVerifySerializer(
            data={"email": "user@test.com", "resetCode": "ABC123"}
        )
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user@test.com"

    def test_missing_all_identifiers(self):
        """Missing all identifier fields fails validation."""
        ser = PasswordResetCodeVerifySerializer(data={"resetCode": "ABC123"})
        assert ser.is_valid() is False
        assert "identifier" in ser.errors

    def test_reset_code_required(self):
        """Missing resetCode fails validation."""
        ser = PasswordResetCodeVerifySerializer(data={"identifier": "user@test.com"})
        assert ser.is_valid() is False
        assert "resetCode" in ser.errors


# ---------------------------------------------------------------------------
# PasswordResetCodeCompleteSerializer
# ---------------------------------------------------------------------------


class TestPasswordResetCodeCompleteSerializer:
    """Tests for PasswordResetCodeCompleteSerializer custom validation."""

    def _valid_payload(self, **overrides):
        base = {
            "identifier": "user@test.com",
            "resetCode": "ABC123",
            "newPassword": "NewPass456!",
            "confirmPassword": "NewPass456!",
        }
        base.update(overrides)
        return base

    def test_valid_payload(self):
        """Complete valid payload passes validation."""
        ser = PasswordResetCodeCompleteSerializer(data=self._valid_payload())
        assert ser.is_valid() is True

    def test_username_fallback(self):
        """Username is used as identifier when identifier is absent."""
        data = self._valid_payload()
        del data["identifier"]
        data["username"] = "user1"
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user1"

    def test_email_fallback(self):
        """Email is used as identifier when identifier and username absent."""
        data = self._valid_payload()
        del data["identifier"]
        data["email"] = "user@test.com"
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is True
        assert ser.validated_data["identifier"] == "user@test.com"

    def test_missing_all_identifiers(self):
        """Missing all identifier fields fails validation."""
        data = self._valid_payload()
        del data["identifier"]
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is False
        assert "identifier" in ser.errors

    def test_reset_code_required(self):
        """Missing resetCode fails validation."""
        data = self._valid_payload()
        del data["resetCode"]
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is False
        assert "resetCode" in ser.errors

    def test_new_password_required(self):
        """Missing newPassword fails validation."""
        data = self._valid_payload()
        del data["newPassword"]
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is False
        assert "newPassword" in ser.errors

    def test_confirm_password_required(self):
        """Missing confirmPassword fails validation."""
        data = self._valid_payload()
        del data["confirmPassword"]
        ser = PasswordResetCodeCompleteSerializer(data=data)
        assert ser.is_valid() is False
        assert "confirmPassword" in ser.errors
