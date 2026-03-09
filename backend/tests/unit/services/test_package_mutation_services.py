"""Unit tests for packages.services._mutations — workspace & node mutation services.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

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
    return u


def _workspace(revision=1, scope_course_id=None):
    ws = MagicMock()
    ws.id = 10
    ws.name = "Test WS"
    ws.description = ""
    ws.scope_course_id = scope_course_id
    ws.revision = revision
    ws.save = MagicMock()
    return ws


def _node(id=1, workspace=None, parent_id=None, node_type="FILE", label="f.csv",
          order_index=0):
    n = MagicMock()
    n.id = id
    n.workspace = workspace or _workspace()
    n.parent_id = parent_id
    n.node_type = node_type
    n.label = label
    n.order_index = order_index
    n.save = MagicMock()
    n.delete = MagicMock()
    return n


# ---------------------------------------------------------------------------
# _log_pkg_audit
# ---------------------------------------------------------------------------

class TestLogPkgAudit:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_creates_audit_log(self, mock_create):
        """Audit log entry is created with correct actor, action, and outcome."""
        from packages.services._mutations import _log_pkg_audit, PkgAuditAction, PkgAuditOutcome
        user = _user()
        _log_pkg_audit(user, PkgAuditAction.WORKSPACE_CREATE, workspace=None, scope="global")
        mock_create.assert_called_once()
        kwargs = mock_create.call_args[1]
        assert kwargs["actor"] == user
        assert kwargs["action"] == PkgAuditAction.WORKSPACE_CREATE
        assert kwargs["scope"] == "global"
        assert kwargs["outcome"] == PkgAuditOutcome.SUCCESS


# ---------------------------------------------------------------------------
# create_workspace
# ---------------------------------------------------------------------------

class TestCreateWorkspace:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageWorkspace.objects.create")
    def test_creates_workspace(self, mock_ws_create, mock_audit):
        """Workspace is created with provided name, description, and scope course ID."""
        from packages.services._mutations import create_workspace
        mock_ws = _workspace()
        mock_ws_create.return_value = mock_ws
        user = _user()

        result = create_workspace(user, {"name": "My WS", "description": "desc", "scopeCourseId": 5})
        mock_ws_create.assert_called_once_with(
            name="My WS",
            description="desc",
            scope_course_id=5,
            created_by=user,
        )
        assert result == mock_ws
        mock_audit.assert_called_once()

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageWorkspace.objects.create")
    def test_creates_workspace_defaults(self, mock_ws_create, mock_audit):
        """Workspace defaults to empty description and no scope course when omitted."""
        from packages.services._mutations import create_workspace
        mock_ws = _workspace()
        mock_ws.scope_course_id = None
        mock_ws_create.return_value = mock_ws
        user = _user()

        result = create_workspace(user, {"name": "WS"})
        mock_ws_create.assert_called_once_with(
            name="WS",
            description="",
            scope_course_id=None,
            created_by=user,
        )


# ---------------------------------------------------------------------------
# update_workspace
# ---------------------------------------------------------------------------

class TestUpdateWorkspace:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_updates_fields(self, mock_audit):
        """Updating workspace sets name, description, status and bumps revision."""
        from packages.services._mutations import update_workspace
        ws = _workspace(revision=1)
        user = _user()
        result = update_workspace(user, ws, {"name": "New", "description": "D", "status": "SEALED"})
        assert ws.name == "New"
        assert ws.description == "D"
        assert ws.status == "SEALED"
        assert ws.revision == 2
        ws.save.assert_called_once()
        mock_audit.assert_called_once()

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_updates_partial(self, mock_audit):
        """Partial update changes only provided fields and bumps revision."""
        from packages.services._mutations import update_workspace
        ws = _workspace(revision=3)
        ws.name = "Old"
        user = _user()
        result = update_workspace(user, ws, {"name": "New"})
        assert ws.name == "New"
        assert ws.revision == 4


# ---------------------------------------------------------------------------
# add_node
# ---------------------------------------------------------------------------

class TestAddNode:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.create")
    def test_add_node(self, mock_node_create, mock_audit):
        """Adding a node creates it with all provided fields and bumps workspace revision."""
        from packages.services._mutations import add_node
        ws = _workspace(revision=1)
        user = _user()
        mock_node = _node(id=5, workspace=ws)
        mock_node_create.return_value = mock_node

        payload = {
            "nodeType": "FILE",
            "label": "roster.csv",
            "parentId": 1,
            "datasetBinding": "ROSTER",
            "bindingCourseId": 10,
            "filters": {"status": "active"},
            "identifiable": True,
            "includeAnswers": True,
            "sourceType": "SNAPSHOT",
            "snapshotId": 42,
            "orderIndex": 3,
        }
        result = add_node(user, ws, payload)
        mock_node_create.assert_called_once()
        assert ws.revision == 2
        ws.save.assert_called_once()
        mock_audit.assert_called_once()

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.create")
    def test_add_node_defaults(self, mock_node_create, mock_audit):
        """Adding a node without optional fields uses sensible defaults."""
        from packages.services._mutations import add_node
        ws = _workspace(revision=1)
        user = _user()
        mock_node = _node(id=6, workspace=ws)
        mock_node_create.return_value = mock_node

        result = add_node(user, ws, {"nodeType": "FOLDER", "label": "data"})
        kwargs = mock_node_create.call_args[1]
        assert kwargs["order_index"] == 0
        assert kwargs["identifiable"] is False
        assert kwargs["include_answers"] is False
        assert kwargs["source_type"] == "LIVE"


# ---------------------------------------------------------------------------
# update_node
# ---------------------------------------------------------------------------

class TestUpdateNode:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_update_all_fields(self, mock_audit):
        """Updating a node sets all provided fields and bumps workspace revision."""
        from packages.services._mutations import update_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws)
        user = _user()
        payload = {
            "label": "new.csv",
            "parentId": 2,
            "orderIndex": 5,
            "datasetBinding": "COURSE_SUBMISSIONS",
            "bindingCourseId": 20,
            "filters": {"startDate": "2025-01-01"},
            "identifiable": True,
            "includeAnswers": True,
            "sourceType": "SNAPSHOT",
            "snapshotId": 99,
        }
        result = update_node(user, node, payload)
        assert node.label == "new.csv"
        assert node.parent_id == 2
        assert node.order_index == 5
        assert node.dataset_binding == "COURSE_SUBMISSIONS"
        assert node.binding_course_id == 20
        assert node.identifiable is True
        assert node.include_answers is True
        assert node.source_type == "SNAPSHOT"
        assert node.snapshot_id == 99
        node.save.assert_called_once()
        assert ws.revision == 2

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_update_partial(self, mock_audit):
        """Partial node update changes only the specified field."""
        from packages.services._mutations import update_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws, label="old.csv")
        user = _user()
        update_node(user, node, {"label": "renamed.csv"})
        assert node.label == "renamed.csv"


# ---------------------------------------------------------------------------
# delete_node
# ---------------------------------------------------------------------------

class TestDeleteNode:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_delete_node(self, mock_audit):
        """Deleting a node removes it and bumps workspace revision."""
        from packages.services._mutations import delete_node
        ws = _workspace(revision=1)
        node = _node(id=7, workspace=ws)
        user = _user()
        delete_node(user, node)
        node.delete.assert_called_once()
        assert ws.revision == 2
        ws.save.assert_called_once()
        mock_audit.assert_called_once()


# ---------------------------------------------------------------------------
# reorder_node
# ---------------------------------------------------------------------------

class TestReorderNode:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.filter")
    def test_reorder_same_parent(self, mock_filter, mock_audit):
        """Reordering within the same parent updates index and bumps revision."""
        from packages.services._mutations import reorder_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws, parent_id=10, order_index=0)
        user = _user()

        # Mock sibling count query
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.count.return_value = 2
        mock_qs.order_by.return_value = []

        reorder_node(user, ws, moved_node=node, target_parent_id=10, target_order_index=1)
        node.save.assert_called()
        assert ws.revision == 2
        mock_audit.assert_called_once()

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.filter")
    def test_reorder_different_parent(self, mock_filter, mock_audit):
        """Reordering to a different parent updates parent_id and bumps revision."""
        from packages.services._mutations import reorder_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws, parent_id=10, order_index=0)
        user = _user()

        # The filter is called multiple times — for target siblings and old parent siblings
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.order_by.return_value = []

        reorder_node(user, ws, moved_node=node, target_parent_id=20, target_order_index=0)
        assert node.parent_id == 20
        assert ws.revision == 2

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.filter")
    def test_reorder_clamps_index(self, mock_filter, mock_audit):
        """Target order index beyond sibling count is clamped to the maximum."""
        from packages.services._mutations import reorder_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws, parent_id=10, order_index=0)
        user = _user()

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.count.return_value = 2  # only 2 siblings
        mock_qs.order_by.return_value = []

        reorder_node(user, ws, moved_node=node, target_parent_id=10, target_order_index=999)
        assert node.order_index == 2  # clamped to sibling_count

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageNode.objects.filter")
    def test_reorder_reindexes_siblings(self, mock_filter, mock_audit):
        """Siblings are reindexed to maintain contiguous order after reorder."""
        from packages.services._mutations import reorder_node
        ws = _workspace(revision=1)
        node = _node(id=1, workspace=ws, parent_id=10, order_index=0)
        user = _user()

        sibling = MagicMock()
        sibling.id = 2
        sibling.order_index = 0

        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.count.return_value = 1
        mock_qs.order_by.return_value = [sibling]

        reorder_node(user, ws, moved_node=node, target_parent_id=10, target_order_index=0)
        # sibling should be reindexed to slot 1 (since moved_node is at 0)
        assert sibling.order_index == 1
        sibling.save.assert_called()


# ---------------------------------------------------------------------------
# create_build_job
# ---------------------------------------------------------------------------

class TestCreateBuildJob:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageBuildJob.objects.create")
    def test_live_mode(self, mock_job_create, mock_audit):
        """Build job without snapshot_id is created in live mode."""
        from packages.services._mutations import create_build_job
        ws = _workspace()
        user = _user()
        mock_job = MagicMock()
        mock_job.id = 1
        mock_job_create.return_value = mock_job

        result = create_build_job(user, ws, strict_mode=True)
        mock_job_create.assert_called_once_with(
            workspace=ws,
            strict_mode=True,
            snapshot_id=None,
            mode="live",
            created_by=user,
        )
        assert result == mock_job

    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    @patch("packages.services._mutations.PackageBuildJob.objects.create")
    def test_snapshot_mode(self, mock_job_create, mock_audit):
        """Build job with snapshot_id is created in snapshot mode."""
        from packages.services._mutations import create_build_job
        ws = _workspace()
        user = _user()
        mock_job = MagicMock()
        mock_job.id = 2
        mock_job_create.return_value = mock_job

        result = create_build_job(user, ws, strict_mode=False, snapshot_id=42)
        mock_job_create.assert_called_once_with(
            workspace=ws,
            strict_mode=False,
            snapshot_id=42,
            mode="snapshot",
            created_by=user,
        )


# ---------------------------------------------------------------------------
# run_build
# ---------------------------------------------------------------------------

class TestRunBuild:
    @patch("packages.services._mutations.execute_build")
    def test_delegates_to_execute_build(self, mock_exec):
        """run_build delegates to execute_build with the provided arguments."""
        from packages.services._mutations import run_build
        job = MagicMock()
        mock_exec.return_value = job
        result = run_build(job, include_metadata_files=False)
        mock_exec.assert_called_once_with(job, include_metadata_files=False)
        assert result == job


# ---------------------------------------------------------------------------
# log_download_audit
# ---------------------------------------------------------------------------

class TestLogDownloadAudit:
    @patch("packages.services._mutations.PackageAuditLog.objects.create")
    def test_log_download(self, mock_create):
        """Download audit log records the artifact ID and build job ID."""
        from packages.services._mutations import log_download_audit
        user = _user()
        ws = _workspace()
        artifact = MagicMock()
        artifact.id = 50
        artifact.build_job_id = 10
        log_download_audit(user, ws, artifact)
        mock_create.assert_called_once()
        kwargs = mock_create.call_args[1]
        assert kwargs["action"] == "DOWNLOAD"
        assert kwargs["metadata"]["artifactId"] == 50
