"""
Serializers for auth and user management.

This module provides DRF serializers for validating and transforming user-related
API payloads. Serializers handle both input validation (requests) and output
formatting (responses).

Input Serializers (for request validation):
    UserInputSerializer: User creation/update payloads
    StudentInviteRegisterSerializer: Invite registration/redeem payloads
    RegistrationCodeValidateInputSerializer: Code validation payload

Output Serializers (for response formatting):
    UserOutputSerializer: User details with role
    UserRoleSerializer: Role records

Note:
    The RoleChoiceField handles legacy ROLE_* format from the Java API,
    converting "ROLE_TEACHER" to "TEACHER" for internal use.
"""

from rest_framework import serializers

from .models import PasswordResetRequestStatus, RegistrationCodeType, Role, User, UserRole


class RoleChoiceField(serializers.ChoiceField):
    """
    Custom choice field that normalizes legacy role strings.

    The Java API used ROLE_* format (ROLE_TEACHER, ROLE_STUDENT).
    This field accepts both formats and normalizes to RESEARCHER, TEACHER, STUDENT.

    Example:
        "ROLE_TEACHER" -> "TEACHER"
        "TEACHER" -> "TEACHER" (unchanged)
    """

    def to_internal_value(self, data):
        """
        Normalize role strings like ROLE_TEACHER to enum values.

        Strips the "ROLE_" prefix if present before standard validation.
        """
        if isinstance(data, str) and data.startswith("ROLE_"):
            data = data.replace("ROLE_", "", 1)
        return super().to_internal_value(data)


class UserInputSerializer(serializers.Serializer):
    """
    Validates user payloads from admin or auth endpoints.

    Used for registration, user creation by admin, and user updates.

    Fields:
        id: Optional user ID (for updates)
        name: Display name (max 255 chars)
        username: Login identifier (max 320 chars)
        email: Optional email identifier/contact (required for non-students in service layer)
        password: Plain-text password (hashed by service layer)
        role: User role (RESEARCHER, TEACHER, STUDENT)

    Note:
        All fields are optional to support partial updates.
        Password whitespace is preserved (trim_whitespace=False).
    """

    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.EmailField(
        required=False, allow_blank=False, allow_null=True, max_length=320
    )
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        trim_whitespace=False,
    )
    role = RoleChoiceField(choices=Role.choices, required=False)


class UserOutputSerializer(serializers.ModelSerializer):
    """
    Formats user data for API responses.

    Includes the user's primary role in ROLE_* format for
    backwards compatibility with frontend expectations.

    Fields:
        id: User's database ID
        name: Display name
        username: Login identifier
        email: Contact/login email when present
        role: Role as ROLE_RESEARCHER, ROLE_TEACHER, or ROLE_STUDENT
    """

    role = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata for UserOutputSerializer."""

        model = User
        fields = ("id", "name", "username", "email", "role")

    def get_role(self, obj):
        """
        Return the user's primary role as a ROLE_* string.

        Falls back to ROLE_STUDENT if no role is assigned.
        """
        role = obj.roles.values_list("role", flat=True).first()
        value = role or Role.STUDENT
        return f"ROLE_{value}"


class RegistrationCodeValidateInputSerializer(serializers.Serializer):
    """Payload for validating an invite code before registration."""

    code = serializers.CharField(max_length=64)


class StudentInviteRegisterSerializer(serializers.Serializer):
    """
    Payload for local registration via invite code.
    """

    code = serializers.CharField(max_length=64)
    name = serializers.CharField(required=True, allow_blank=False, max_length=255)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.EmailField(required=False, allow_blank=False, max_length=320)
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
        trim_whitespace=False,
    )


class StudentJoinCourseSerializer(serializers.Serializer):
    """Payload for authenticated student join-course redemption."""

    code = serializers.CharField(max_length=64)


class RegistrationOAuthSerializer(serializers.Serializer):
    """Payload for non-student OAuth registration via invite code."""

    code = serializers.CharField(max_length=64)
    accessToken = serializers.CharField(required=True, allow_blank=False)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    name = serializers.CharField(required=False, allow_blank=False, max_length=255)


class RegistrationCodeCreateSerializer(serializers.Serializer):
    """Payload for registration code generation endpoints."""

    codeType = RoleChoiceField(choices=RegistrationCodeType.choices, required=True)
    count = serializers.IntegerField(required=True, min_value=1)
    usesPerCode = serializers.IntegerField(required=True, min_value=1)
    expiresAt = serializers.DateTimeField(required=True)
    courseId = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.DictField(required=False)

    def validate(self, attrs):
        metadata = attrs.get("metadata")
        count = attrs["count"]
        code_type = attrs["codeType"]
        if metadata and count != 1:
            raise serializers.ValidationError(
                {"count": "count must be 1 when metadata is provided"}
            )
        if metadata and code_type != RegistrationCodeType.TEACHER:
            raise serializers.ValidationError(
                {"metadata": "metadata is only supported for teacher code generation"}
            )
        return attrs


class RegistrationCodeUpdateSerializer(serializers.Serializer):
    """Payload for code lifecycle state transitions."""

    status = serializers.ChoiceField(choices=["REVOKED", "ARCHIVED"])
    reason = serializers.CharField(required=False, allow_blank=False, max_length=255)


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Serializes individual role records.

    Used when listing all roles assigned to a user.

    Fields:
        role: The role value (RESEARCHER, TEACHER, or STUDENT)
    """

    class Meta:
        """Serializer metadata for UserRoleSerializer."""

        model = UserRole
        fields = ("role",)


class LoginSerializer(serializers.Serializer):
    """Payload for password login."""

    identifier = serializers.CharField(required=False, allow_blank=False, max_length=320)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    password = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username")
        if not identifier:
            raise serializers.ValidationError({"identifier": "identifier is required"})
        attrs["identifier"] = identifier
        return attrs


class GoogleOAuthLoginSerializer(serializers.Serializer):
    """Payload for Google OAuth login."""

    accessToken = serializers.CharField(required=True, allow_blank=False)


class RefreshTokenSerializer(serializers.Serializer):
    """Payload for token refresh/logout."""

    refreshToken = serializers.CharField(required=True, allow_blank=False)


class PasswordChangeSerializer(serializers.Serializer):
    """Payload for self-service password change."""

    currentPassword = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)
    newPassword = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)
    confirmPassword = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)


class PasswordResetRequestCreateSerializer(serializers.Serializer):
    """Payload to initiate a reset request."""

    identifier = serializers.CharField(required=False, allow_blank=False, max_length=320)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.CharField(required=False, allow_blank=False, max_length=320)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "identifier is required"})
        attrs["identifier"] = identifier
        return attrs


class PasswordResetStatusSerializer(serializers.Serializer):
    """Payload to check reset request status."""

    identifier = serializers.CharField(required=False, allow_blank=False, max_length=320)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.CharField(required=False, allow_blank=False, max_length=320)
    requestToken = serializers.CharField(required=True, allow_blank=False, max_length=64)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "identifier is required"})
        attrs["identifier"] = identifier
        return attrs


class PasswordResetTransitionSerializer(serializers.Serializer):
    """Payload for approver state transition."""

    status = serializers.ChoiceField(
        choices=[PasswordResetRequestStatus.APPROVED, PasswordResetRequestStatus.DENIED]
    )
    reason = serializers.CharField(required=False, allow_blank=False, max_length=255)
    expires_at = serializers.DateTimeField(required=False)


class PasswordResetCodeVerifySerializer(serializers.Serializer):
    """Payload to verify a reset code."""

    identifier = serializers.CharField(required=False, allow_blank=False, max_length=320)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.CharField(required=False, allow_blank=False, max_length=320)
    resetCode = serializers.CharField(required=True, allow_blank=False, max_length=64)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "identifier is required"})
        attrs["identifier"] = identifier
        return attrs


class PasswordResetCodeCompleteSerializer(serializers.Serializer):
    """Payload to complete a reset with a valid code."""

    identifier = serializers.CharField(required=False, allow_blank=False, max_length=320)
    username = serializers.CharField(required=False, allow_blank=False, max_length=320)
    email = serializers.CharField(required=False, allow_blank=False, max_length=320)
    resetCode = serializers.CharField(required=True, allow_blank=False, max_length=64)
    newPassword = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)
    confirmPassword = serializers.CharField(required=True, allow_blank=False, trim_whitespace=False)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "identifier is required"})
        attrs["identifier"] = identifier
        return attrs
