"""
Shared permission helpers for role-based access control.

This module provides DRF permission classes and helper functions for
enforcing role-based access control across API endpoints.

Role Hierarchy (highest to lowest privilege):
    RESEARCHER > TEACHER > STUDENT

Permission Classes (use with @permission_classes decorator):
    IsAdmin: Restricts to admin users only (is_staff)
    IsResearcher: Restricts to researcher users only
    IsResearcherOrAdmin: Restricts to researchers or admins
    IsTeacher: Restricts to teacher users only
    IsTeacherOrAbove: Restricts to teachers, researchers, or admins

Helper Functions (for custom permission logic in views):
    primary_role(user): Get user's highest-privilege role
    has_role(user, role): Check if user has specific role
    has_any_role(user, roles): Check if user has any of the roles
    has_sudo_permission(user, permission): Check if user has sudo permission

Usage:
    from core.permissions import IsTeacherOrAdmin, primary_role

    @api_view(["GET"])
    @permission_classes([IsTeacherOrAdmin])
    def my_view(request):
        if request.user.is_staff:
            # Admin-specific logic
            pass
"""

from collections.abc import Iterable

from rest_framework import permissions

from accounts.models import Role


def _role_set(user) -> set[str]:
    """
    Return the authenticated user's set of assigned roles.

    Results are cached on the user object for the duration of the request
    to avoid repeated identical queries when multiple permission checks
    call has_role() or primary_role() on the same user.

    Args:
        user: User instance or None

    Returns:
        Set of role strings (e.g., {"RESEARCHER", "TEACHER"}) or empty set
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    cached: set[str] | None = getattr(user, "_cached_role_set", None)
    if cached is not None:
        return cached
    roles: set[str] = set(user.roles.values_list("role", flat=True))
    user._cached_role_set = roles
    return roles


def primary_role(user) -> str:
    """
    Return the user's primary (highest-privilege) role.

    Checks roles in order of privilege: RESEARCHER > TEACHER > STUDENT.
    Returns the first matching role, or STUDENT as fallback.

    Args:
        user: User instance

    Returns:
        Role string (ADMIN for is_staff users, otherwise RESEARCHER/TEACHER/STUDENT)
    """

    if user.is_staff:
        return "ADMIN"

    roles = _role_set(user)
    for role in (Role.RESEARCHER, Role.TEACHER, Role.STUDENT):
        if role in roles:
            return role
    return Role.STUDENT


def has_role(user, role: str) -> bool:
    """
    Check if the user has a specific role.

    Args:
        user: User instance
        role: Role to check for (e.g., Role.RESEARCHER)

    Returns:
        True if user has the role, False otherwise
    """
    return role in _role_set(user)


def has_any_role(user, roles: Iterable[str]) -> bool:
    """
    Check if the user has any of the specified roles.

    Args:
        user: User instance
        roles: Iterable of role strings to check

    Returns:
        True if user has at least one of the roles
    """
    role_set = _role_set(user)
    return any(role in role_set for role in roles)


def has_sudo_permission(user, permission: str) -> bool:
    """
    Check if user is a sudoed researcher with the given permission.

    A user has sudo permission if they have a SudoGrant record and the
    specific permission is in their permissions list.

    Args:
        user: User instance to check
        permission: SudoPermission value (e.g., "CREATE_TEACHER")

    Returns:
        True if user has the sudo permission, False otherwise

    Example:
        from accounts.models import SudoPermission
        if has_sudo_permission(user, SudoPermission.CREATE_TEACHER):
            # Allow creating teachers
    """
    try:
        sudo_grant = user.sudo_grant
        return permission in sudo_grant.permissions
    except AttributeError:
        return False


class IsAdmin(permissions.BasePermission):
    """
    DRF permission class restricting access to admin users only.

    Usage:
        @permission_classes([IsAdmin])
        def admin_only_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is an admin."""
        return request.user.is_staff


class IsResearcher(permissions.BasePermission):
    """
    DRF permission class restricting access to researcher users only.

    Usage:
        @permission_classes([IsResearcher])
        def researcher_only_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a researcher."""
        return has_role(request.user, Role.RESEARCHER)


class IsResearcherOrAdmin(permissions.BasePermission):
    """
    DRF permission class allowing access to researchers or admins.

    Usage:
        @permission_classes([IsResearcherOrAdmin])
        def research_management_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a researcher or admin."""
        return request.user.is_staff or has_role(request.user, Role.RESEARCHER)


class IsTeacher(permissions.BasePermission):
    """
    DRF permission class restricting access to teacher users only.

    Usage:
        @permission_classes([IsTeacher])
        def teacher_only_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a teacher."""
        return has_role(request.user, Role.TEACHER)


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    DRF permission class allowing access to teachers or admins only.

    Used for user management endpoints where teachers manage their students
    and admins have full access. Does not include researchers.

    Usage:
        @permission_classes([IsTeacherOrAdmin])
        def user_management_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a teacher or admin."""
        return request.user.is_staff or has_role(request.user, Role.TEACHER)


class IsTeacherOrAbove(permissions.BasePermission):
    """
    DRF permission class allowing access to teachers, researchers, or admins.

    This is the most common permission for management endpoints where
    teachers need access and higher-privilege roles should also have access.
    Follows the role hierarchy: ADMIN (is_staff) > RESEARCHER > TEACHER > STUDENT.

    Usage:
        @permission_classes([IsTeacherOrAbove])
        def management_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a teacher, researcher, or admin."""
        return (
            request.user.is_staff
            or has_role(request.user, Role.RESEARCHER)
            or has_role(request.user, Role.TEACHER)
        )


# ── Reusable ownership checks ─────────────────────────────────────────


def teacher_owns_course(user, course) -> bool:
    """
    Check if a teacher user owns the given course.

    Returns True if the course's teacher_profile matches the user's
    teacher_profile. Returns False if either lacks a teacher profile.

    Args:
        user: User instance to check ownership for
        course: Course instance (must have teacher_profile relation)

    Returns:
        True if the user owns the course, False otherwise
    """
    try:
        return course.teacher_profile_id == user.teacher_profile.id
    except AttributeError:
        return False


def teacher_owns_assignment(user, assignment) -> bool:
    """
    Check if a teacher user owns the given assignment.

    Ownership is determined by either:
    1. The assignment's teacher_id matches the user's ID, OR
    2. The assignment's course belongs to the user's teacher profile

    Args:
        user: User instance to check ownership for
        assignment: Assignment instance (should be select_related with
            course__teacher_profile__user for efficiency)

    Returns:
        True if the user owns the assignment, False otherwise
    """
    if assignment.teacher_id == user.id:
        return True
    if assignment.course and assignment.course.teacher_profile:
        return bool(assignment.course.teacher_profile.user_id == user.id)
    return False
