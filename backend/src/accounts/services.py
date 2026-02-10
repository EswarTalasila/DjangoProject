"""
Account service helpers.

This module provides business logic for user account management including:
- Role normalization and assignment
- Profile creation for teachers and students
- Authentication and authorization checks
- User creation from payloads
- OAuth account linking
"""

from django.contrib.auth import authenticate
from django.db import transaction

from core.permissions import has_sudo_permission, primary_role
from courses.models import Enrollment

from .models import (
    OAuthAccount,
    OAuthProvider,
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)


def _get_role_value(role: str | None) -> Role:
    """
    Normalize a role string to a valid Role enum value.

    Handles legacy ROLE_ prefixes from the Spring Boot API and defaults to STUDENT
    if no role is provided.

    Args:
        role: Raw role string, possibly with ROLE_ prefix (e.g., "ROLE_TEACHER")

    Returns:
        Normalized Role enum value (RESEARCHER, TEACHER, or STUDENT)

    Raises:
        ValueError: If the role string is not a valid Role choice
    """
    if not role:
        return Role.STUDENT
    if isinstance(role, str) and role.startswith("ROLE_"):
        role = role.replace("ROLE_", "", 1)
    
    try:
        return Role(role)
    except ValueError:
        valid_roles = [r.value for r in Role]
        raise ValueError(f"Invalid role '{role}'. Must be one of: {valid_roles}")


def set_single_role(user: User, role: str) -> None:
    """
    Set a single role for a user, replacing any existing roles.

    This ensures each user has exactly one role at a time, which simplifies
    permission checks throughout the application.

    Args:
        user: The user to update
        role: The role to assign (will be normalized)
    """
    normalized = _get_role_value(role)
    UserRole.objects.filter(user=user).delete()
    UserRole.objects.create(user=user, role=normalized)


def ensure_profiles_for_role(user: User, role: str, creator: User | None = None) -> None:
    """
    Create the appropriate profile for a user's role if it does not exist.

    Each role requires a corresponding profile:
    - RESEARCHER: ResearcherProfile
    - TEACHER: TeacherProfile
    - STUDENT: StudentProfile (with consent tracking and creator reference)

    Args:
        user: The user who needs a profile
        role: The user's role (determines which profile to create)
        creator: For students, the user who created this student account
    """
    normalized = _get_role_value(role)
    if normalized == Role.RESEARCHER and not ResearcherProfile.objects.filter(user=user).exists():
        ResearcherProfile.objects.create(user=user)
    if normalized == Role.TEACHER and not TeacherProfile.objects.filter(user=user).exists():
        TeacherProfile.objects.create(user=user)
    if normalized == Role.STUDENT and not StudentProfile.objects.filter(user=user).exists():
        StudentProfile.objects.create(user=user, created_by=creator or user, consent=False)


def build_user_response(user: User, access_token: str) -> dict:
    """
    Build the login response payload for a user.

    This creates the response structure expected by the frontend after
    successful authentication, including the JWT token and user metadata.

    Args:
        user: The authenticated user
        access_token: The JWT access token to include

    Returns:
        Dict with email, name, accessToken, tokenType, role, and id
    """
    role = primary_role(user)
    payload = {
        "email": user.username,
        "name": user.name,
        "accessToken": access_token,
        "tokenType": "Bearer",
        "role": role,
        "id": str(user.id),
    }
    return payload


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.

    Args:
        username: The user's email address (used as username)
        password: The user's password

    Returns:
        The authenticated User object, or None if authentication fails
    """
    return authenticate(username=username, password=password)


def can_create_user(request_user: User, requested_role: str) -> bool:
    """
    Check if request_user is allowed to create a user with the requested role.

    Permission hierarchy:
    - Admins (is_staff) can create researchers and teachers
    - Researchers with sudo can create teachers (CREATE_TEACHER) or students (CREATE_STUDENT)
    - Teachers can create students
    - Students cannot create any users

    Args:
        request_user: The user making the create request
        requested_role: The role for the new user

    Returns:
        True if the creation is allowed, False otherwise
    """
    role = _get_role_value(requested_role)
    request_role = primary_role(request_user)

    # Admin can create researchers and teachers
    if request_user.is_staff:
        return role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can create teachers/students
    if request_role == Role.RESEARCHER:
        if role == Role.TEACHER and has_sudo_permission(request_user, SudoPermission.CREATE_TEACHER):
            return True
        if role == Role.STUDENT and has_sudo_permission(request_user, SudoPermission.CREATE_STUDENT):
            return True

    # Teacher can create students
    if request_role == Role.TEACHER:
        return role == Role.STUDENT

    return False


def teacher_owns_student(teacher_user: User, student_user: User) -> bool:
    """
    Check if a teacher has ownership over a student via course enrollment.

    A teacher "owns" a student if that student is enrolled in any course
    taught by the teacher. This establishes the permission relationship
    for teachers to manage their students.

    Args:
        teacher_user: The potential teacher
        student_user: The potential student

    Returns:
        True if the student is enrolled in one of the teacher's courses
    """
    if primary_role(teacher_user) != Role.TEACHER:
        return False
    if primary_role(student_user) != Role.STUDENT:
        return False
    try:
        student_profile = student_user.student_profile
    except StudentProfile.DoesNotExist:
        return False
    return Enrollment.objects.filter(
        student_profile=student_profile, course__teacher_profile__user=teacher_user
    ).exists()


def can_edit_user(request_user: User, target_user: User, requested_role: str) -> bool:
    """
    Check if request_user can edit target_user with the requested role.

    Permission rules:
    - Admins (is_staff) can edit researchers and teachers
    - Researchers with EDIT_USER sudo can edit teachers and students
    - Teachers can edit students they own (enrolled in their courses)
    - Students cannot edit any users

    Args:
        request_user: The user making the edit request
        target_user: The user being edited
        requested_role: The role to assign to target_user

    Returns:
        True if the edit is allowed, False otherwise
    """
    target_role = _get_role_value(requested_role)
    request_role = primary_role(request_user)

    # Admin can edit researchers and teachers
    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can edit teachers and students
    if request_role == Role.RESEARCHER:
        if target_role in (Role.TEACHER, Role.STUDENT) and has_sudo_permission(request_user, SudoPermission.EDIT_USER):
            return True

    # Teacher can edit students they own
    if request_role == Role.TEACHER:
        return target_role == Role.STUDENT and teacher_owns_student(request_user, target_user)

    return False


def can_delete_user(request_user: User, target_user: User) -> bool:
    """
    Check if request_user can delete target_user.

    Permission rules:
    - Admins (is_staff) can delete researchers and teachers
    - Researchers with DELETE_USER sudo can delete teachers and students
    - Teachers can delete students they own
    - Students cannot delete any users

    Args:
        request_user: The user making the delete request
        target_user: The user to be deleted

    Returns:
        True if the deletion is allowed, False otherwise
    """
    request_role = primary_role(request_user)
    target_role = primary_role(target_user)

    # Admin can delete researchers and teachers
    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can delete teachers and students
    if request_role == Role.RESEARCHER:
        if target_role in (Role.TEACHER, Role.STUDENT) and has_sudo_permission(request_user, SudoPermission.DELETE_USER):
            return True

    # Teacher can delete students they own
    if request_role == Role.TEACHER:
        return target_role == Role.STUDENT and teacher_owns_student(request_user, target_user)

    return False


def can_reset_password(request_user: User, target_user: User) -> bool:
    """
    Check if request_user can reset target_user's password.

    Permission rules:
    - Admins (is_staff) can reset passwords for researchers, teachers, and students
    - Researchers with RESET_PASSWORD sudo can reset passwords for researchers, teachers, and students

    Args:
        request_user: The user making the reset request
        target_user: The user whose password will be reset

    Returns:
        True if the password reset is allowed, False otherwise
    """
    target_role = primary_role(target_user)

    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER, Role.STUDENT)

    # Sudoed researchers can reset passwords within user space
    if (
        primary_role(request_user) == Role.RESEARCHER
        and has_sudo_permission(request_user, SudoPermission.RESET_PASSWORD)
    ):
        return target_role in (Role.RESEARCHER, Role.TEACHER, Role.STUDENT)

    return False


@transaction.atomic
def create_user_from_payload(
    payload: dict, role_override: str | None = None, creator: User | None = None
) -> User:
    """
    Create a new user from a request payload.

    This is the main entry point for user creation, handling:
    - User record creation with password hashing
    - Role assignment (with optional override for security)
    - Profile creation based on role

    The role_override parameter is used to force a specific role regardless
    of what the payload contains, which is important for public registration
    where we always force STUDENT role.

    Args:
        payload: Dict containing username, name, password, and optionally role
        role_override: If provided, this role is used instead of payload role
        creator: For students, the user creating this account

    Returns:
        The newly created User object
    """
    username = payload.get("username")
    name = payload.get("name")
    password = payload.get("password")
    role = _get_role_value(role_override or payload.get("role") or Role.STUDENT)

    user = User.objects.create_user(username=username, name=name, password=password, is_active=True)
    set_single_role(user, role)
    ensure_profiles_for_role(user, role, creator=creator)
    return user


def link_or_create_oauth_account(user: User, subject: str, email: str) -> OAuthAccount:
    """
    Link a Google OAuth account to a user, or update an existing link.

    This is called during Google OAuth login to associate the Google account
    with the local user account. If the link already exists, it updates the
    email in case it has changed.

    Args:
        user: The local user to link
        subject: The Google account subject ID (unique identifier)
        email: The email from the Google account

    Returns:
        The OAuthAccount linking the user to their Google account
    """
    account, _ = OAuthAccount.objects.update_or_create(
        provider=OAuthProvider.GOOGLE,
        subject=subject,
        defaults={"user": user, "email": email},
    )
    return account


def _can_grant_permissions(granter: User, permissions: list[str], can_grant_sudo: bool) -> tuple[bool, str]:
    """
    Check if granter can grant the specified permissions.

    Permission rules:
    - Admins (is_staff) can grant any permissions and set can_grant_sudo=True
    - Sudoed researchers with can_grant_sudo=True can grant, but:
      - Cannot set can_grant_sudo=True (admin only)
      - Can only grant permissions they hold (subset check)

    Args:
        granter: The user attempting to grant permissions
        permissions: List of SudoPermission values to grant
        can_grant_sudo: Whether to allow the grantee to grant sudo to others

    Returns:
        Tuple of (allowed, error_message). If allowed is True, error_message is empty.
    """
    if granter.is_staff:
        return True, ""

    try:
        granter_grant = granter.sudo_grant
    except SudoGrant.DoesNotExist:
        return False, "Granter does not have sudo permissions"

    if not granter_grant.can_grant_sudo:
        return False, "Granter cannot grant sudo (can_grant_sudo=False)"

    if can_grant_sudo:
        return False, "Only admins can set can_grant_sudo=True"

    # Subset check: granter must hold all permissions being granted
    missing = [p for p in permissions if p not in granter_grant.permissions]
    if missing:
        return False, f"Cannot grant permissions you don't hold: {missing}"

    return True, ""


@transaction.atomic
def grant_sudo_to_researcher(
    granter: User, grantee: User, permissions: list[str], can_grant_sudo: bool = False
) -> SudoGrant:
    """
    Grant sudo permissions to a researcher.

    This function creates or updates a SudoGrant for the grantee, allowing them
    to perform elevated actions. Enforces escalation prevention rules.

    Args:
        granter: The admin or sudoed researcher granting permissions
        grantee: The researcher receiving sudo permissions (must have RESEARCHER role)
        permissions: List of SudoPermission values to grant
        can_grant_sudo: Whether grantee can grant sudo to other researchers (admin only)

    Returns:
        The created or updated SudoGrant

    Raises:
        ValueError: If grantee is not a researcher
        PermissionError: If granter is not authorized or attempting escalation
    """
    # Verify grantee has RESEARCHER role
    grantee_role = primary_role(grantee)
    if grantee_role != Role.RESEARCHER:
        raise ValueError(f"Grantee must have RESEARCHER role, has {grantee_role}")

    # Verify granter is authorized
    allowed, error = _can_grant_permissions(granter, permissions, can_grant_sudo)
    if not allowed:
        raise PermissionError(error)

    # Create or update the SudoGrant
    try:
        grant = grantee.sudo_grant
        # Update existing grant
        grant.permissions = permissions
        grant.can_grant_sudo = can_grant_sudo
        grant.granted_by = granter
    except SudoGrant.DoesNotExist:
        # Create new grant
        grant = SudoGrant(
            user=grantee,
            granted_by=granter,
            permissions=permissions,
            can_grant_sudo=can_grant_sudo,
        )

    # Validate permissions against enum before saving
    grant.full_clean()
    grant.save()
    return grant


@transaction.atomic
def revoke_sudo_grant(revoker: User, grant_id: int) -> None:
    """
    Revoke a sudo grant.

    Args:
        revoker: The admin or sudoed researcher revoking the grant
        grant_id: ID of the SudoGrant to revoke

    Raises:
        ValueError: If grant not found
        PermissionError: If revoker is not authorized to revoke this grant
    """
    try:
        grant = SudoGrant.objects.get(id=grant_id)
    except SudoGrant.DoesNotExist:
        raise ValueError(f"SudoGrant with id {grant_id} not found")

    # Verify revoker is authorized
    if revoker.is_staff:
        # Admin can revoke any grant
        grant.delete()
        return

    # Sudoed researcher can revoke grants they created
    if grant.granted_by_id == revoker.id:
        grant.delete()
        return

    raise PermissionError("You can only revoke grants you created")
