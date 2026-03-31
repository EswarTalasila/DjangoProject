"""Sudo grant management views."""

import sys

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import AuditAction, AuditOutcome


def _v():
    return sys.modules["accounts.views"]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_sudo_grant(request):
    """Return current-user sudo grant permissions for frontend capability gating."""
    v = _v()
    if request.user.is_staff:
        return Response(
            {
                "hasSudo": True,
                "canGrantSudo": True,
                "permissions": [p.value for p in v.SudoPermission],
                "isStaff": True,
            },
            status=status.HTTP_200_OK,
        )

    grant = v.SudoGrant.objects.filter(user=request.user).first()
    if not grant:
        return Response(
            {"hasSudo": False, "canGrantSudo": False, "permissions": [], "isStaff": False},
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "hasSudo": True,
            "canGrantSudo": bool(grant.can_grant_sudo),
            "permissions": grant.permissions,
            "isStaff": False,
        },
        status=status.HTTP_200_OK,
    )


def _list_sudo_grants(request):
    """Return sudo grants visible to the current user."""
    v = _v()
    if request.user.is_staff:
        grants = v.SudoGrant.objects.select_related("user", "granted_by").all()
    else:
        grants = v.SudoGrant.objects.select_related("user", "granted_by").filter(
            granted_by=request.user
        )

    results = [
        {
            "id": g.id,
            "user": {
                "id": g.user.id,
                "username": g.user.username,
                "name": g.user.name or g.user.username,
            },
            "permissions": g.permissions,
            "canGrantSudo": g.can_grant_sudo,
            "grantedAt": g.granted_at.isoformat(),
        }
        for g in grants
    ]
    return Response(results, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([_v().IsResearcherOrAdmin])
def sudo_grants_collection(request):
    """Dispatch GET (list) and POST (grant) for sudo grants."""
    if request.method == "GET":
        return _v()._list_sudo_grants(request)
    return _v()._grant_sudo(request)


def _grant_sudo(request):
    """Grant sudo permissions to a researcher."""
    v = _v()
    user_id = request.data.get("user_id")
    permissions = request.data.get("permissions", [])
    can_grant_sudo_flag = request.data.get("can_grant_sudo", False)

    if not user_id:
        return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    grantee = v.User.objects.filter(id=user_id).first()
    if not grantee:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    audit_id = v.log_audit(
        actor=request.user,
        action=AuditAction.SUDO_GRANT,
        target_user=grantee,
        new_value={"permissions": permissions, "can_grant_sudo": can_grant_sudo_flag},
        ip_address=v.get_client_ip(request),
    )

    try:
        grant = v.grant_sudo_to_researcher(
            granter=request.user,
            grantee=grantee,
            permissions=permissions,
            can_grant_sudo=can_grant_sudo_flag,
        )
        v.complete_audit(audit_id, AuditOutcome.SUCCESS)
        return Response(
            {"message": "Sudo granted", "grant_id": grant.id}, status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        v.complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        v.complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


@api_view(["DELETE"])
@permission_classes([_v().IsResearcherOrAdmin])
def revoke_sudo(request, grant_id: int):
    """Revoke a sudo grant."""
    v = _v()
    grant = v.SudoGrant.objects.filter(id=grant_id).select_related("user").first()
    target_user = grant.user if grant else None
    audit_id = v.log_audit(
        actor=request.user,
        action=AuditAction.SUDO_REVOKE,
        target_user=target_user,
        old_value={"grant_id": grant_id},
        ip_address=v.get_client_ip(request),
    )

    try:
        v.revoke_sudo_grant(revoker=request.user, grant_id=grant_id)
        v.complete_audit(audit_id, AuditOutcome.SUCCESS)
        return Response(status=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        v.complete_audit(audit_id, AuditOutcome.FAILURE)
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except PermissionError as e:
        v.complete_audit(audit_id, AuditOutcome.DENIED)
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
