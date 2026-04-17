"""Shared lifecycle helpers for FR-14 archival operations."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from accounts.models import User


class LifecycleStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class ConflictError(Exception):
    """Raised when a lifecycle transition conflicts with current state."""

    pass


def archive_entity(entity, user: User) -> None:
    """Set entity status to ARCHIVED with metadata. Caller must save."""
    if entity.status == LifecycleStatus.ARCHIVED:
        raise ConflictError("Entity is already archived.")
    entity.status = LifecycleStatus.ARCHIVED
    entity.archived_at = timezone.now()
    entity.archived_by = user


def restore_entity(entity, user: User) -> None:
    """Set entity status to ACTIVE with restore metadata. Caller must save."""
    if entity.status != LifecycleStatus.ARCHIVED:
        raise ConflictError("Entity is not archived.")
    entity.status = LifecycleStatus.ACTIVE
    entity.archived_at = None
    entity.archived_by = None
    entity.restored_at = timezone.now()
    entity.restored_by = user
