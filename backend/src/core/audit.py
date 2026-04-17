"""Two-phase audit logging for sensitive actions (OBS-CN-08)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

from .models import AuditLog, AuditOutcome

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str | None:
    """Extract client IP from request META."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(
    *,
    actor: AbstractUser,
    action: str,
    target_user: AbstractUser | None = None,
    target_resource_type: str | None = None,
    target_resource_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> int | None:
    """Phase 1: insert audit entry with outcome=PENDING.

    Returns the entry ID for phase-2 update, or None if the write failed.
    Failures are logged but never block the calling action.
    """
    try:
        entry = AuditLog.objects.create(
            actor=actor,
            action=action,
            target_user=target_user,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            old_value=old_value,
            new_value=new_value,
            outcome=AuditOutcome.PENDING,
            ip_address=ip_address,
        )
        return entry.id
    except Exception:
        logger.exception("Audit log intent write failed for action=%s", action)
        return None


def complete_audit(entry_id: int | None, outcome: str) -> None:
    """Phase 2: update audit entry outcome to SUCCESS / FAILURE / DENIED.

    If entry_id is None (phase 1 failed), this is a no-op.
    Update failures are logged but never block the calling action.
    """
    if entry_id is None:
        return
    try:
        AuditLog.objects.filter(id=entry_id).update(outcome=outcome)
    except Exception:
        logger.exception("Audit log outcome update failed for entry=%s", entry_id)
