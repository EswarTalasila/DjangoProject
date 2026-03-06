"""FR-16 build pipeline — materialize datasets, generate manifest/checksums, zip artifact."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

from courses.models import Course
from exports.services import (
    export_course_submissions,
    export_roster,
    resolve_anonymization,
)

from ..models import (
    BuildStatus,
    DataSnapshot,
    DatasetBinding,
    NodeSourceType,
    NodeType,
    PackageArtifact,
    PackageBuildJob,
    PackageWorkspace,
)
from ._snapshots import create_snapshot
from ._validation import (
    ValidationResult,
    compute_node_path,
    validate_workspace,
)

ARTIFACT_DIR = os.path.join(
    (
        os.path.join(
            tempfile.gettempdir(),
            "eel-package-builds",
            os.getenv("PYTEST_XDIST_WORKER", "main"),
        )
        if getattr(settings, "ENVIRONMENT", "").lower() == "testing"
        else getattr(settings, "MEDIA_ROOT", tempfile.gettempdir())
    ),
    "package_artifacts",
)
ARTIFACT_RETENTION_HOURS = 72


def _sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def execute_build(
    job: PackageBuildJob,
    *,
    include_metadata_files: bool = True,
) -> PackageBuildJob:
    """Run a build job synchronously.

    1. Validate workspace.
    2. Materialize each file node into CSV bytes.
    3. Optionally generate MANIFEST.json + CHECKSUMS.txt.
    4. Zip everything and persist artifact metadata.
    """
    job.status = BuildStatus.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    workspace = job.workspace
    user = job.created_by

    try:
        # 1. Validate
        vr = validate_workspace(
            workspace,
            user,
            strict_mode=job.strict_mode,
            snapshot_id=job.snapshot_id,
        )

        if job.strict_mode and not vr.valid:
            job.status = BuildStatus.FAILED
            job.error_message = json.dumps(
                [v.to_dict() for v in vr.violations], default=str
            )
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])
            return job

        # 2. Materialize files
        nodes = list(workspace.nodes.select_related("parent", "snapshot").order_by("id"))
        node_map = {n.id: n for n in nodes}
        file_nodes = [n for n in nodes if n.node_type == NodeType.FILE]

        file_contents: dict[str, bytes] = {}
        checksums: dict[str, str] = {}
        warnings: list[dict[str, Any]] = list(vr.warnings)
        auto_live_snapshots: dict[int, DataSnapshot] = {}

        # 2a. Automatically snapshot all LIVE file nodes so users do not
        # need to manage snapshot IDs manually.
        for node in file_nodes:
            if node.source_type != NodeSourceType.LIVE:
                continue
            try:
                snapshot = create_snapshot(
                    user,
                    workspace,
                    dataset_binding=node.dataset_binding,
                    scope_course_id=node.binding_course_id,
                    filters=node.filters,
                    include_answers=node.include_answers,
                    identifiable=node.identifiable,
                )
                snapshot.metadata = {
                    **(snapshot.metadata or {}),
                    "buildJobId": job.id,
                    "nodeId": node.id,
                    "autoSnapshot": True,
                }
                snapshot.save(update_fields=["metadata", "updated_at"])
                auto_live_snapshots[node.id] = snapshot
            except Exception as exc:
                if job.strict_mode:
                    raise
                warnings.append(
                    {
                        "nodeId": node.id,
                        "code": "AUTO_SNAPSHOT_FAILED",
                        "message": str(exc),
                    }
                )

        for node in file_nodes:
            path = compute_node_path(node, node_map)
            # Ensure .csv extension
            if not path.endswith(".csv"):
                path = path + ".csv"

            try:
                if node.source_type == NodeSourceType.LIVE:
                    auto_snapshot = auto_live_snapshots.get(node.id)
                    if auto_snapshot is None:
                        raise ValueError(
                            f"Node {node.id} has no automatic snapshot available for this build."
                        )
                    data = _read_snapshot_bytes(auto_snapshot)
                else:
                    data = _materialize_node(node, user)
                file_contents[path] = data
                checksums[path] = hashlib.sha256(data).hexdigest()
            except Exception as exc:
                if job.strict_mode:
                    raise
                warnings.append(
                    {
                        "nodeId": node.id,
                        "code": "MATERIALIZE_FAILED",
                        "message": str(exc),
                    }
                )

        # 3. Generate manifest for audit/persistence (optionally included in ZIP)
        manifest = _build_manifest(
            workspace,
            job,
            file_contents,
            checksums,
            warnings,
            auto_live_snapshots=auto_live_snapshots,
        )
        manifest_bytes = json.dumps(manifest, indent=2, default=str).encode("utf-8")

        checksums_bytes: bytes | None = None
        if include_metadata_files:
            # 4. Generate checksums file
            checksums_lines = [f"{sha}  {path}" for path, sha in sorted(checksums.items())]
            # Include MANIFEST.json checksum
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            checksums_lines.append(f"{manifest_sha}  MANIFEST.json")
            checksums_bytes = "\n".join(checksums_lines).encode("utf-8")

        # 5. Write zip
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        zip_filename = f"pkg-{workspace.id}-build-{job.id}.zip"
        zip_path = os.path.join(ARTIFACT_DIR, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, data in sorted(file_contents.items()):
                zf.writestr(path, data)
            if include_metadata_files:
                zf.writestr("MANIFEST.json", manifest_bytes)
                if checksums_bytes is not None:
                    zf.writestr("CHECKSUMS.txt", checksums_bytes)

        file_size = os.path.getsize(zip_path)

        # 6. Persist artifact
        artifact = PackageArtifact.objects.create(
            build_job=job,
            file_path=zip_path,
            file_size=file_size,
            checksum_sha256=_sha256_file(zip_path),
            manifest=manifest,
            expires_at=timezone.now() + timedelta(hours=ARTIFACT_RETENTION_HOURS),
        )

        job.status = BuildStatus.COMPLETED
        job.warnings = warnings
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "warnings", "completed_at"])

    except Exception as exc:
        job.status = BuildStatus.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])

    return job


def _materialize_node(node, user) -> bytes:
    """Produce CSV bytes for a single file node.

    If node.source_type is SNAPSHOT, read pre-materialized bytes from disk.
    Otherwise, query live data via export functions.
    """
    from ..models import NodeSourceType

    # ── Snapshot path: read from disk ──
    if node.source_type == NodeSourceType.SNAPSHOT:
        snapshot = node.snapshot
        if snapshot is None:
            raise ValueError(f"Node {node.id} has source_type=SNAPSHOT but no snapshot linked")
        return _read_snapshot_bytes(snapshot)

    # ── Live path: query current data ──
    is_identifiable, _ = resolve_anonymization(user, node.identifiable or False)

    if node.dataset_binding == DatasetBinding.ROSTER:
        course = Course.objects.get(id=node.binding_course_id)
        gen, _count, _anon = export_roster(
            user, course, identifiable=is_identifiable
        )
        return b"".join(gen)

    if node.dataset_binding == DatasetBinding.COURSE_SUBMISSIONS:
        course = Course.objects.get(id=node.binding_course_id)
        filters = node.filters or {}
        gen, _count, _anon = export_course_submissions(
            user,
            course,
            start_date=filters.get("startDate"),
            end_date=filters.get("endDate"),
            category=filters.get("category"),
            assessment_id=filters.get("assessmentId"),
            assignment_id=filters.get("assignmentId"),
            status_filter=filters.get("status"),
            include_answers=node.include_answers,
            identifiable=is_identifiable,
        )
        return b"".join(gen)

    raise ValueError(f"Unsupported dataset binding: {node.dataset_binding}")


def _build_manifest(
    workspace: PackageWorkspace,
    job: PackageBuildJob,
    file_contents: dict[str, bytes],
    checksums: dict[str, str],
    warnings: list[dict],
    auto_live_snapshots: dict[int, DataSnapshot] | None = None,
) -> dict[str, Any]:
    """Build a MANIFEST.json dict with file inventory, checksums, and snapshot lineage."""
    from ..models import NodeSourceType

    # Collect snapshot metadata from file nodes
    nodes = list(workspace.nodes.select_related("snapshot").filter(
        source_type=NodeSourceType.SNAPSHOT,
        snapshot__isnull=False,
    ))
    snapshot_info = {}
    for node in nodes:
        snap = node.snapshot
        if snap:
            snapshot_info[node.id] = {
                "snapshotId": snap.id,
                "capturedAt": snap.metadata.get("capturedAt", ""),
                "expiresAt": snap.expires_at.isoformat() if snap.expires_at else None,
                "sha256": snap.checksum_sha256,
                "filters": snap.filters,
                "datasetBinding": snap.dataset_binding,
                "rowCount": snap.row_count,
                "sourceType": "SNAPSHOT",
            }

    if auto_live_snapshots:
        for node_id, snap in auto_live_snapshots.items():
            snapshot_info[node_id] = {
                "snapshotId": snap.id,
                "capturedAt": snap.metadata.get("capturedAt", ""),
                "expiresAt": snap.expires_at.isoformat() if snap.expires_at else None,
                "sha256": snap.checksum_sha256,
                "filters": snap.filters,
                "datasetBinding": snap.dataset_binding,
                "rowCount": snap.row_count,
                "sourceType": "LIVE_AUTO",
            }

    return {
        "workspaceId": workspace.id,
        "workspaceName": workspace.name,
        "revision": workspace.revision,
        "buildJobId": job.id,
        "mode": job.mode,
        "snapshotId": job.snapshot_id,
        "strictMode": job.strict_mode,
        "liveCaptureStartedAt": job.started_at.isoformat() if job.started_at else None,
        "generatedAt": timezone.now().isoformat(),
        "files": [
            {"path": path, "sizeBytes": len(data), "sha256": checksums.get(path, "")}
            for path, data in sorted(file_contents.items())
        ],
        "snapshots": snapshot_info if snapshot_info else None,
        "warnings": warnings,
    }


def _read_snapshot_bytes(snapshot: DataSnapshot) -> bytes:
    """Read CSV bytes from a snapshot's storage file. Raises ValueError if expired/failed/missing."""
    from ..models import SnapshotStatus

    if snapshot.expires_at and snapshot.expires_at < timezone.now():
        snapshot.status = SnapshotStatus.EXPIRED
        snapshot.save(update_fields=["status", "updated_at"])
        raise ValueError(
            f"Snapshot {snapshot.id} has expired (expired at {snapshot.expires_at})"
        )
    if snapshot.status == SnapshotStatus.EXPIRED:
        raise ValueError(
            f"Snapshot {snapshot.id} has expired (expired at {snapshot.expires_at})"
        )
    if snapshot.status == SnapshotStatus.FAILED:
        raise ValueError(f"Snapshot {snapshot.id} failed: {snapshot.error_message}")
    if snapshot.status != SnapshotStatus.READY:
        raise ValueError(f"Snapshot {snapshot.id} is not ready (status={snapshot.status})")
    if not snapshot.storage_key or not os.path.exists(snapshot.storage_key):
        raise ValueError(
            f"Snapshot {snapshot.id} file missing at {snapshot.storage_key}"
        )
    with open(snapshot.storage_key, "rb") as file_obj:
        return file_obj.read()
