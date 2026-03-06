"""Unit tests for packages.services._build — build pipeline services.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, mock_open, PropertyMock

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
    u.is_staff = True
    return u


def _workspace(id=10, name="WS", revision=1):
    ws = MagicMock()
    ws.id = id
    ws.name = name
    ws.revision = revision
    return ws


def _job(id=1, workspace=None, user=None, strict_mode=False, snapshot_id=None,
         mode="live"):
    j = MagicMock()
    j.id = id
    j.workspace = workspace or _workspace()
    j.created_by = user or _user()
    j.strict_mode = strict_mode
    j.snapshot_id = snapshot_id
    j.mode = mode
    j.status = "QUEUED"
    j.started_at = None
    j.completed_at = None
    j.error_message = ""
    j.warnings = []
    j.save = MagicMock()
    return j


def _node(id, label="f.csv", node_type="FILE", parent_id=None, source_type="LIVE",
          dataset_binding="ROSTER", binding_course_id=1, snapshot=None,
          filters=None, include_answers=False, identifiable=False):
    return SimpleNamespace(
        id=id,
        label=label,
        node_type=node_type,
        parent_id=parent_id,
        source_type=source_type,
        dataset_binding=dataset_binding,
        binding_course_id=binding_course_id,
        snapshot=snapshot,
        filters=filters,
        include_answers=include_answers,
        identifiable=identifiable,
    )


def _mock_validation_result(valid=True, violations=None, warnings=None):
    vr = MagicMock()
    vr.valid = valid
    vr.violations = violations or []
    vr.warnings = warnings or []
    return vr


# ---------------------------------------------------------------------------
# _read_snapshot_bytes
# ---------------------------------------------------------------------------

class TestReadSnapshotBytes:
    def test_expired_by_time(self):
        """Snapshot past its expiration time raises ValueError and is marked expired."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 1
        snap.expires_at = timezone.now() - timedelta(hours=1)
        snap.status = "READY"
        with pytest.raises(ValueError, match="has expired"):
            _read_snapshot_bytes(snap)
        assert snap.status == "EXPIRED"

    def test_expired_status(self):
        """Snapshot with EXPIRED status raises ValueError even if not past expiry time."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 2
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "EXPIRED"
        with pytest.raises(ValueError, match="has expired"):
            _read_snapshot_bytes(snap)

    def test_failed_status(self):
        """Snapshot with FAILED status raises ValueError."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 3
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "FAILED"
        snap.error_message = "bad data"
        with pytest.raises(ValueError, match="failed"):
            _read_snapshot_bytes(snap)

    def test_not_ready_status(self):
        """Snapshot with non-READY status (e.g. QUEUED) raises ValueError."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 4
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "QUEUED"
        with pytest.raises(ValueError, match="not ready"):
            _read_snapshot_bytes(snap)

    @patch("packages.services._build.os.path.exists", return_value=False)
    def test_missing_file(self, mock_exists):
        """Snapshot whose storage file does not exist on disk raises ValueError."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 5
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "READY"
        snap.storage_key = "/tmp/missing.csv"
        with pytest.raises(ValueError, match="file missing"):
            _read_snapshot_bytes(snap)

    def test_no_storage_key(self):
        """Snapshot with empty storage_key raises ValueError."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 6
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "READY"
        snap.storage_key = ""
        with pytest.raises(ValueError, match="file missing"):
            _read_snapshot_bytes(snap)

    @patch("builtins.open", mock_open(read_data=b"csv,data"))
    @patch("packages.services._build.os.path.exists", return_value=True)
    def test_reads_file_successfully(self, mock_exists):
        """Valid READY snapshot returns its file contents as bytes."""
        from packages.services._build import _read_snapshot_bytes
        snap = MagicMock()
        snap.id = 7
        snap.expires_at = timezone.now() + timedelta(hours=1)
        snap.status = "READY"
        snap.storage_key = "/tmp/snap-7.csv"
        result = _read_snapshot_bytes(snap)
        assert result == b"csv,data"


# ---------------------------------------------------------------------------
# _materialize_node — SNAPSHOT source
# ---------------------------------------------------------------------------

class TestMaterializeNodeSnapshot:
    @patch("packages.services._build._read_snapshot_bytes", return_value=b"snap-data")
    def test_snapshot_source(self, mock_read):
        """Snapshot-sourced node delegates to _read_snapshot_bytes and returns data."""
        from packages.services._build import _materialize_node
        snap = MagicMock()
        node = _node(1, source_type="SNAPSHOT", snapshot=snap)
        result = _materialize_node(node, _user())
        assert result == b"snap-data"
        mock_read.assert_called_once_with(snap)

    def test_snapshot_source_no_snapshot_linked(self):
        """Snapshot-sourced node with no linked snapshot raises ValueError."""
        from packages.services._build import _materialize_node
        node = _node(1, source_type="SNAPSHOT", snapshot=None)
        with pytest.raises(ValueError, match="no snapshot linked"):
            _materialize_node(node, _user())


# ---------------------------------------------------------------------------
# _materialize_node — LIVE source ROSTER
# ---------------------------------------------------------------------------

class TestMaterializeNodeLiveRoster:
    @patch("packages.services._build.Course.objects.get")
    @patch("packages.services._build.export_roster")
    @patch("packages.services._build.resolve_anonymization", return_value=(True, None))
    def test_live_roster(self, mock_anon, mock_export, mock_course_get):
        """Live ROSTER node exports and concatenates roster CSV chunks."""
        from packages.services._build import _materialize_node
        mock_course_get.return_value = MagicMock()
        mock_export.return_value = (iter([b"header\n", b"row\n"]), 1, False)
        node = _node(1, source_type="LIVE", dataset_binding="ROSTER", binding_course_id=5)
        result = _materialize_node(node, _user())
        assert result == b"header\nrow\n"


# ---------------------------------------------------------------------------
# _materialize_node — LIVE source COURSE_SUBMISSIONS
# ---------------------------------------------------------------------------

class TestMaterializeNodeLiveSubmissions:
    @patch("packages.services._build.Course.objects.get")
    @patch("packages.services._build.export_course_submissions")
    @patch("packages.services._build.resolve_anonymization", return_value=(False, None))
    def test_live_submissions(self, mock_anon, mock_export, mock_course_get):
        """Live COURSE_SUBMISSIONS node exports submission data with filters."""
        from packages.services._build import _materialize_node
        mock_course_get.return_value = MagicMock()
        mock_export.return_value = (iter([b"data\n"]), 3, True)
        node = _node(1, source_type="LIVE", dataset_binding="COURSE_SUBMISSIONS",
                      binding_course_id=5, filters={"startDate": "2025-01-01"})
        result = _materialize_node(node, _user())
        assert result == b"data\n"

    @patch("packages.services._build.resolve_anonymization", return_value=(False, None))
    def test_unsupported_binding(self, mock_anon):
        """Unsupported dataset binding raises ValueError."""
        from packages.services._build import _materialize_node
        node = _node(1, source_type="LIVE", dataset_binding="UNKNOWN")
        with pytest.raises(ValueError, match="Unsupported dataset binding"):
            _materialize_node(node, _user())


# ---------------------------------------------------------------------------
# _build_manifest
# ---------------------------------------------------------------------------

class TestBuildManifest:
    def test_manifest_structure(self):
        """Manifest includes workspace metadata, build job ID, and file checksums."""
        from packages.services._build import _build_manifest

        ws = _workspace(id=10, name="WS", revision=2)
        # Mock the workspace.nodes query chain
        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.filter.return_value = []

        job = _job(id=1, workspace=ws)
        job.started_at = timezone.now()

        file_contents = {"data/roster.csv": b"col\nval\n"}
        checksums = {"data/roster.csv": "abc123"}

        manifest = _build_manifest(ws, job, file_contents, checksums, [])
        assert manifest["workspaceId"] == 10
        assert manifest["workspaceName"] == "WS"
        assert manifest["revision"] == 2
        assert manifest["buildJobId"] == 1
        assert len(manifest["files"]) == 1
        assert manifest["files"][0]["path"] == "data/roster.csv"
        assert manifest["files"][0]["sha256"] == "abc123"
        assert manifest["snapshots"] is None

    def test_manifest_with_snapshot_nodes(self):
        """Manifest includes snapshot metadata when nodes use snapshot sources."""
        from packages.services._build import _build_manifest

        ws = _workspace()
        snap_node = MagicMock()
        snap_node.id = 5
        snap_node.snapshot = MagicMock()
        snap_node.snapshot.id = 100
        snap_node.snapshot.metadata = {"capturedAt": "2025-01-01T00:00:00"}
        snap_node.snapshot.expires_at = MagicMock()
        snap_node.snapshot.expires_at.isoformat.return_value = "2025-01-02T00:00:00"
        snap_node.snapshot.checksum_sha256 = "def456"
        snap_node.snapshot.filters = {}
        snap_node.snapshot.dataset_binding = "ROSTER"
        snap_node.snapshot.row_count = 10

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.filter.return_value = [snap_node]

        job = _job(workspace=ws)
        job.started_at = timezone.now()

        manifest = _build_manifest(ws, job, {}, {}, [])
        assert manifest["snapshots"] is not None
        assert 5 in manifest["snapshots"]
        assert manifest["snapshots"][5]["sourceType"] == "SNAPSHOT"

    def test_manifest_with_auto_live_snapshots(self):
        """Manifest records auto-created live snapshots with LIVE_AUTO source type."""
        from packages.services._build import _build_manifest

        ws = _workspace()
        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.filter.return_value = []

        auto_snap = MagicMock()
        auto_snap.id = 200
        auto_snap.metadata = {"capturedAt": "2025-02-01T00:00:00"}
        auto_snap.expires_at = None
        auto_snap.checksum_sha256 = "ghi789"
        auto_snap.filters = None
        auto_snap.dataset_binding = "ROSTER"
        auto_snap.row_count = 5

        job = _job(workspace=ws)
        job.started_at = timezone.now()

        manifest = _build_manifest(ws, job, {}, {}, [], auto_live_snapshots={10: auto_snap})
        assert manifest["snapshots"] is not None
        assert 10 in manifest["snapshots"]
        assert manifest["snapshots"][10]["sourceType"] == "LIVE_AUTO"
        assert manifest["snapshots"][10]["expiresAt"] is None


# ---------------------------------------------------------------------------
# execute_build — strict mode validation failure
# ---------------------------------------------------------------------------

class TestExecuteBuildStrictFail:
    @patch("packages.services._build.validate_workspace")
    def test_strict_mode_validation_failure(self, mock_validate):
        """Strict mode build fails immediately when validation finds violations."""
        from packages.services._build import execute_build

        vr = MagicMock()
        vr.valid = False
        violation = MagicMock()
        violation.to_dict.return_value = {"code": "EMPTY_TREE", "message": "no nodes"}
        vr.violations = [violation]
        vr.warnings = []
        mock_validate.return_value = vr

        job = _job(strict_mode=True)
        result = execute_build(job)
        assert result.status == "FAILED"
        assert result.error_message  # JSON serialized violations


# ---------------------------------------------------------------------------
# execute_build — successful build
# ---------------------------------------------------------------------------

class TestExecuteBuildSuccess:
    @patch("packages.services._build.PackageArtifact.objects.create")
    @patch("packages.services._build.create_snapshot")
    @patch("packages.services._build.validate_workspace")
    def test_successful_live_build(self, mock_validate, mock_create_snapshot, mock_artifact_create):
        """Successful live build creates a zip artifact and marks job COMPLETED."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        file_node = _node(2, label="roster", node_type="FILE", parent_id=1,
                          source_type="LIVE", dataset_binding="ROSTER")

        # Mock workspace nodes query
        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        # Mock auto-snapshot for LIVE node
        auto_snap = MagicMock()
        auto_snap.id = 50
        auto_snap.metadata = {}
        auto_snap.expires_at = None
        auto_snap.checksum_sha256 = "abc"
        auto_snap.filters = None
        auto_snap.dataset_binding = "ROSTER"
        auto_snap.row_count = 1
        auto_snap.status = "READY"
        auto_snap.storage_key = "/tmp/test.csv"
        mock_create_snapshot.return_value = auto_snap

        job = _job(workspace=ws, strict_mode=False)

        # Mock _read_snapshot_bytes to return CSV data
        with patch("packages.services._build._read_snapshot_bytes", return_value=b"col\nval\n"), \
             patch("packages.services._build.os.makedirs"), \
             patch("packages.services._build.zipfile.ZipFile") as mock_zip, \
             patch("packages.services._build.os.path.getsize", return_value=100), \
             patch("builtins.open", mock_open(read_data=b"zipdata")):

            mock_zf = MagicMock()
            mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zf)
            mock_zip.return_value.__exit__ = MagicMock(return_value=False)

            result = execute_build(job)

        assert result.status == "COMPLETED"
        mock_artifact_create.assert_called_once()

    @patch("packages.services._build.PackageArtifact.objects.create")
    @patch("packages.services._build.validate_workspace")
    def test_snapshot_source_build(self, mock_validate, mock_artifact_create):
        """Build using snapshot-sourced nodes completes successfully."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        snap = MagicMock()
        snap.id = 99
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        file_node = _node(2, label="data.csv", node_type="FILE", parent_id=1,
                          source_type="SNAPSHOT", snapshot=snap)

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        job = _job(workspace=ws, strict_mode=False)

        with patch("packages.services._build._materialize_node", return_value=b"snap-csv\n"), \
             patch("packages.services._build.os.makedirs"), \
             patch("packages.services._build.zipfile.ZipFile") as mock_zip, \
             patch("packages.services._build.os.path.getsize", return_value=50), \
             patch("builtins.open", mock_open(read_data=b"zipdata")):

            mock_zf = MagicMock()
            mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zf)
            mock_zip.return_value.__exit__ = MagicMock(return_value=False)

            result = execute_build(job)

        assert result.status == "COMPLETED"


# ---------------------------------------------------------------------------
# execute_build — general exception
# ---------------------------------------------------------------------------

class TestExecuteBuildException:
    @patch("packages.services._build.validate_workspace", side_effect=RuntimeError("boom"))
    def test_exception_marks_failed(self, mock_validate):
        """Unhandled exception during build marks the job as FAILED with error message."""
        from packages.services._build import execute_build
        job = _job(strict_mode=False)
        result = execute_build(job)
        assert result.status == "FAILED"
        assert "boom" in result.error_message


# ---------------------------------------------------------------------------
# execute_build — auto snapshot failure in non-strict mode
# ---------------------------------------------------------------------------

class TestExecuteBuildAutoSnapshotWarning:
    @patch("packages.services._build.PackageArtifact.objects.create")
    @patch("packages.services._build.create_snapshot", side_effect=RuntimeError("snap fail"))
    @patch("packages.services._build.validate_workspace")
    def test_auto_snapshot_fail_warning(self, mock_validate, mock_snap, mock_artifact):
        """Auto-snapshot failure in non-strict mode records a warning but still completes."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          source_type="LIVE", dataset_binding="ROSTER")

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        job = _job(workspace=ws, strict_mode=False)

        # The auto snapshot fails -> warning; then materialization also fails because no auto_snapshot
        with patch("packages.services._build.os.makedirs"), \
             patch("packages.services._build.zipfile.ZipFile") as mock_zip, \
             patch("packages.services._build.os.path.getsize", return_value=10), \
             patch("builtins.open", mock_open(read_data=b"zip")):

            mock_zf = MagicMock()
            mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zf)
            mock_zip.return_value.__exit__ = MagicMock(return_value=False)

            result = execute_build(job)

        assert result.status == "COMPLETED"
        # Should have warnings for auto snapshot failure AND materialize failure
        assert len(result.warnings) >= 1


# ---------------------------------------------------------------------------
# execute_build — auto snapshot failure in strict mode re-raises
# ---------------------------------------------------------------------------

class TestExecuteBuildAutoSnapshotStrictRaise:
    @patch("packages.services._build.create_snapshot", side_effect=RuntimeError("strict snap fail"))
    @patch("packages.services._build.validate_workspace")
    def test_auto_snapshot_strict_raises(self, mock_validate, mock_snap):
        """Auto-snapshot failure in strict mode marks the build as FAILED."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          source_type="LIVE", dataset_binding="ROSTER")

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        job = _job(workspace=ws, strict_mode=True)

        result = execute_build(job)
        assert result.status == "FAILED"
        assert "strict snap fail" in result.error_message


# ---------------------------------------------------------------------------
# execute_build — csv extension added
# ---------------------------------------------------------------------------

class TestExecuteBuildCsvExtension:
    @patch("packages.services._build.PackageArtifact.objects.create")
    @patch("packages.services._build.create_snapshot")
    @patch("packages.services._build.validate_workspace")
    def test_csv_extension_appended(self, mock_validate, mock_snap, mock_artifact):
        """File nodes without .csv extension get it appended in the zip archive."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        # Label without .csv extension
        file_node = _node(2, label="roster", node_type="FILE", parent_id=1,
                          source_type="LIVE", dataset_binding="ROSTER")

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        auto_snap = MagicMock()
        auto_snap.id = 1
        auto_snap.metadata = {}
        auto_snap.save = MagicMock()
        mock_snap.return_value = auto_snap

        job = _job(workspace=ws, strict_mode=False)

        with patch("packages.services._build._read_snapshot_bytes", return_value=b"data\n"), \
             patch("packages.services._build.os.makedirs"), \
             patch("packages.services._build.zipfile.ZipFile") as mock_zip, \
             patch("packages.services._build.os.path.getsize", return_value=10), \
             patch("builtins.open", mock_open(read_data=b"zip")):

            mock_zf = MagicMock()
            mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zf)
            mock_zip.return_value.__exit__ = MagicMock(return_value=False)

            result = execute_build(job)

        assert result.status == "COMPLETED"
        # Check that the file was written with .csv extension
        write_calls = mock_zf.writestr.call_args_list
        paths_written = [c[0][0] for c in write_calls]
        assert any(p.endswith(".csv") for p in paths_written)


# ---------------------------------------------------------------------------
# execute_build — no metadata files
# ---------------------------------------------------------------------------

class TestExecuteBuildNoMetadata:
    @patch("packages.services._build.PackageArtifact.objects.create")
    @patch("packages.services._build.validate_workspace")
    def test_no_metadata_files(self, mock_validate, mock_artifact):
        """Build with include_metadata_files=False omits MANIFEST.json and CHECKSUMS.txt."""
        from packages.services._build import execute_build

        vr = _mock_validation_result(valid=True)
        mock_validate.return_value = vr

        ws = _workspace()
        root = _node(1, label="root", node_type="FOLDER", parent_id=None,
                     source_type="LIVE", dataset_binding=None)
        file_node = _node(2, label="data.csv", node_type="FILE", parent_id=1,
                          source_type="SNAPSHOT",
                          snapshot=MagicMock())

        mock_qs = MagicMock()
        ws.nodes.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = [root, file_node]

        job = _job(workspace=ws, strict_mode=False)

        with patch("packages.services._build._materialize_node", return_value=b"csv\n"), \
             patch("packages.services._build.os.makedirs"), \
             patch("packages.services._build.zipfile.ZipFile") as mock_zip, \
             patch("packages.services._build.os.path.getsize", return_value=10), \
             patch("builtins.open", mock_open(read_data=b"zip")):

            mock_zf = MagicMock()
            mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zf)
            mock_zip.return_value.__exit__ = MagicMock(return_value=False)

            result = execute_build(job, include_metadata_files=False)

        assert result.status == "COMPLETED"
        write_calls = mock_zf.writestr.call_args_list
        paths = [c[0][0] for c in write_calls]
        assert "MANIFEST.json" not in paths
        assert "CHECKSUMS.txt" not in paths
