"""Snapshot lifecycle services — create, list, expire, cleanup."""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from courses.models import Course
from exports.services import (
    export_course_submissions,
    export_cross_course_submissions,
    export_roster,
    resolve_anonymization,
)

from ..models import (
    DatasetBinding,
    DataSnapshot,
    PackageAuditLog,
    PkgAuditAction,
    PkgAuditOutcome,
    SnapshotStatus,
)

if TYPE_CHECKING:
    from accounts.models import User
    from ..models import PackageWorkspace

SNAPSHOT_DIR = os.path.join(
    getattr(settings, "MEDIA_ROOT", tempfile.gettempdir()), "snapshots"
)
SNAPSHOT_RETENTION_HOURS = 24


def _log_pkg_audit(actor, action, workspace=None, metadata=None, outcome=PkgAuditOutcome.SUCCESS):
    PackageAuditLog.objects.create(
        actor=actor,
        action=action,
        workspace=workspace,
        metadata=metadata or {},
        outcome=outcome,
    )


@transaction.atomic
def create_snapshot(
    user: User,
    workspace: PackageWorkspace,
    *,
    dataset_binding: str,
    scope_course_id: int | None = None,
    filters: dict | None = None,
    include_answers: bool = False,
    identifiable: bool = False,
) -> DataSnapshot:
    """Create a DataSnapshot, materialize CSV bytes to disk immediately."""

    # Resolve anonymization (same logic as exports)
    is_identifiable, err = resolve_anonymization(user, identifiable)
    if err:
        raise PermissionError(err)

    snapshot = DataSnapshot.objects.create(
        workspace=workspace,
        created_by=user,
        dataset_binding=dataset_binding,
        scope_course_id=scope_course_id,
        filters=filters,
        include_answers=include_answers,
        identifiable=is_identifiable,
        status=SnapshotStatus.QUEUED,
        expires_at=timezone.now() + timedelta(hours=SNAPSHOT_RETENTION_HOURS),
    )

    try:
        csv_bytes, row_count, course_name = _materialize_snapshot(
            snapshot, user, is_identifiable
        )

        # Write to disk
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        storage_key = os.path.join(SNAPSHOT_DIR, f"snap-{snapshot.id}.csv")
        with open(storage_key, "wb") as f:
            f.write(csv_bytes)

        file_size = len(csv_bytes)
        checksum = hashlib.sha256(csv_bytes).hexdigest()

        snapshot.storage_key = storage_key
        snapshot.row_count = row_count
        snapshot.file_size = file_size
        snapshot.checksum_sha256 = checksum
        snapshot.status = SnapshotStatus.READY
        snapshot.metadata = {
            "capturedAt": timezone.now().isoformat(),
            "courseName": course_name,
            "datasetBinding": dataset_binding,
            "isAnonymized": not is_identifiable,
            "filters": filters,
        }
        snapshot.save(update_fields=[
            "storage_key", "row_count", "file_size", "checksum_sha256",
            "status", "metadata", "updated_at",
        ])

        _log_pkg_audit(
            user,
            PkgAuditAction.SNAPSHOT_CREATE,
            workspace=workspace,
            metadata={
                "snapshotId": snapshot.id,
                "datasetBinding": dataset_binding,
                "scopeCourseId": scope_course_id,
                "rowCount": row_count,
                "fileSize": file_size,
            },
        )

    except Exception as exc:
        snapshot.status = SnapshotStatus.FAILED
        snapshot.error_message = str(exc)
        snapshot.save(update_fields=["status", "error_message", "updated_at"])
        _log_pkg_audit(
            user,
            PkgAuditAction.SNAPSHOT_CREATE,
            workspace=workspace,
            metadata={"snapshotId": snapshot.id, "error": str(exc)},
            outcome=PkgAuditOutcome.FAILURE,
        )
        raise

    return snapshot


def _materialize_snapshot(snapshot: DataSnapshot, user, is_identifiable: bool):
    """Call the existing export functions and collect all bytes. Returns (bytes, row_count, course_name)."""
    course_name = ""

    if snapshot.dataset_binding == DatasetBinding.ROSTER:
        course = Course.objects.get(id=snapshot.scope_course_id)
        course_name = course.name
        gen, row_count, _anon = export_roster(
            user, course, identifiable=is_identifiable
        )
        return b"".join(gen), row_count, course_name

    if snapshot.dataset_binding == DatasetBinding.COURSE_SUBMISSIONS:
        course = Course.objects.get(id=snapshot.scope_course_id)
        course_name = course.name
        filters = snapshot.filters or {}
        gen, row_count, _anon = export_course_submissions(
            user,
            course,
            start_date=filters.get("startDate"),
            end_date=filters.get("endDate"),
            category=filters.get("category"),
            assessment_id=filters.get("assessmentId"),
            assignment_id=filters.get("assignmentId"),
            status_filter=filters.get("status"),
            include_answers=snapshot.include_answers,
            identifiable=is_identifiable,
        )
        return b"".join(gen), row_count, course_name

    if snapshot.dataset_binding == DatasetBinding.CROSS_COURSE_SUBMISSIONS:
        filters = snapshot.filters or {}
        gen, row_count, _anon = export_cross_course_submissions(
            user,
            start_date=filters.get("startDate"),
            end_date=filters.get("endDate"),
            category=filters.get("category"),
            assessment_id=filters.get("assessmentId"),
            status_filter=filters.get("status"),
            include_answers=snapshot.include_answers,
            identifiable=is_identifiable,
        )
        return b"".join(gen), row_count, course_name

    raise ValueError(f"Unsupported dataset binding: {snapshot.dataset_binding}")


def list_snapshots(workspace: PackageWorkspace) -> list[DataSnapshot]:
    """Return all non-expired snapshots for a workspace, newest first."""
    # Keep status in sync for time-expired snapshots even if cleanup command has not run.
    now = timezone.now()
    DataSnapshot.objects.filter(
        workspace=workspace,
        expires_at__lt=now,
    ).exclude(status=SnapshotStatus.EXPIRED).update(status=SnapshotStatus.EXPIRED)

    return list(
        DataSnapshot.objects.filter(
            workspace=workspace,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).exclude(
            status=SnapshotStatus.EXPIRED,
        ).order_by("-created_at")
    )


def expire_snapshot(snapshot: DataSnapshot) -> None:
    """Mark a snapshot as expired and delete its file."""
    snapshot.status = SnapshotStatus.EXPIRED
    snapshot.save(update_fields=["status", "updated_at"])
    if snapshot.storage_key and os.path.exists(snapshot.storage_key):
        os.remove(snapshot.storage_key)


def cleanup_expired_snapshots() -> dict[str, int]:
    """Delete all snapshots past their expires_at. Idempotent."""
    now = timezone.now()
    expired = DataSnapshot.objects.filter(
        expires_at__lt=now,
    ).exclude(status=SnapshotStatus.EXPIRED)

    count = 0
    files_deleted = 0
    for snap in expired:
        if snap.storage_key and os.path.exists(snap.storage_key):
            try:
                os.remove(snap.storage_key)
                files_deleted += 1
            except OSError:
                pass  # Idempotent — missing file is fine
        snap.status = SnapshotStatus.EXPIRED
        snap.save(update_fields=["status", "updated_at"])
        count += 1

    return {"snapshotsExpired": count, "filesDeleted": files_deleted}
