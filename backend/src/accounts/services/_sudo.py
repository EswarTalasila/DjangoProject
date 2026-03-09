"""Sudo grant and revoke operations for researchers."""

from django.db import transaction

from core.permissions import primary_role

from ..models import Role, SudoGrant, SudoPermission, User

NON_DELEGABLE_PERMISSIONS = {
    SudoPermission.ISSUE_RESEARCHER_REG_CODE.value,
}


def _can_grant_permissions(
    granter: User, permissions: list[str], can_grant_sudo: bool
) -> tuple[bool, str]:
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

    non_delegable = [p for p in permissions if p in NON_DELEGABLE_PERMISSIONS]
    if non_delegable:
        return False, f"Cannot delegate non-delegable permissions: {non_delegable}"

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
    except SudoGrant.DoesNotExist as err:
        raise ValueError(f"SudoGrant with id {grant_id} not found") from err

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
