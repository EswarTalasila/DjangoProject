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
)
from .serializers import (
    AddNodeSerializer,
    BuildWorkspaceSerializer,
    CreateWorkspaceSerializer,
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


@api_view(["GET", "PATCH"])
@permission_classes([IsTeacherOrAbove])
def workspace_detail(request, workspace_id):
    """GET/PATCH /api/v1/packages/workspaces/{workspaceId}"""
    ws = PackageWorkspace.objects.filter(id=workspace_id).first()
    if not ws:
        return Response({"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

    access_err = _check_workspace_access(request.user, ws)
    if access_err:
        return access_err

    if request.method == "GET":
        return Response(_workspace_to_dict(ws))

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

    # Validate parent belongs to this workspace
    parent_id = ser.validated_data.get("parentId")
    if parent_id is not None:
        if not ws.nodes.filter(id=parent_id).exists():
            return Response(
                {"detail": "Parent node not found in this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    node = add_node(request.user, ws, ser.validated_data)
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
    node = update_node(request.user, node, ser.validated_data)
    return Response(_node_to_dict(node))


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

    ser = BuildWorkspaceSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    job = create_build_job(
        request.user,
        ws,
        strict_mode=ser.validated_data.get("strictMode", True),
        snapshot_id=ser.validated_data.get("snapshotId"),
    )

    # Execute synchronously for now (async upgrade is future work)
    job = run_build(job)

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
