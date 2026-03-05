"""
FR-16 Package Workspace API endpoints.

Endpoints:
    GET    /api/v1/packages/workspaces                          (PKG-UC-01)
    POST   /api/v1/packages/workspaces                          (PKG-UC-01)
    GET    /api/v1/packages/workspaces/{workspaceId}             (PKG-UC-01)
    PATCH  /api/v1/packages/workspaces/{workspaceId}             (PKG-UC-02)
    POST   /api/v1/packages/workspaces/{workspaceId}/nodes       (PKG-UC-02)
    PATCH  /api/v1/packages/workspaces/{workspaceId}/nodes/{id}  (PKG-UC-02)
    DELETE /api/v1/packages/workspaces/{workspaceId}/nodes/{id}  (PKG-UC-02)
    POST   /api/v1/packages/workspaces/{workspaceId}/validate    (PKG-UC-03)
    POST   /api/v1/packages/workspaces/{workspaceId}/build       (PKG-UC-04)
    GET    /api/v1/packages/jobs/{jobId}                         (PKG-UC-04)
    GET    /api/v1/packages/artifacts/{artifactId}/download      (PKG-UC-05)
"""

import os

from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import Role
from core.permissions import IsTeacherOrAbove, has_role

from .models import (
    BuildStatus,
    PackageArtifact,
    PackageBuildJob,
    PackageNode,
    PackageWorkspace,
    PkgAuditAction,
    PkgAuditOutcome,
    SnapshotStatus,
)
from .serializers import (
    AddNodeSerializer,
    BuildWorkspaceSerializer,
    CreateSnapshotSerializer,
    CreateWorkspaceSerializer,
    ReorderNodeSerializer,
    UpdateNodeSerializer,
    UpdateWorkspaceSerializer,
    ValidateWorkspaceSerializer,
)
from .services import (
    add_node,
    create_build_job,
    create_workspace,
    delete_node,
    log_download_audit,
    run_build,
    update_node,
    update_workspace,
    validate_workspace,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _check_workspace_access(user, workspace):
    """Return error Response if user lacks scope access, else None."""
    if user.is_staff:
        return None
    if has_role(user, Role.RESEARCHER):
        return None
    # Teacher must own the scoped course
    if workspace.scope_course_id:
        try:
            if workspace.scope_course.teacher_profile != user.teacher_profile:
                return Response(
                    {"detail": "You do not own this workspace's course"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Exception:
            return Response(
                {"detail": "You do not own this workspace's course"},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif workspace.created_by_id != user.id:
        return Response(
            {"detail": "You do not own this workspace"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _cleanup_legacy_cross_course_nodes(workspace: PackageWorkspace) -> None:
    """Remove legacy nodes that use removed CROSS_COURSE_SUBMISSIONS binding."""
    deleted, _ = workspace.nodes.filter(
        dataset_binding="CROSS_COURSE_SUBMISSIONS"
    ).delete()
    if deleted:
        workspace.revision += 1
        workspace.save(update_fields=["revision", "updated_at"])


def _workspace_to_dict(workspace):
    nodes = list(workspace.nodes.select_related("parent").order_by("order_index", "id"))
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "status": workspace.status,
        "scopeCourseId": workspace.scope_course_id,
        "revision": workspace.revision,
        "createdBy": workspace.created_by_id,
        "createdAt": workspace.created_at.isoformat(),
        "updatedAt": workspace.updated_at.isoformat(),
        "nodes": [_node_to_dict(n) for n in nodes],
    }


def _node_to_dict(node):
    return {
        "id": node.id,
        "parentId": node.parent_id,
        "nodeType": node.node_type,
        "label": node.label,
        "orderIndex": node.order_index,
        "datasetBinding": node.dataset_binding,
        "bindingCourseId": node.binding_course_id,
        "filters": node.filters,
        "identifiable": node.identifiable,
        "includeAnswers": node.include_answers,
        "sourceType": node.source_type,
        "snapshotId": node.snapshot_id,
    }


def _job_to_dict(job):
    d = {
        "id": job.id,
        "workspaceId": job.workspace_id,
        "status": job.status,
        "strictMode": job.strict_mode,
        "mode": job.mode,
        "snapshotId": job.snapshot_id,
        "createdBy": job.created_by_id,
        "createdAt": job.created_at.isoformat(),
    }
    if job.started_at:
        d["startedAt"] = job.started_at.isoformat()
    if job.completed_at:
        d["completedAt"] = job.completed_at.isoformat()
    if job.status == BuildStatus.FAILED:
        d["errorMessage"] = job.error_message
    if job.warnings:
        d["warnings"] = job.warnings
    if job.status == BuildStatus.COMPLETED:
        try:
            d["artifactId"] = job.artifact.id
        except PackageArtifact.DoesNotExist:
            pass
    return d


def _snapshot_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "workspaceId": snapshot.workspace_id,
        "datasetBinding": snapshot.dataset_binding,
        "scopeCourseId": snapshot.scope_course_id,
        "filters": snapshot.filters,
        "includeAnswers": snapshot.include_answers,
        "identifiable": snapshot.identifiable,
        "rowCount": snapshot.row_count,
        "fileSize": snapshot.file_size,
        "checksumSha256": snapshot.checksum_sha256,
        "status": snapshot.status,
        "errorMessage": snapshot.error_message,
        "metadata": snapshot.metadata,
        "expiresAt": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "createdAt": snapshot.created_at.isoformat(),
        "createdBy": snapshot.created_by_id,
    }


# ── PKG-UC-01: Create / Get workspace ───────────────────────────────


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def workspace_list_create_view(request):
    """GET/POST /api/v1/packages/workspaces"""
    if request.method == "GET":
        qs = PackageWorkspace.objects.all()
        user = request.user
        if user.is_staff or has_role(user, Role.RESEARCHER):
            pass  # full access
        else:
            qs = qs.filter(created_by=user)
        qs = qs.order_by("-updated_at")
        return Response([_workspace_to_dict(ws) for ws in qs])

    # POST
    ser = CreateWorkspaceSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ws = create_workspace(request.user, ser.validated_data)
    return Response(_workspace_to_dict(ws), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def workspace_detail(request, workspace_id):
    """GET/PATCH/DELETE /api/v1/packages/workspaces/{workspaceId}"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    _cleanup_legacy_cross_course_nodes(ws)

    if request.method == "GET":
        return Response(_workspace_to_dict(ws))

    if request.method == "DELETE":
        from .models import PackageAuditLog

        PackageAuditLog.objects.create(
            actor=request.user,
            action=PkgAuditAction.WORKSPACE_DELETE,
            metadata={"workspace_id": ws.id, "workspace_name": ws.name},
            outcome=PkgAuditOutcome.SUCCESS,
        )
        ws.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    ser = UpdateWorkspaceSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ws = update_workspace(request.user, ws, ser.validated_data)
    return Response(_workspace_to_dict(ws))


# ── PKG-UC-02: Manage nodes ─────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def add_node_view(request, workspace_id):
    """POST /api/v1/packages/workspaces/{workspaceId}/nodes"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    ser = AddNodeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    payload = dict(ser.validated_data)

    snapshot_id = payload.get("snapshotId")
    source_type = payload.get("sourceType")
    if snapshot_id is not None:
        snapshot = ws.snapshots.filter(id=snapshot_id).first()
        if not snapshot:
            return Response(
                {"detail": "snapshotId not found in this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if snapshot.status in (SnapshotStatus.EXPIRED, SnapshotStatus.FAILED):
            return Response(
                {"detail": f"Snapshot {snapshot.id} is not usable ({snapshot.status})"},
                status=status.HTTP_409_CONFLICT,
            )
        if source_type == "SNAPSHOT":
            payload["datasetBinding"] = snapshot.dataset_binding
            payload["bindingCourseId"] = snapshot.scope_course_id
            payload["identifiable"] = snapshot.identifiable
            payload["includeAnswers"] = snapshot.include_answers

    # Validate parent belongs to this workspace
    parent_id = payload.get("parentId")
    if parent_id is not None:
        if not ws.nodes.filter(id=parent_id).exists():
            return Response(
                {"detail": "Parent node not found in this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    node = add_node(request.user, ws, payload)
    return Response(_node_to_dict(node), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def node_detail(request, workspace_id, node_id):
    """PATCH/DELETE /api/v1/packages/workspaces/{workspaceId}/nodes/{nodeId}"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    node = ws.nodes.filter(id=node_id).first()
    if not node:
        return Response({"detail": "Node not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        delete_node(request.user, node)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    ser = UpdateNodeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    payload = dict(ser.validated_data)
    snapshot_id = payload.get("snapshotId")
    source_type = payload.get("sourceType")
    if snapshot_id is not None:
        snapshot = ws.snapshots.filter(id=snapshot_id).first()
        if not snapshot:
            return Response(
                {"detail": "snapshotId not found in this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if snapshot.status in (SnapshotStatus.EXPIRED, SnapshotStatus.FAILED):
            return Response(
                {"detail": f"Snapshot {snapshot.id} is not usable ({snapshot.status})"},
                status=status.HTTP_409_CONFLICT,
            )
        if source_type == "SNAPSHOT":
            payload["datasetBinding"] = snapshot.dataset_binding
            payload["bindingCourseId"] = snapshot.scope_course_id
            payload["identifiable"] = snapshot.identifiable
            payload["includeAnswers"] = snapshot.include_answers

    node = update_node(request.user, node, payload)
    return Response(_node_to_dict(node))


# ── Snapshots ────────────────────────────────────────────────────────


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def snapshot_list_create_view(request, workspace_id):
    """GET/POST /api/v1/packages/workspaces/{workspaceId}/snapshots"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    if request.method == "GET":
        from .services import list_snapshots
        snapshots = list_snapshots(ws)
        return Response([_snapshot_to_dict(s) for s in snapshots])

    # POST — create snapshot
    ser = CreateSnapshotSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    from .services import create_snapshot
    try:
        snapshot = create_snapshot(
            request.user,
            ws,
            dataset_binding=ser.validated_data["datasetBinding"],
            scope_course_id=ser.validated_data.get("scopeCourseId"),
            filters=ser.validated_data.get("filters"),
            include_answers=ser.validated_data.get("includeAnswers", False),
            identifiable=ser.validated_data.get("identifiable", False),
        )
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(_snapshot_to_dict(snapshot), status=status.HTTP_201_CREATED)


# ── Node Reorder ─────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def reorder_node_view(request, workspace_id):
    """POST /api/v1/packages/workspaces/{workspaceId}/nodes/reorder"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    ser = ReorderNodeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    moved_node_id = ser.validated_data["movedNodeId"]
    target_parent_id = ser.validated_data.get("targetParentId")
    target_order_index = ser.validated_data["targetOrderIndex"]

    # Validate moved node exists
    moved_node = ws.nodes.filter(id=moved_node_id).first()
    if not moved_node:
        return Response({"detail": "Moved node not found"}, status=status.HTTP_404_NOT_FOUND)

    # Validate target parent
    if target_parent_id is not None:
        target_parent = ws.nodes.filter(id=target_parent_id).first()
        if not target_parent:
            return Response(
                {"detail": "Target parent not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target_parent.node_type != "FOLDER":
            return Response(
                {"detail": "Target parent must be a folder"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check for cyclic move — can't move a folder into its own descendant
        if moved_node.node_type == "FOLDER":
            if _is_descendant_of(target_parent_id, moved_node_id, ws):
                return Response(
                    {"detail": "Cannot move folder into its own descendant"},
                    status=status.HTTP_409_CONFLICT,
                )

    from .services import reorder_node
    reorder_node(
        request.user,
        ws,
        moved_node=moved_node,
        target_parent_id=target_parent_id,
        target_order_index=target_order_index,
    )

    return Response(_workspace_to_dict(ws))


def _is_descendant_of(node_id: int, ancestor_id: int, workspace) -> bool:
    """Check if node_id is a descendant of ancestor_id in the workspace tree."""
    nodes = {n.id: n for n in workspace.nodes.all()}
    current = nodes.get(node_id)
    while current:
        if current.id == ancestor_id:
            return True
        current = nodes.get(current.parent_id)
    return False


# ── PKG-UC-03: Validate ─────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def validate_workspace_view(request, workspace_id):
    """POST /api/v1/packages/workspaces/{workspaceId}/validate"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    _cleanup_legacy_cross_course_nodes(ws)

    ser = ValidateWorkspaceSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    result = validate_workspace(
        ws,
        request.user,
        strict_mode=ser.validated_data.get("strictMode", True),
        snapshot_id=ser.validated_data.get("snapshotId"),
    )

    # Log audit
    from .models import PackageAuditLog
    PackageAuditLog.objects.create(
        actor=request.user,
        action=PkgAuditAction.VALIDATE,
        workspace=ws,
        metadata=result.to_dict(),
        outcome=PkgAuditOutcome.SUCCESS if result.valid else PkgAuditOutcome.FAILURE,
    )

    if not result.valid:
        return Response(result.to_dict(), status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response(result.to_dict())


# ── PKG-UC-04: Build ────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def build_workspace_view(request, workspace_id):
    """POST /api/v1/packages/workspaces/{workspaceId}/build"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    _cleanup_legacy_cross_course_nodes(ws)

    ser = BuildWorkspaceSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    job = create_build_job(
        request.user,
        ws,
        strict_mode=ser.validated_data.get("strictMode", True),
        snapshot_id=ser.validated_data.get("snapshotId"),
    )

    # Execute synchronously for now (async upgrade is future work)
    job = run_build(
        job,
        include_metadata_files=ser.validated_data.get("includeMetadataFiles", True),
    )

    if job.status == BuildStatus.FAILED:
        return Response(_job_to_dict(job), status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response(_job_to_dict(job), status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def job_detail(request, job_id):
    """GET /api/v1/packages/jobs/{jobId}"""
    job = PackageBuildJob.objects.filter(id=job_id).first()
    if not job:
        return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    # Scope check via workspace
    access_err = _check_workspace_access(request.user, job.workspace)
    if access_err:
        return access_err

    return Response(_job_to_dict(job))


# ── PKG-UC-05: Download artifact ────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsTeacherOrAbove])
def download_artifact(request, artifact_id):
    """GET /api/v1/packages/artifacts/{artifactId}/download"""
    artifact = PackageArtifact.objects.select_related(
        "build_job__workspace"
    ).filter(id=artifact_id).first()

    if not artifact:
        return Response({"detail": "Artifact not found"}, status=status.HTTP_404_NOT_FOUND)

    # Expiry check (410 Gone)
    if artifact.expires_at and artifact.expires_at < timezone.now():
        log_download_audit(
            request.user,
            artifact.build_job.workspace,
            artifact,
            outcome=PkgAuditOutcome.FAILURE,
        )
        return Response({"detail": "Artifact expired"}, status=status.HTTP_410_GONE)

    # Scope check
    access_err = _check_workspace_access(request.user, artifact.build_job.workspace)
    if access_err:
        log_download_audit(
            request.user,
            artifact.build_job.workspace,
            artifact,
            outcome=PkgAuditOutcome.DENIED,
        )
        return access_err

    # File existence check
    if not os.path.exists(artifact.file_path):
        return Response({"detail": "Artifact file missing"}, status=status.HTTP_404_NOT_FOUND)

    log_download_audit(request.user, artifact.build_job.workspace, artifact)

    return FileResponse(
        open(artifact.file_path, "rb"),
        as_attachment=True,
        filename=os.path.basename(artifact.file_path),
        content_type="application/zip",
    )
