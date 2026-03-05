"""FR-16 workspace & node mutation services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from ..models import (
    BuildStatus,
    NodeSourceType,
    NodeType,
    PackageAuditLog,
    PackageBuildJob,
    PackageNode,
    PackageWorkspace,
    PkgAuditAction,
    PkgAuditOutcome,
    WorkspaceStatus,
)
from ._build import execute_build

if TYPE_CHECKING:
    from accounts.models import User


def _log_pkg_audit(actor, action, workspace=None, scope="", metadata=None, outcome=PkgAuditOutcome.SUCCESS):
    PackageAuditLog.objects.create(
        actor=actor,
        action=action,
        workspace=workspace,
        scope=scope,
        metadata=metadata or {},
        outcome=outcome,
    )


# ── Workspace mutations ─────────────────────────────────────────────


@transaction.atomic
def create_workspace(user: User, payload: dict) -> PackageWorkspace:
    ws = PackageWorkspace.objects.create(
        name=payload["name"],
        description=payload.get("description", ""),
        scope_course_id=payload.get("scopeCourseId"),
        created_by=user,
    )
    _log_pkg_audit(
        user,
        PkgAuditAction.WORKSPACE_CREATE,
        workspace=ws,
        scope=f"course:{ws.scope_course_id}" if ws.scope_course_id else "global",
    )
    return ws


@transaction.atomic
def update_workspace(user: User, workspace: PackageWorkspace, payload: dict) -> PackageWorkspace:
    if "name" in payload:
        workspace.name = payload["name"]
    if "description" in payload:
        workspace.description = payload["description"]
    if "status" in payload:
        workspace.status = payload["status"]
    workspace.revision += 1
    workspace.save()
    _log_pkg_audit(
        user,
        PkgAuditAction.WORKSPACE_UPDATE,
        workspace=workspace,
        metadata={"fields": list(payload.keys())},
    )
    return workspace


# ── Node mutations ───────────────────────────────────────────────────


@transaction.atomic
def add_node(user: User, workspace: PackageWorkspace, payload: dict) -> PackageNode:
    node = PackageNode.objects.create(
        workspace=workspace,
        parent_id=payload.get("parentId"),
        node_type=payload["nodeType"],
        label=payload["label"],
        order_index=payload.get("orderIndex", 0),
        dataset_binding=payload.get("datasetBinding"),
        binding_course_id=payload.get("bindingCourseId"),
        filters=payload.get("filters"),
        identifiable=payload.get("identifiable", False),
        include_answers=payload.get("includeAnswers", False),
        source_type=payload.get("sourceType", NodeSourceType.LIVE),
        snapshot_id=payload.get("snapshotId"),
    )
    workspace.revision += 1
    workspace.save(update_fields=["revision", "updated_at"])
    _log_pkg_audit(
        user,
        PkgAuditAction.NODE_ADD,
        workspace=workspace,
        metadata={"nodeId": node.id, "nodeType": node.node_type, "label": node.label},
    )
    return node


@transaction.atomic
def update_node(user: User, node: PackageNode, payload: dict) -> PackageNode:
    if "label" in payload:
        node.label = payload["label"]
    if "parentId" in payload:
        node.parent_id = payload["parentId"]
    if "orderIndex" in payload:
        node.order_index = payload["orderIndex"]
    if "datasetBinding" in payload:
        node.dataset_binding = payload["datasetBinding"]
    if "bindingCourseId" in payload:
        node.binding_course_id = payload["bindingCourseId"]
    if "filters" in payload:
        node.filters = payload["filters"]
    if "identifiable" in payload:
        node.identifiable = payload["identifiable"]
    if "includeAnswers" in payload:
        node.include_answers = payload["includeAnswers"]
    if "sourceType" in payload:
        node.source_type = payload["sourceType"]
    if "snapshotId" in payload:
        node.snapshot_id = payload["snapshotId"]
    node.save()
    node.workspace.revision += 1
    node.workspace.save(update_fields=["revision", "updated_at"])
    _log_pkg_audit(
        user,
        PkgAuditAction.NODE_UPDATE,
        workspace=node.workspace,
        metadata={"nodeId": node.id, "fields": list(payload.keys())},
    )
    return node


@transaction.atomic
def delete_node(user: User, node: PackageNode) -> None:
    workspace = node.workspace
    node_id = node.id
    node.delete()
    workspace.revision += 1
    workspace.save(update_fields=["revision", "updated_at"])
    _log_pkg_audit(
        user,
        PkgAuditAction.NODE_DELETE,
        workspace=workspace,
        metadata={"nodeId": node_id},
    )


# ── Node reorder ─────────────────────────────────────────────────────


@transaction.atomic
def reorder_node(
    user: User,
    workspace: PackageWorkspace,
    *,
    moved_node: PackageNode,
    target_parent_id: int | None,
    target_order_index: int,
) -> None:
    """Move a node to a new parent/position and reindex siblings atomically."""
    old_parent_id = moved_node.parent_id
    old_order_index = moved_node.order_index

    sibling_count = (
        PackageNode.objects.filter(workspace=workspace, parent_id=target_parent_id)
        .exclude(id=moved_node.id)
        .count()
    )
    bounded_index = max(0, min(target_order_index, sibling_count))

    # Update the moved node's parent and order
    moved_node.parent_id = target_parent_id
    moved_node.order_index = bounded_index
    moved_node.save(update_fields=["parent_id", "order_index", "updated_at"])

    # Reindex siblings in the target parent to make room
    siblings = (
        PackageNode.objects.filter(workspace=workspace, parent_id=target_parent_id)
        .exclude(id=moved_node.id)
        .order_by("order_index", "id")
    )
    idx = 0
    for sibling in siblings:
        if idx == bounded_index:
            idx += 1  # skip the slot for the moved node
        if sibling.order_index != idx:
            sibling.order_index = idx
            sibling.save(update_fields=["order_index", "updated_at"])
        idx += 1

    # If parent changed, reindex old parent's siblings too
    if old_parent_id != target_parent_id:
        old_siblings = (
            PackageNode.objects.filter(workspace=workspace, parent_id=old_parent_id)
            .exclude(id=moved_node.id)
            .order_by("order_index", "id")
        )
        for i, sibling in enumerate(old_siblings):
            if sibling.order_index != i:
                sibling.order_index = i
                sibling.save(update_fields=["order_index", "updated_at"])

    workspace.revision += 1
    workspace.save(update_fields=["revision", "updated_at"])

    _log_pkg_audit(
        user,
        PkgAuditAction.NODE_REORDER,
        workspace=workspace,
        metadata={
            "nodeId": moved_node.id,
            "fromParentId": old_parent_id,
            "toParentId": target_parent_id,
            "fromIndex": old_order_index,
            "toIndex": bounded_index,
        },
    )


# ── Build ────────────────────────────────────────────────────────────


@transaction.atomic
def create_build_job(
    user: User,
    workspace: PackageWorkspace,
    *,
    strict_mode: bool = True,
    snapshot_id: int | None = None,
) -> PackageBuildJob:
    mode = "snapshot" if snapshot_id is not None else "live"
    job = PackageBuildJob.objects.create(
        workspace=workspace,
        strict_mode=strict_mode,
        snapshot_id=snapshot_id,
        mode=mode,
        created_by=user,
    )
    _log_pkg_audit(
        user,
        PkgAuditAction.BUILD,
        workspace=workspace,
        metadata={
            "jobId": job.id,
            "strictMode": strict_mode,
            "mode": mode,
            "snapshotId": snapshot_id,
        },
    )
    return job


def run_build(
    job: PackageBuildJob,
    *,
    include_metadata_files: bool = True,
) -> PackageBuildJob:
    """Execute build (called after job creation, outside transaction)."""
    return execute_build(job, include_metadata_files=include_metadata_files)


# ── Download audit ───────────────────────────────────────────────────


def log_download_audit(user, workspace, artifact, outcome=PkgAuditOutcome.SUCCESS):
    _log_pkg_audit(
        user,
        PkgAuditAction.DOWNLOAD,
        workspace=workspace,
        metadata={"artifactId": artifact.id, "buildJobId": artifact.build_job_id},
        outcome=outcome,
    )
