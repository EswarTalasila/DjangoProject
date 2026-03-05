"""FR-16 Packaging Workspace integration tests — v5 traceability naming.

Covers:
    PKG-UC-01  Create / retrieve workspace
    PKG-UC-02  Manage nodes (add / update / delete)
    PKG-UC-03  Validate workspace
    PKG-UC-04  Build workspace
    PKG-UC-05  Download artifact
    PKG-CN-01  Node-level permissions
    PKG-CN-03  Cap checks
    PKG-CN-04  Manifest / checksums
    PKG-CN-06  Strict vs partial build
    PKG-CN-08  Deterministic paths / duplicate rejection
"""

import json
import zipfile
from io import BytesIO

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, SudoPermission, TeacherProfile, UserRole
from packages.models import (
    BuildStatus,
    DatasetBinding,
    NodeType,
    PackageArtifact,
    PackageAuditLog,
    PackageBuildJob,
    PackageWorkspace,
    PkgAuditAction,
    WorkspaceStatus,
)
from tests.factories import (
    CourseFactory,
    EnrollmentFactory,
    StudentProfileFactory,
    SudoGrantFactory,
    UserFactory,
)

WS_URL = "/api/v1/packages/workspaces"


# ── Helpers ──────────────────────────────────────────────────────────


def _create_workspace(client, name="Test Package", **extra):
    payload = {"name": name, **extra}
    return client.post(WS_URL, payload, format="json")


def _add_node(client, ws_id, **payload):
    return client.post(f"{WS_URL}/{ws_id}/nodes", payload, format="json")


def _seed_workspace_tree(client, ws_id, course_id):
    """Build a minimal root folder + one file node tree."""
    root = _add_node(
        client, ws_id, nodeType="FOLDER", label="export-root"
    )
    root_id = root.json()["id"]
    file_node = _add_node(
        client,
        ws_id,
        parentId=root_id,
        nodeType="FILE",
        label="roster.csv",
        datasetBinding="ROSTER",
        bindingCourseId=course_id,
    )
    return root_id, file_node.json()["id"]


# ═════════════════════════════════════════════════════════════════════
# PKG-UC-01 — Create & retrieve workspace
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_UC_01:
    """Create and retrieve package workspace."""

    def test_PKG_UC_01_ADMIN_create(self, api_client, admin_user):
        """Admin can create workspace; returns 201."""
        api_client.force_authenticate(user=admin_user)
        resp = _create_workspace(api_client)
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["name"] == "Test Package"
        assert body["status"] == "DRAFT"
        assert body["revision"] == 1
        assert PackageWorkspace.objects.filter(id=body["id"]).exists()

    def test_PKG_UC_01_TEACHER_create(self, api_client, teacher_user):
        """Teacher can create workspace."""
        api_client.force_authenticate(user=teacher_user)
        resp = _create_workspace(api_client, name="Teacher Pkg")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_PKG_UC_01_RESEARCHER_create(self, api_client, researcher_user):
        """Researcher can create workspace."""
        api_client.force_authenticate(user=researcher_user)
        resp = _create_workspace(api_client, name="Research Pkg")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_PKG_UC_01_E1_student_denied(self, api_client, student_user):
        """Student cannot create workspace; returns 403."""
        api_client.force_authenticate(user=student_user)
        resp = _create_workspace(api_client)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_PKG_UC_01_E2_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        resp = _create_workspace(api_client)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_PKG_UC_01_get_workspace(self, api_client, admin_user):
        """GET workspace returns full tree."""
        api_client.force_authenticate(user=admin_user)
        create_resp = _create_workspace(api_client)
        ws_id = create_resp.json()["id"]
        resp = api_client.get(f"{WS_URL}/{ws_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == ws_id
        assert resp.json()["nodes"] == []

    def test_PKG_UC_01_E3_not_found(self, api_client, admin_user):
        """GET non-existent workspace returns 404."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"{WS_URL}/99999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_01_with_scope_course(self, api_client, teacher_user):
        """Workspace can be scoped to a course."""
        tp = TeacherProfile.objects.get(user=teacher_user)
        course = CourseFactory(teacher_profile=tp)
        api_client.force_authenticate(user=teacher_user)
        resp = _create_workspace(api_client, scopeCourseId=course.id)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["scopeCourseId"] == course.id

    def test_PKG_UC_01_audit_logged(self, api_client, admin_user):
        """Workspace creation audit log entry created."""
        api_client.force_authenticate(user=admin_user)
        _create_workspace(api_client)
        assert PackageAuditLog.objects.filter(
            actor=admin_user, action=PkgAuditAction.WORKSPACE_CREATE
        ).exists()


# ═════════════════════════════════════════════════════════════════════
# PKG-UC-02 — Manage nodes
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_UC_02:
    """Manage workspace nodes (add, update, delete)."""

    def test_PKG_UC_02_add_folder_node(self, api_client, admin_user):
        """Add folder node to workspace."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = _add_node(api_client, ws["id"], nodeType="FOLDER", label="data")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["nodeType"] == "FOLDER"
        assert resp.json()["label"] == "data"

    def test_PKG_UC_02_add_file_node_with_binding(self, api_client, admin_user):
        """Add file node with dataset binding."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()
        resp = _add_node(
            api_client,
            ws["id"],
            parentId=root["id"],
            nodeType="FILE",
            label="roster.csv",
            datasetBinding="ROSTER",
            bindingCourseId=1,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["datasetBinding"] == "ROSTER"

    def test_PKG_UC_02_update_node(self, api_client, admin_user):
        """PATCH updates node label."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        node = _add_node(api_client, ws["id"], nodeType="FOLDER", label="old").json()
        resp = api_client.patch(
            f"{WS_URL}/{ws['id']}/nodes/{node['id']}",
            {"label": "new-label"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["label"] == "new-label"

    def test_PKG_UC_02_delete_node(self, api_client, admin_user):
        """DELETE removes node; returns 204."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        node = _add_node(api_client, ws["id"], nodeType="FOLDER", label="temp").json()
        resp = api_client.delete(f"{WS_URL}/{ws['id']}/nodes/{node['id']}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_PKG_UC_02_E1_node_not_found(self, api_client, admin_user):
        """PATCH non-existent node returns 404."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = api_client.patch(
            f"{WS_URL}/{ws['id']}/nodes/99999",
            {"label": "x"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_02_E2_bad_parent(self, api_client, admin_user):
        """Add node with non-existent parent returns 400."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = _add_node(
            api_client, ws["id"], parentId=99999, nodeType="FOLDER", label="orphan"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_PKG_UC_02_revision_increments(self, api_client, admin_user):
        """Adding/updating/deleting nodes increments workspace revision."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        assert ws["revision"] == 1

        node = _add_node(api_client, ws["id"], nodeType="FOLDER", label="a").json()
        ws_after = api_client.get(f"{WS_URL}/{ws['id']}").json()
        assert ws_after["revision"] == 2

        api_client.patch(
            f"{WS_URL}/{ws['id']}/nodes/{node['id']}",
            {"label": "b"},
            format="json",
        )
        ws_after2 = api_client.get(f"{WS_URL}/{ws['id']}").json()
        assert ws_after2["revision"] == 3

    def test_PKG_UC_02_workspace_patch(self, api_client, admin_user):
        """PATCH workspace updates name and increments revision."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = api_client.patch(
            f"{WS_URL}/{ws['id']}", {"name": "Updated"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["name"] == "Updated"
        assert resp.json()["revision"] == 2


# ═════════════════════════════════════════════════════════════════════
# PKG-UC-03 — Validate workspace
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_UC_03:
    """Validate workspace tree."""

    def test_PKG_UC_03_valid_tree(self, api_client, admin_user):
        """Valid tree returns 200 with valid=true."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)

        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["valid"] is True

    def test_PKG_UC_03_empty_tree(self, api_client, admin_user):
        """Empty workspace fails validation; returns 422."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = resp.json()
        assert body["valid"] is False
        codes = [v["code"] for v in body["violations"]]
        assert "EMPTY_TREE" in codes

    def test_PKG_UC_03_E1_workspace_not_found(self, api_client, admin_user):
        """Validate non-existent workspace returns 404."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            f"{WS_URL}/99999/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_03_missing_binding(self, api_client, admin_user):
        """File node without binding fails validation."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        _add_node(api_client, ws["id"], nodeType="FOLDER", label="root")
        root_id = api_client.get(f"{WS_URL}/{ws['id']}").json()["nodes"][0]["id"]
        _add_node(
            api_client,
            ws["id"],
            parentId=root_id,
            nodeType="FILE",
            label="no-binding.csv",
        )
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        codes = [v["code"] for v in resp.json()["violations"]]
        assert "MISSING_BINDING" in codes

    def test_PKG_UC_03_audit_logged(self, api_client, admin_user):
        """Validation creates audit log entry."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        api_client.post(f"{WS_URL}/{ws['id']}/validate", {}, format="json")
        assert PackageAuditLog.objects.filter(
            actor=admin_user, action=PkgAuditAction.VALIDATE
        ).exists()


# ═════════════════════════════════════════════════════════════════════
# PKG-CN-01 — Node-level permissions
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_CN_01:
    """Node-level permission enforcement."""

    def test_PKG_CN_01_identifiable_researcher_no_sudo(
        self, api_client, researcher_user, admin_user
    ):
        """Researcher without EXPORT_IDENTIFIABLE sudo cannot use identifiable=true."""
        api_client.force_authenticate(user=researcher_user)
        ws = _create_workspace(api_client).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()
        course = CourseFactory()
        _add_node(
            api_client,
            ws["id"],
            parentId=root["id"],
            nodeType="FILE",
            label="roster.csv",
            datasetBinding="ROSTER",
            bindingCourseId=course.id,
            identifiable=True,
        )
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        codes = [v["code"] for v in resp.json()["violations"]]
        assert "IDENTIFIABLE_DENIED" in codes

    def test_PKG_CN_01_identifiable_researcher_with_sudo(
        self, api_client, researcher_user, admin_user
    ):
        """Researcher with EXPORT_IDENTIFIABLE sudo can use identifiable=true."""
        SudoGrantFactory(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.EXPORT_IDENTIFIABLE.value],
        )
        api_client.force_authenticate(user=researcher_user)
        ws = _create_workspace(api_client).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()
        course = CourseFactory()
        _add_node(
            api_client,
            ws["id"],
            parentId=root["id"],
            nodeType="FILE",
            label="roster.csv",
            datasetBinding="ROSTER",
            bindingCourseId=course.id,
            identifiable=True,
        )
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/validate", {}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["valid"] is True

    def test_PKG_CN_01_teacher_scope_own_course(self, api_client, teacher_user):
        """Teacher can only reference their own courses."""
        tp = TeacherProfile.objects.get(user=teacher_user)
        own_course = CourseFactory(teacher_profile=tp)
        other_course = CourseFactory()  # Different teacher

        api_client.force_authenticate(user=teacher_user)
        ws = _create_workspace(api_client, scopeCourseId=own_course.id).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()

        # Own course — should pass
        _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="own.csv",
            datasetBinding="ROSTER", bindingCourseId=own_course.id,
        )
        # Other course — should fail
        _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="other.csv",
            datasetBinding="ROSTER", bindingCourseId=other_course.id,
        )

        resp = api_client.post(f"{WS_URL}/{ws['id']}/validate", {}, format="json")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        codes = [v["code"] for v in resp.json()["violations"]]
        assert "SCOPE_DENIED" in codes

    def test_PKG_CN_01_cross_course_binding_removed(self, api_client, teacher_user):
        """Cross-course binding is removed from package node dataset choices."""
        tp = TeacherProfile.objects.get(user=teacher_user)
        course = CourseFactory(teacher_profile=tp)
        api_client.force_authenticate(user=teacher_user)
        ws = _create_workspace(api_client, scopeCourseId=course.id).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()
        resp = _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="cross.csv",
            datasetBinding="CROSS_COURSE_SUBMISSIONS",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "datasetBinding" in str(resp.json())


# ═════════════════════════════════════════════════════════════════════
# PKG-CN-03 — Workspace access scope
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_CN_03_access:
    """Workspace access: teacher scope is owned-course only."""

    def test_PKG_CN_03_teacher_cannot_access_other_workspace(
        self, api_client, teacher_user
    ):
        """Teacher cannot GET workspace created by another user without course scope."""
        other_user = UserFactory()
        UserRole.objects.create(user=other_user, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_user)

        # Create workspace as other teacher
        api_client.force_authenticate(user=other_user)
        ws = _create_workspace(api_client).json()

        # Try to access as teacher_user
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"{WS_URL}/{ws['id']}")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_PKG_CN_03_admin_can_access_any(self, api_client, admin_user, teacher_user):
        """Admin can access any workspace."""
        api_client.force_authenticate(user=teacher_user)
        ws = _create_workspace(api_client).json()

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"{WS_URL}/{ws['id']}")
        assert resp.status_code == status.HTTP_200_OK


# ═════════════════════════════════════════════════════════════════════
# PKG-CN-08 — Deterministic paths / duplicate rejection
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_CN_08:
    """Deterministic paths and duplicate path rejection."""

    def test_PKG_CN_08_duplicate_path_rejected(self, api_client, admin_user):
        """Two file nodes with same output path fail validation."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        ws = _create_workspace(api_client).json()
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()

        # Two files with identical labels under same parent
        _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="data.csv",
            datasetBinding="ROSTER", bindingCourseId=course.id,
        )
        _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="data.csv",
            datasetBinding="ROSTER", bindingCourseId=course.id,
        )

        resp = api_client.post(f"{WS_URL}/{ws['id']}/validate", {}, format="json")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        codes = [v["code"] for v in resp.json()["violations"]]
        assert "DUPLICATE_PATH" in codes


# ═════════════════════════════════════════════════════════════════════
# PKG-UC-04 — Build workspace
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_UC_04:
    """Build workspace and produce artifact."""

    def test_PKG_UC_04_build_success(self, api_client, admin_user):
        """Successful build returns 202 with COMPLETED status and artifactId."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        # Add a student so roster has data
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)

        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build", {}, format="json"
        )
        assert resp.status_code == status.HTTP_202_ACCEPTED
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert "artifactId" in body

    def test_PKG_UC_04_build_empty_tree_fails(self, api_client, admin_user):
        """Build on empty workspace fails with 422."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build", {"strictMode": True}, format="json"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.json()["status"] == "FAILED"

    def test_PKG_UC_04_E1_workspace_not_found(self, api_client, admin_user):
        """Build on non-existent workspace returns 404."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            f"{WS_URL}/99999/build", {}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_04_job_status(self, api_client, admin_user):
        """GET job returns job details."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)

        build_resp = api_client.post(f"{WS_URL}/{ws['id']}/build", {}, format="json")
        job_id = build_resp.json()["id"]

        resp = api_client.get(f"/api/v1/packages/jobs/{job_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "COMPLETED"

    def test_PKG_UC_04_E2_job_not_found(self, api_client, admin_user):
        """GET non-existent job returns 404."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/packages/jobs/99999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_04_snapshot_mode(self, api_client, admin_user):
        """Build with snapshotId records mode=snapshot in job."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)

        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build",
            {"snapshotId": 42},
            format="json",
        )
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.json()["mode"] == "snapshot"
        assert resp.json()["snapshotId"] == 42

    def test_PKG_UC_04_build_audit_logged(self, api_client, admin_user):
        """Build creates audit log."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)
        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)
        api_client.post(f"{WS_URL}/{ws['id']}/build", {}, format="json")
        assert PackageAuditLog.objects.filter(
            actor=admin_user, action=PkgAuditAction.BUILD
        ).exists()


# ═════════════════════════════════════════════════════════════════════
# PKG-CN-04 — Manifest & Checksums
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_CN_04:
    """Artifact includes MANIFEST.json and CHECKSUMS.txt."""

    def test_PKG_CN_04_manifest_and_checksums(self, api_client, admin_user):
        """Built artifact zip contains MANIFEST.json and CHECKSUMS.txt."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)
        build_resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build", {}, format="json"
        )
        artifact_id = build_resp.json()["artifactId"]

        # Download and inspect zip
        dl_resp = api_client.get(
            f"/api/v1/packages/artifacts/{artifact_id}/download"
        )
        assert dl_resp.status_code == status.HTTP_200_OK

        # Read zip from streaming content
        content = b"".join(dl_resp.streaming_content)
        zf = zipfile.ZipFile(BytesIO(content))
        names = zf.namelist()

        assert "MANIFEST.json" in names
        assert "CHECKSUMS.txt" in names

        # Verify manifest structure
        manifest = json.loads(zf.read("MANIFEST.json"))
        assert "workspaceId" in manifest
        assert "revision" in manifest
        assert "generatedAt" in manifest
        assert "files" in manifest
        assert manifest["mode"] == "live"

        # Verify checksums file has SHA-256 entries
        checksums_text = zf.read("CHECKSUMS.txt").decode("utf-8")
        assert "MANIFEST.json" in checksums_text
        for file_entry in manifest["files"]:
            assert file_entry["path"] in checksums_text

    def test_PKG_CN_04_clean_zip_excludes_metadata_files(self, api_client, admin_user):
        """Build can produce clean ZIP without MANIFEST.json/CHECKSUMS.txt."""
        api_client.force_authenticate(user=admin_user)
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)
        build_resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build",
            {"includeMetadataFiles": False},
            format="json",
        )
        artifact_id = build_resp.json()["artifactId"]

        dl_resp = api_client.get(
            f"/api/v1/packages/artifacts/{artifact_id}/download"
        )
        assert dl_resp.status_code == status.HTTP_200_OK
        content = b"".join(dl_resp.streaming_content)
        zf = zipfile.ZipFile(BytesIO(content))
        names = zf.namelist()

        assert "MANIFEST.json" not in names
        assert "CHECKSUMS.txt" not in names


# ═════════════════════════════════════════════════════════════════════
# PKG-CN-06 — Strict vs partial build
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_CN_06:
    """strictMode=true fails entire build; strictMode=false skips invalid nodes."""

    def test_PKG_CN_06_strict_mode_fails(self, api_client, admin_user):
        """strictMode=true with invalid node fails build."""
        api_client.force_authenticate(user=admin_user)
        ws = _create_workspace(api_client).json()
        # Add root + file node without binding (will fail materialization)
        root = _add_node(api_client, ws["id"], nodeType="FOLDER", label="root").json()
        _add_node(
            api_client, ws["id"],
            parentId=root["id"], nodeType="FILE", label="bad.csv",
            # Missing binding → validation will catch
        )
        resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build",
            {"strictMode": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.json()["status"] == "FAILED"


# ═════════════════════════════════════════════════════════════════════
# PKG-UC-05 — Download artifact
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPKG_UC_05:
    """Download built artifact."""

    def _build_artifact(self, api_client, admin_user):
        """Helper: create workspace, build, return artifact_id."""
        course = CourseFactory()
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        ws = _create_workspace(api_client).json()
        _seed_workspace_tree(api_client, ws["id"], course.id)
        build_resp = api_client.post(
            f"{WS_URL}/{ws['id']}/build", {}, format="json"
        )
        return build_resp.json()["artifactId"], ws["id"]

    def test_PKG_UC_05_download(self, api_client, admin_user):
        """Download returns zip file."""
        api_client.force_authenticate(user=admin_user)
        artifact_id, _ = self._build_artifact(api_client, admin_user)
        resp = api_client.get(
            f"/api/v1/packages/artifacts/{artifact_id}/download"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/zip"
        assert "attachment" in resp.get("Content-Disposition", "")

    def test_PKG_UC_05_E1_not_found(self, api_client, admin_user):
        """Download non-existent artifact returns 404."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/packages/artifacts/99999/download")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_PKG_UC_05_E2_expired(self, api_client, admin_user):
        """Download expired artifact returns 410."""
        api_client.force_authenticate(user=admin_user)
        artifact_id, _ = self._build_artifact(api_client, admin_user)

        # Force expire
        artifact = PackageArtifact.objects.get(id=artifact_id)
        artifact.expires_at = timezone.now() - timezone.timedelta(hours=1)
        artifact.save()

        resp = api_client.get(
            f"/api/v1/packages/artifacts/{artifact_id}/download"
        )
        assert resp.status_code == status.HTTP_410_GONE

    def test_PKG_UC_05_E3_access_denied(self, api_client, admin_user, teacher_user):
        """Teacher cannot download artifact from another teacher's workspace."""
        api_client.force_authenticate(user=admin_user)
        artifact_id, _ = self._build_artifact(api_client, admin_user)

        # Create a different workspace as admin (not scoped to teacher's course)
        # Teacher should be denied since they don't own the workspace
        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)

        api_client.force_authenticate(user=other_teacher)
        resp = api_client.get(
            f"/api/v1/packages/artifacts/{artifact_id}/download"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_PKG_UC_05_download_audit(self, api_client, admin_user):
        """Download logs audit event."""
        api_client.force_authenticate(user=admin_user)
        artifact_id, _ = self._build_artifact(api_client, admin_user)
        api_client.get(f"/api/v1/packages/artifacts/{artifact_id}/download")
        assert PackageAuditLog.objects.filter(
            actor=admin_user, action=PkgAuditAction.DOWNLOAD
        ).exists()
