"""Pure unit tests for core.lifecycle (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestArchiveEntity:

    @patch("core.lifecycle.timezone")
    def test_archives_active_entity(self, mock_tz):
        """archive_entity sets status to ARCHIVED and records timestamp and actor."""
        from core.lifecycle import LifecycleStatus, archive_entity

        mock_tz.now.return_value = "2025-01-01T00:00:00Z"
        entity = SimpleNamespace(
            status=LifecycleStatus.ACTIVE,
            archived_at=None,
            archived_by=None,
        )
        user = SimpleNamespace(id=1)

        archive_entity(entity, user)

        assert entity.status == LifecycleStatus.ARCHIVED
        assert entity.archived_at == "2025-01-01T00:00:00Z"
        assert entity.archived_by is user

    def test_raises_when_already_archived(self):
        """archive_entity raises ConflictError when entity is already archived."""
        from core.lifecycle import ConflictError, LifecycleStatus, archive_entity

        entity = SimpleNamespace(status=LifecycleStatus.ARCHIVED)
        user = SimpleNamespace(id=1)

        with pytest.raises(ConflictError, match="already archived"):
            archive_entity(entity, user)


class TestRestoreEntity:

    @patch("core.lifecycle.timezone")
    def test_restores_archived_entity(self, mock_tz):
        """restore_entity resets status to ACTIVE and clears archive metadata."""
        from core.lifecycle import LifecycleStatus, restore_entity

        mock_tz.now.return_value = "2025-06-01T00:00:00Z"
        entity = SimpleNamespace(
            status=LifecycleStatus.ARCHIVED,
            archived_at="2025-01-01",
            archived_by=SimpleNamespace(id=1),
            restored_at=None,
            restored_by=None,
        )
        user = SimpleNamespace(id=2)

        restore_entity(entity, user)

        assert entity.status == LifecycleStatus.ACTIVE
        assert entity.archived_at is None
        assert entity.archived_by is None
        assert entity.restored_at == "2025-06-01T00:00:00Z"
        assert entity.restored_by is user

    def test_raises_when_not_archived(self):
        """restore_entity raises ConflictError when entity is not archived."""
        from core.lifecycle import ConflictError, LifecycleStatus, restore_entity

        entity = SimpleNamespace(status=LifecycleStatus.ACTIVE)
        user = SimpleNamespace(id=1)

        with pytest.raises(ConflictError, match="not archived"):
            restore_entity(entity, user)
