"""
Shared permission helpers for role-based access control.

This module provides DRF permission classes and helper functions for
enforcing role-based access control across API endpoints.

Role Hierarchy (highest to lowest privilege):
    ADMIN > TEACHER > STUDENT

Permission Classes (use with @permission_classes decorator):
    IsAdmin: Restricts to admin users only
    IsTeacher: Restricts to teacher users only
    IsTeacherOrAdmin: Restricts to teachers or admins

Helper Functions (for custom permission logic in views):
    primary_role(user): Get user's highest-privilege role
    has_role(user, role): Check if user has specific role
    has_any_role(user, roles): Check if user has any of the roles

Usage:
    from core.permissions import IsTeacherOrAdmin, primary_role

    @api_view(["GET"])
    @permission_classes([IsTeacherOrAdmin])
    def my_view(request):
        if primary_role(request.user) == Role.ADMIN:
            # Admin-specific logic
            pass
"""

from collections.abc import Iterable

from rest_framework import permissions

from accounts.models import Role


def _role_set(user) -> set[str]:
    """
    Return the authenticated user's set of assigned roles.

    Args:
        user: User instance or None

    Returns:
        Set of role strings (e.g., {"ADMIN", "TEACHER"}) or empty set
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.roles.values_list("role", flat=True))


def primary_role(user) -> str:
    """
    Return the user's primary (highest-privilege) role.

    Checks roles in order of privilege: ADMIN > TEACHER > STUDENT.
    Returns the first matching role, or STUDENT as fallback.

    Args:
        user: User instance

    Returns:
        Role string (ADMIN, TEACHER, or STUDENT)
    """
    roles = _role_set(user)
    for role in (Role.ADMIN, Role.TEACHER, Role.STUDENT):
        if role in roles:
            return role
    return Role.STUDENT


def has_role(user, role: str) -> bool:
    """
    Check if the user has a specific role.

    Args:
        user: User instance
        role: Role to check for (e.g., Role.ADMIN)

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
        return has_role(request.user, Role.ADMIN)


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
    DRF permission class allowing access to teachers or admins.

    This is the most common permission for management endpoints where
    both teachers and admins should have access.

    Usage:
        @permission_classes([IsTeacherOrAdmin])
        def management_view(request):
            ...
    """

    def has_permission(self, request, view):
        """Return True if request user is a teacher or admin."""
        return has_any_role(request.user, (Role.ADMIN, Role.TEACHER))
