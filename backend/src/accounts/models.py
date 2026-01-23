"""
Account and profile models for user authentication and authorization.

This module defines the core user model and associated profiles that power
the authentication and role-based access control system. The architecture
supports three user types:

    ADMIN: Full system access, can manage assessments and view all data
    TEACHER: Can create courses, enroll students, create assignments
    STUDENT: Can view assigned assessments and submit responses

User Creation Flows:
    1. Self-registration (register endpoint): Creates user + STUDENT role + StudentProfile
    2. Teacher creation (admin creates): Creates user + TEACHER role + TeacherProfile
    3. Student import (teacher imports): Creates user + STUDENT role + StudentProfile
    4. OAuth login (Google): Creates/links user via OAuthAccount

Database Tables:
    app_users        - Core user accounts (email-based authentication)
    user_roles       - Many-to-many join table for user roles
    teacher_profiles - Extended data for teacher accounts
    student_profiles - Extended data for student accounts (includes consent)
    oauth_accounts   - Linked external identity provider accounts

Note:
    The User model uses email as the username field. All emails are
    normalized to lowercase during creation.
"""

from typing import cast

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom manager for User model with email-based authentication.

    Provides factory methods for creating regular users and superusers,
    handling email normalization and password hashing automatically.
    """

    def create_user(self, username, name, password=None, **extra_fields) -> "User":
        """
        Create and persist a user with a normalized email.

        Args:
            username: Email address (will be normalized to lowercase)
            name: Display name for the user
            password: Optional plain-text password (hashed before storage)
            **extra_fields: Additional fields to set on the user model

        Returns:
            User: The created and saved user instance

        Raises:
            ValueError: If username or name is empty
        """
        if not username:
            raise ValueError("username is required")
        if not name:
            raise ValueError("name is required")
        username = self.normalize_email(username)
        user = cast("User", self.model(username=username, name=name, **extra_fields))
        if password:
            user.set_password(password)
        else:
            user.password = None
        user.save(using=self._db)
        return user

    def create_superuser(self, username, name, password=None, **extra_fields):
        """
        Create and persist a superuser with admin role.

        Superusers are automatically granted is_staff and is_superuser flags,
        and receive the ADMIN role in the user_roles table.

        Args:
            username: Email address for the superuser
            name: Display name
            password: Plain-text password (hashed before storage)
            **extra_fields: Additional fields (is_staff/is_superuser enforced)

        Returns:
            User: The created superuser with ADMIN role

        Raises:
            ValueError: If is_staff or is_superuser explicitly set to False
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        user = self.create_user(username, name, password, **extra_fields)
        UserRole.objects.get_or_create(user=user, role=Role.ADMIN)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the primary identifier.

    This model replaces Django's default User model to support email-based
    authentication. Users can authenticate via password or OAuth (Google).

    Attributes:
        username: Email address serving as unique identifier (max 320 chars)
        name: Display name shown in UI (max 255 chars)
        is_active: Whether account can authenticate (db column: enabled)
        is_staff: Whether user can access Django admin
        created_at: Timestamp of account creation
        updated_at: Timestamp of last modification
        password: Hashed password (nullable for OAuth-only users)

    Related Models:
        roles: UserRole instances defining user's permissions
        teacher_profile: TeacherProfile if user is a teacher
        student_profile: StudentProfile if user is a student
    """

    # Email address used as the unique identifier for authentication
    username = models.EmailField(max_length=320, unique=True)

    # Display name shown throughout the application UI
    name = models.CharField(max_length=255)

    # Account status flag - disabled accounts cannot authenticate
    # Note: db_column="enabled" for legacy compatibility
    is_active = models.BooleanField(db_column="enabled", default=True)

    # Django admin access flag - only superusers typically have this
    is_staff = models.BooleanField(default=False)

    # Automatic timestamps for auditing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Password hash - nullable to support OAuth-only accounts
    # Note: db_column="password_hash" for legacy compatibility
    password = models.CharField(  # type: ignore[assignment]
        max_length=128,
        db_column="password_hash",
        blank=True,
        null=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        """Database table configuration for User."""

        db_table = "app_users"
        constraints = [
            models.UniqueConstraint(fields=["username"], name="uq_user_username"),
        ]
        indexes = [
            models.Index(fields=["username"], name="idx_user_username"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"{self.name} <{self.username}>"


class Role(models.TextChoices):
    """
    Enumeration of application roles for authorization checks.

    Roles determine what actions a user can perform in the system.
    Users can have multiple roles (stored in UserRole), but permission
    checks typically use the "primary" role (highest privilege).

    Role Hierarchy (highest to lowest):
        ADMIN > TEACHER > STUDENT

    Values:
        ADMIN: System administrator with full access
        TEACHER: Can create courses, assignments, view student data
        STUDENT: Can view assigned work and submit responses
    """

    ADMIN = "ADMIN", "Admin"
    TEACHER = "TEACHER", "Teacher"
    STUDENT = "STUDENT", "Student"


class UserRole(models.Model):
    """
    Join table mapping users to their assigned roles.

    Users can have multiple roles (e.g., a teacher who is also an admin).
    The unique constraint ensures no duplicate role assignments.

    Attributes:
        user: Foreign key to the User model
        role: One of the Role enum values (ADMIN, TEACHER, STUDENT)

    Note:
        When checking permissions, the system uses the user's "primary"
        role (highest privilege level) via the primary_role() helper.
    """

    # Reference to the user who holds this role
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="roles"
    )

    # The role assigned to the user (from Role enum)
    role = models.CharField(max_length=32, choices=Role.choices)

    class Meta:
        """Database table configuration for UserRole."""

        db_table = "user_roles"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uq_user_role"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"{self.user.username}: {self.role}"


class TeacherProfile(models.Model):
    """
    Extended profile data for teacher accounts.

    Every user with the TEACHER role should have an associated TeacherProfile.
    This model stores teacher-specific data and serves as the owner reference
    for courses created by the teacher.

    Attributes:
        user: One-to-one link to the User model
        created_at: When the teacher profile was created

    Related Models:
        courses: Course instances owned by this teacher (via Course.teacher)
    """

    # One-to-one link to the user account
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="teacher_profile"
    )

    # Timestamp for auditing when teacher was onboarded
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Database table configuration for TeacherProfile."""

        db_table = "teacher_profiles"
        constraints = [
            models.UniqueConstraint(fields=["user"], name="uq_teacher_user"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"TeacherProfile({self.user.username})"


class StudentProfile(models.Model):
    """
    Extended profile data for student accounts.

    Every user with the STUDENT role should have an associated StudentProfile.
    Students are typically created by teachers via roster import, and the
    created_by field tracks which teacher provisioned the account.

    Attributes:
        user: One-to-one link to the User model
        created_by: Teacher who created this student account (PROTECT on delete)
        consent: Whether the student/guardian has consented to data collection
        created_at: When the student profile was created

    Related Models:
        enrollments: Enrollment instances linking student to courses

    Note:
        The consent field is required for certain data collection features.
        Teachers importing students should obtain consent separately.
    """

    # One-to-one link to the user account
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="student_profile"
    )

    # Teacher who provisioned this student account
    # PROTECT prevents deleting teacher if they have created students
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_column="created_by_user_id",
        related_name="students_created",
    )

    # Data collection consent flag (required for certain features)
    consent = models.BooleanField(default=False)

    # Timestamp for auditing when student was added
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Database table configuration for StudentProfile."""

        db_table = "student_profiles"
        constraints = [
            models.UniqueConstraint(fields=["user"], name="uq_student_user"),
        ]
        indexes = [
            models.Index(fields=["created_by"], name="idx_student_created_by"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"StudentProfile({self.user.username})"


class OAuthProvider(models.TextChoices):
    """
    Enumeration of supported OAuth identity providers.

    Currently only Google is supported, but this enum allows for
    future expansion to other providers (Microsoft, GitHub, etc.).

    Values:
        GOOGLE: Google OAuth 2.0 identity provider
    """

    GOOGLE = "GOOGLE", "Google"


class OAuthAccount(models.Model):
    """
    External OAuth account linked to a local user.

    Stores information from OAuth identity providers (currently Google)
    to enable social login. A single user can have multiple OAuth accounts
    from different providers.

    Attributes:
        user: Foreign key to the local User account
        provider: Which OAuth provider (from OAuthProvider enum)
        subject: Provider's unique identifier for the user (sub claim)
        email: Email address from the OAuth provider
        email_verified: Whether provider verified the email (from token)
        picture_url: Profile picture URL from the provider
        created_at: When the OAuth link was first established
        last_login_at: Timestamp of most recent OAuth login

    Unique Constraint:
        (provider, subject) - prevents duplicate links to same external account
    """

    # Link to the local user account
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")

    # Which OAuth provider this account is from
    provider = models.CharField(max_length=32, choices=OAuthProvider.choices)

    # Provider's unique ID for the user (the "sub" claim in OIDC)
    subject = models.CharField(max_length=255)

    # Email from the OAuth provider (may differ from local username)
    email = models.EmailField(max_length=320)

    # Whether the provider has verified this email address
    email_verified = models.BooleanField(null=True, blank=True)

    # Profile picture URL from the OAuth provider
    picture_url = models.CharField(max_length=512, null=True, blank=True)

    # When the OAuth account was first linked
    created_at = models.DateTimeField(auto_now_add=True)

    # Updated on each OAuth login for activity tracking
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Database table configuration for OAuthAccount."""

        db_table = "oauth_accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "subject"], name="uq_oauth_provider_subject"
            ),
        ]
        indexes = [
            models.Index(fields=["email"], name="idx_oauth_email"),
            models.Index(fields=["user"], name="idx_oauth_user"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"{self.provider}:{self.subject}"
