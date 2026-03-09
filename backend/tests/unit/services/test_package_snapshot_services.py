"""Unit tests for packages.services._snapshots — snapshot lifecycle services.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, mock_open

import pytest
from django.utils import timezone

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _patch_transaction_atomic(monkeypatch):
    monkeypatch.setattr("django.db.transaction.Atomic.__enter__", lambda self: None)
    monkeypatch.setattr("django.db.transaction.Atomic.__exit__", lambda self, exc_type, exc, tb: False)
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, using=None: func())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user():
    u = MagicMock()
    u.id = 1
    u.is_staff = False
    return u


def _workspace():
    ws = MagicMock()
    ws.id = 10
    return ws


# ---------------------------------------------------------------------------
# create_snapshot — ROSTER binding
# ---------------------------------------------------------------------------

class TestCreateSnapshotRoster:
    @patch("packages.services._snapshots.PackageAuditLog.objects.create")
    @patch("packages.services._snapshots.DataSnapshot.objects.create")
    @patch("packages.services._snapshots.export_roster")
    @patch("packages.services._snapshots.resolve_anonymization", return_value=(False, None))
    @patch("packages.services._snapshots.Course.objects.get")
    @patch("packages.services._snapshots.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_roster_snapshot_success(self, m_open, m_makedirs, m_course_get,
                                      m_resolve, m_export, m_snap_create, m_audit):
        """Roster snapshot exports CSV data, marks status READY, and logs audit."""
        from packages.services._snapshots import create_snapshot

        mock_course = MagicMock()
        mock_course.name = "CS101"
        m_course_get.return_value = mock_course

        csv_data = b"col1,col2\nval1,val2\n"
        m_export.return_value = (iter([csv_data]), 1, False)

        mock_snap = MagicMock()
        mock_snap.id = 100
        mock_snap.filters = None
        mock_snap.include_answers = False
        mock_snap.dataset_binding = "ROSTER"
        mock_snap.scope_course_id = 5
        m_snap_create.return_value = mock_snap

        result = create_snapshot(
            _user(), _workspace(),
            dataset_binding="ROSTER",
            scope_course_id=5,
            identifiable=False,
        )
        assert result == mock_snap
        mock_snap.save.assert_called()
        assert mock_snap.status == "READY"
        assert mock_snap.row_count == 1
        m_audit.assert_called_once()


# ---------------------------------------------------------------------------
# create_snapshot — COURSE_SUBMISSIONS binding
# ---------------------------------------------------------------------------

class TestCreateSnapshotSubmissions:
    @patch("packages.services._snapshots.PackageAuditLog.objects.create")
    @patch("packages.services._snapshots.DataSnapshot.objects.create")
    @patch("packages.services._snapshots.export_course_submissions")
    @patch("packages.services._snapshots.resolve_anonymization", return_value=(True, None))
    @patch("packages.services._snapshots.Course.objects.get")
    @patch("packages.services._snapshots.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_submissions_snapshot_success(self, m_open, m_makedirs, m_course_get,
                                           m_resolve, m_export, m_snap_create, m_audit):
        """Course submissions snapshot exports data with filters and answers."""
        from packages.services._snapshots import create_snapshot

        mock_course = MagicMock()
        mock_course.name = "CS202"
        m_course_get.return_value = mock_course

        csv_data = b"data\n"
        m_export.return_value = (iter([csv_data]), 5, True)

        mock_snap = MagicMock()
        mock_snap.id = 200
        mock_snap.filters = {"startDate": "2025-01-01"}
        mock_snap.include_answers = True
        mock_snap.dataset_binding = "COURSE_SUBMISSIONS"
        mock_snap.scope_course_id = 10
        m_snap_create.return_value = mock_snap

        result = create_snapshot(
            _user(), _workspace(),
            dataset_binding="COURSE_SUBMISSIONS",
            scope_course_id=10,
            filters={"startDate": "2025-01-01"},
            include_answers=True,
            identifiable=True,
        )
        assert result == mock_snap
        assert mock_snap.row_count == 5


# ---------------------------------------------------------------------------
# create_snapshot — unsupported binding
# ---------------------------------------------------------------------------

class TestCreateSnapshotUnsupported:
    @patch("packages.services._snapshots.PackageAuditLog.objects.create")
    @patch("packages.services._snapshots.DataSnapshot.objects.create")
    @patch("packages.services._snapshots.resolve_anonymization", return_value=(False, None))
    def test_unsupported_binding_raises(self, m_resolve, m_snap_create, m_audit):
        """Unsupported dataset binding raises ValueError and marks snapshot FAILED."""
        from packages.services._snapshots import create_snapshot

        mock_snap = MagicMock()
        mock_snap.id = 300
        mock_snap.dataset_binding = "UNKNOWN"
        mock_snap.scope_course_id = None
        mock_snap.filters = None
        mock_snap.include_answers = False
        m_snap_create.return_value = mock_snap

        with pytest.raises(ValueError, match="Unsupported dataset binding"):
            create_snapshot(
                _user(), _workspace(),
                dataset_binding="UNKNOWN",
            )
        # Should mark snapshot as FAILED
        assert mock_snap.status == "FAILED"


# ---------------------------------------------------------------------------
# create_snapshot — anonymization error
# ---------------------------------------------------------------------------

class TestCreateSnapshotPermError:
    @patch("packages.services._snapshots.resolve_anonymization", return_value=(False, "EXPORT_IDENTIFIABLE permission required"))
    def test_permission_error(self, m_resolve):
        """Identifiable export without permission raises PermissionError."""
        from packages.services._snapshots import create_snapshot
        with pytest.raises(PermissionError, match="EXPORT_IDENTIFIABLE"):
            create_snapshot(
                _user(), _workspace(),
                dataset_binding="ROSTER",
                identifiable=True,
            )


# ---------------------------------------------------------------------------
# list_snapshots
# ---------------------------------------------------------------------------

class TestListSnapshots:
    @patch("packages.services._snapshots.DataSnapshot.objects")
    def test_list_snapshots(self, mock_objs):
        """Listing snapshots returns non-expired snapshots ordered by creation."""
        from packages.services._snapshots import list_snapshots

        # Setup filter chain
        mock_qs = MagicMock()
        mock_objs.filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.update.return_value = 0

        # Second filter chain for the actual listing
        mock_list_qs = MagicMock()
        mock_objs.filter.return_value = mock_list_qs
        mock_list_qs.filter.return_value = mock_list_qs
        mock_list_qs.exclude.return_value = mock_list_qs
        mock_list_qs.order_by.return_value = ["snap1", "snap2"]

        ws = _workspace()
        result = list_snapshots(ws)
        assert result == ["snap1", "snap2"]


# ---------------------------------------------------------------------------
# expire_snapshot
# ---------------------------------------------------------------------------

class TestExpireSnapshot:
    @patch("packages.services._snapshots.os.path.exists", return_value=True)
    @patch("packages.services._snapshots.os.remove")
    def test_expire_deletes_file(self, mock_remove, mock_exists):
        """Expiring a snapshot deletes its storage file and sets status to EXPIRED."""
        from packages.services._snapshots import expire_snapshot
        snap = MagicMock()
        snap.storage_key = "/tmp/snap-1.csv"
        expire_snapshot(snap)
        assert snap.status == "EXPIRED"
        snap.save.assert_called_once()
        mock_remove.assert_called_once_with("/tmp/snap-1.csv")

    @patch("packages.services._snapshots.os.path.exists", return_value=False)
    def test_expire_no_file(self, mock_exists):
        """Expiring a snapshot with missing file still sets status to EXPIRED."""
        from packages.services._snapshots import expire_snapshot
        snap = MagicMock()
        snap.storage_key = "/tmp/snap-2.csv"
        expire_snapshot(snap)
        assert snap.status == "EXPIRED"

    def test_expire_no_storage_key(self):
        """Expiring a snapshot with empty storage_key still sets status to EXPIRED."""
        from packages.services._snapshots import expire_snapshot
        snap = MagicMock()
        snap.storage_key = ""
        expire_snapshot(snap)
        assert snap.status == "EXPIRED"


# ---------------------------------------------------------------------------
# cleanup_expired_snapshots
# ---------------------------------------------------------------------------

class TestCleanupExpiredSnapshots:
    @patch("packages.services._snapshots.DataSnapshot.objects.filter")
    def test_cleanup_deletes_files(self, mock_filter):
        """Cleanup expires snapshots and deletes their storage files."""
        from packages.services._snapshots import cleanup_expired_snapshots

        snap1 = MagicMock()
        snap1.storage_key = "/tmp/snap-a.csv"
        snap2 = MagicMock()
        snap2.storage_key = "/tmp/snap-b.csv"

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = [snap1, snap2]

        with patch("packages.services._snapshots.os.path.exists", return_value=True), \
             patch("packages.services._snapshots.os.remove") as mock_remove:
            result = cleanup_expired_snapshots()

        assert result["snapshotsExpired"] == 2
        assert result["filesDeleted"] == 2
        assert snap1.status == "EXPIRED"
        assert snap2.status == "EXPIRED"

    @patch("packages.services._snapshots.DataSnapshot.objects.filter")
    def test_cleanup_handles_missing_file(self, mock_filter):
        """Cleanup handles OSError when deleting a storage file gracefully."""
        from packages.services._snapshots import cleanup_expired_snapshots

        snap = MagicMock()
        snap.storage_key = "/tmp/missing.csv"

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = [snap]

        with patch("packages.services._snapshots.os.path.exists", return_value=True), \
             patch("packages.services._snapshots.os.remove", side_effect=OSError("gone")):
            result = cleanup_expired_snapshots()

        assert result["snapshotsExpired"] == 1
        assert result["filesDeleted"] == 0

    @patch("packages.services._snapshots.DataSnapshot.objects.filter")
    def test_cleanup_no_expired(self, mock_filter):
        """Cleanup with no expired snapshots returns zero counts."""
        from packages.services._snapshots import cleanup_expired_snapshots

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = []

        result = cleanup_expired_snapshots()
        assert result["snapshotsExpired"] == 0
        assert result["filesDeleted"] == 0

    @patch("packages.services._snapshots.DataSnapshot.objects.filter")
    def test_cleanup_no_storage_key(self, mock_filter):
        """Cleanup skips file deletion for snapshots with empty storage_key."""
        from packages.services._snapshots import cleanup_expired_snapshots

        snap = MagicMock()
        snap.storage_key = ""

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = [snap]

        result = cleanup_expired_snapshots()
        assert result["snapshotsExpired"] == 1
        assert result["filesDeleted"] == 0
