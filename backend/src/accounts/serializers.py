"""
Serializers for auth and user management.

This module provides DRF serializers for validating and transforming user-related
API payloads. Serializers handle both input validation (requests) and output
formatting (responses).

Input Serializers (for request validation):
    UserInputSerializer: User creation/update payloads
    BulkUserSerializer: Batch user creation

Output Serializers (for response formatting):
    UserOutputSerializer: User details with role
    CheckEmailSerializer: Email availability check response
    UserRoleSerializer: Role records

Note:
    The RoleChoiceField handles legacy ROLE_* format from the Java API,
    converting "ROLE_TEACHER" to "TEACHER" for internal use.
"""

from rest_framework import serializers

from .models import Role, User, UserRole


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
        username: Email address (max 320 chars)
        password: Plain-text password (hashed by service layer)
        role: User role (RESEARCHER, TEACHER, STUDENT)

    Note:
        All fields are optional to support partial updates.
        Password whitespace is preserved (trim_whitespace=False).
    """

    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    username = serializers.EmailField(required=False, max_length=320)
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
        username: Email address
        role: Role as ROLE_RESEARCHER, ROLE_TEACHER, or ROLE_STUDENT
    """

    role = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata for UserOutputSerializer."""

        model = User
        fields = ("id", "name", "username", "role")

    def get_role(self, obj):
        """
        Return the user's primary role as a ROLE_* string.

        Falls back to ROLE_STUDENT if no role is assigned.
        """
        role = obj.roles.values_list("role", flat=True).first()
        value = role or Role.STUDENT
        return f"ROLE_{value}"


class CheckEmailSerializer(serializers.Serializer):
    """
    Response format for the email availability check endpoint.

    Used by the frontend to determine login flow (password vs OAuth).

    Fields:
        exists: Whether a user with this email exists
        userId: The user's ID if found (0 if not found)
        needsPassword: Whether user needs to set a password (OAuth-only users)
    """

    exists = serializers.BooleanField()
    userId = serializers.IntegerField()
    needsPassword = serializers.BooleanField()


class BulkUserSerializer(serializers.Serializer):
    """
    Validates batch user creation payloads.

    Used for CSV import of multiple users at once.

    Fields:
        users: List of UserInputSerializer objects
    """

    users = UserInputSerializer(many=True)


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
