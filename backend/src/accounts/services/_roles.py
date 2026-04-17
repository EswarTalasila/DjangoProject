"""Role management, permissions, and user CRUD."""

from django.db import transaction

from core.permissions import has_sudo_permission, primary_role
from courses.models import Enrollment

from ..models import (
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from ._utils import normalize_username_identifier


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
    except ValueError as err:
        valid_roles = [r.value for r in Role]
        raise ValueError(f"Invalid role '{role}'. Must be one of: {valid_roles}") from err


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
        if role == Role.TEACHER and has_sudo_permission(
            request_user, SudoPermission.CREATE_TEACHER
        ):
            return True
        if role == Role.STUDENT and has_sudo_permission(
            request_user, SudoPermission.CREATE_STUDENT
        ):
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
    # Admin/staff accounts are not editable through role-assignment flows.
    if target_user.is_staff:
        return False

    try:
        target_role = _get_role_value(requested_role)
    except ValueError:
        return False
    request_role = primary_role(request_user)

    # Admin can edit researchers and teachers
    if request_user.is_staff:
        return target_role in (Role.RESEARCHER, Role.TEACHER)

    # Researcher with sudo can edit teachers and students
    if (
        request_role == Role.RESEARCHER
        and target_role
        in (
            Role.TEACHER,
            Role.STUDENT,
        )
        and has_sudo_permission(request_user, SudoPermission.EDIT_USER)
    ):
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
    if (
        request_role == Role.RESEARCHER
        and target_role
        in (
            Role.TEACHER,
            Role.STUDENT,
        )
        and has_sudo_permission(request_user, SudoPermission.DELETE_USER)
    ):
        return True

    # Teacher can delete students they own
    if request_role == Role.TEACHER:
        return target_role == Role.STUDENT and teacher_owns_student(request_user, target_user)

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
    username = normalize_username_identifier(payload.get("username", ""))
    raw_email = payload.get("email")
    email = normalize_username_identifier(raw_email) if raw_email else None
    name = payload.get("name")
    password = payload.get("password")
    role = _get_role_value(role_override or payload.get("role") or Role.STUDENT)

    if role != Role.STUDENT and not email:
        raise ValueError("email is required for non-student users")

    user = User.objects.create_user(
        username=username,
        email=email,
        name=name,
        password=password,
        is_active=True,
    )
    set_single_role(user, role)
    ensure_profiles_for_role(user, role, creator=creator)
    return user
