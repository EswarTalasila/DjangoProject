"""User management views: CRUD operations for user accounts."""

import sys

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.models import AuditAction, AuditOutcome


def _v():
    return sys.modules["accounts.views"]


@api_view(["POST"])
@permission_classes([_v().IsTeacherOrAbove])
def create_user(request):
    """Create a new user account with specified role (privileged operation)."""
    v = _v()
    serializer = v.UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if "username" in request.data:
        return Response(
            {"detail": v.USERNAME_IMMUTABLE_DETAIL},
            status=status.HTTP_400_BAD_REQUEST,
        )
    payload = serializer.validated_data
    if not payload.get("name"):
        return Response({"detail": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
    requested_role = payload.get("role") or v.Role.STUDENT
    if not v.can_create_user(request.user, requested_role):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if requested_role != v.Role.STUDENT and not payload.get("email"):
        return Response(
            {"detail": "email is required for non-student users"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if payload.get("email") and v.identifier_in_use(payload.get("email")):
        return Response({"detail": "Email already taken"}, status=status.HTTP_409_CONFLICT)
    create_payload = dict(payload)
    create_payload["username"] = v.generate_managed_username(name=payload["name"])
    try:
        user = v.create_user_from_payload(
            create_payload,
            role_override=requested_role,
            creator=request.user,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(v.UserOutputSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([_v().IsTeacherOrAbove])
def manage_user(request, user_id: int):
    """Update or delete an existing user account."""
    if request.method == "DELETE":
        return _v()._delete_user(request, user_id)
    return _v()._edit_user(request, user_id)


def _edit_user(request, user_id: int):
    """Update an existing user's profile, role, or password."""
    v = _v()
    serializer = v.UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    user = v.User.objects.filter(id=user_id).first()
    if not user:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    requested_role = payload.get("role") or v.primary_role(user)
    if not v.can_edit_user(request.user, user, requested_role):
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    next_email = user.email

    if payload.get("name"):
        user.name = payload["name"]

    if "username" in payload:
        return Response(
            {"detail": "Usernames are system-managed and immutable."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "email" in payload:
        incoming_email = payload.get("email")
        normalized_email = v.normalize_username_identifier(incoming_email) if incoming_email else None
        if normalized_email and v.identifier_in_use(normalized_email, exclude_user_id=user_id):
            return Response({"detail": "Email already taken"}, status=status.HTTP_409_CONFLICT)
        next_email = normalized_email
        user.email = normalized_email

    if requested_role != v.Role.STUDENT and not next_email:
        return Response(
            {"detail": "email is required for non-student users"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_role = v.primary_role(user)
    role_changing = payload.get("role") and str(payload["role"]) != str(old_role)
    audit_id = None
    if role_changing:
        audit_id = v.log_audit(
            actor=request.user,
            action=AuditAction.ROLE_CHANGE,
            target_user=user,
            old_value={"role": str(old_role)},
            new_value={"role": str(payload["role"])},
            ip_address=v.get_client_ip(request),
        )

    if payload.get("password"):
        user.set_password(payload["password"])
    user.save()
    if payload.get("role"):
        v.set_single_role(user, payload["role"])
        v.ensure_profiles_for_role(user, payload["role"], creator=request.user)

    if audit_id is not None:
        v.complete_audit(audit_id, AuditOutcome.SUCCESS)

    user.refresh_from_db()
    user._cached_role_set = None
    return Response(v.UserOutputSerializer(user).data, status=status.HTTP_200_OK)


def _delete_user(request, user_id: int):
    """Permanently delete a user account by ID."""
    v = _v()
    user = v.User.objects.filter(id=user_id).first()
    if not user:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    if not v.can_delete_user(request.user, user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    audit_id = v.log_audit(
        actor=request.user,
        action=AuditAction.USER_DELETE,
        target_user=user,
        old_value={"username": user.username, "role": str(v.primary_role(user))},
        ip_address=v.get_client_ip(request),
    )
    user.delete()
    v.complete_audit(audit_id, AuditOutcome.SUCCESS)
    return Response(status=status.HTTP_204_NO_CONTENT)
