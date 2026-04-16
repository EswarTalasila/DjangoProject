"""FR-14 Lifecycle and Archival integration tests.

Tests verify archive/restore/purge behaviour across all ARCH-managed
entities (AssignmentTemplate, Assignment, Course) through the REST API.

Naming convention per FR-14 Section 8:
  - test_ARCH_UC_##      : use-case coverage
  - test_ARCH_UC_##_E#   : error-path coverage
  - test_ARCH_CN_##      : constraint coverage
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, TeacherProfile, UserRole
from assignment_templates.models import AssignmentTemplateStatus
from assignments.models import AssignmentArchiveArtifact, AssignmentStatus
from core.models import AuditAction, AuditLog, AuditOutcome
from courses.models import CourseStatus, Enrollment, EnrollmentStatus
from submissions.models import SubmissionStatus
from tests.factories import (
    AssignmentTemplateFactory,
    AssignmentFactory,
    CourseFactory,
    SubmissionFactory,
    TeacherProfileFactory,
    UserFactory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def teacher_client(teacher_user, api_client):
    api_client.force_authenticate(user=teacher_user)
    return api_client


@pytest.fixture
def admin_client(admin_user, api_client):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def researcher_client(researcher_user, api_client):
    api_client.force_authenticate(user=researcher_user)
    return api_client


@pytest.fixture
def student_client(student_user):
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


@pytest.fixture
def teacher_course(teacher_user):
    tp = TeacherProfile.objects.get(user=teacher_user)
    return CourseFactory(teacher_profile=tp)


@pytest.fixture
def assignment_template():
    return AssignmentTemplateFactory()


@pytest.fixture
def teacher_assignment(teacher_user, teacher_course, assignment_template):
    return AssignmentFactory(
        created_by=teacher_user,
        course=teacher_course,
        assignment_template=assignment_template,
    )


# ---------------------------------------------------------------------------
# ARCH-UC-01 — Archive AssignmentTemplate Template
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_01:
    """Archive assignment_template template."""

    def test_ARCH_UC_01_ADMIN(self, admin_client, assignment_template):
        """Admin can archive an assignment_template."""
        resp = admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert resp.status_code == status.HTTP_200_OK
        assignment_template.refresh_from_db()
        assert assignment_template.status == AssignmentTemplateStatus.ARCHIVED
        assert assignment_template.archived_at is not None

    def test_ARCH_UC_01_RESEARCHER(self, researcher_client, assignment_template):
        """Researcher can archive an assignment_template."""
        resp = researcher_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert resp.status_code == status.HTTP_200_OK

    def test_ARCH_UC_01_E1_not_found(self, admin_client):
        """404 for non-existent assignment_template."""
        resp = admin_client.post("/api/v1/assignment-templates/99999/archive")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ARCH_UC_01_E2_teacher_forbidden(self, teacher_client, assignment_template):
        """Teacher cannot archive assignment_templates."""
        resp = teacher_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ARCH_UC_01_E3_already_archived(self, admin_client, assignment_template):
        """409 when assignment_template already archived."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        resp = admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-UC-02 — Archive Assignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_02:
    """Archive assignment."""

    def test_ARCH_UC_02_TEACHER_owner(self, teacher_client, teacher_assignment):
        """Teacher-owner can archive their assignment."""
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/archive")
        assert resp.status_code == status.HTTP_200_OK
        teacher_assignment.refresh_from_db()
        assert teacher_assignment.status == AssignmentStatus.ARCHIVED

    def test_ARCH_UC_02_ADMIN_override(self, admin_client, teacher_assignment):
        """Admin can archive any assignment."""
        resp = admin_client.post(f"/api/v1/assignments/{teacher_assignment.id}/archive")
        assert resp.status_code == status.HTTP_200_OK

    def test_ARCH_UC_02_E2_not_owner(self, teacher_assignment):
        """Non-owner teacher gets 403."""
        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        client = APIClient()
        client.force_authenticate(user=other_teacher)
        resp = client.post(f"/api/v1/assignments/{teacher_assignment.id}/archive")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ARCH_UC_02_E3_already_archived(self, teacher_client, teacher_assignment):
        """409 when assignment already archived."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/archive")
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-UC-03 — Archive Course
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_03:
    """Archive course."""

    def test_ARCH_UC_03_TEACHER_owner(self, teacher_client, teacher_course):
        """Teacher-owner can archive their course."""
        resp = teacher_client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        assert resp.status_code == status.HTTP_200_OK
        teacher_course.refresh_from_db()
        assert teacher_course.status == CourseStatus.ARCHIVED

    def test_ARCH_UC_03_ADMIN_override(self, admin_client, teacher_course):
        """Admin can archive any course."""
        resp = admin_client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        assert resp.status_code == status.HTTP_200_OK

    def test_ARCH_UC_03_E1_not_found(self, teacher_client):
        """404 for non-existent course."""
        resp = teacher_client.post("/api/v1/courses/99999/archive")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ARCH_UC_03_E2_not_owner(self, teacher_course):
        """Non-owner teacher gets 403."""
        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other)
        client = APIClient()
        client.force_authenticate(user=other)
        resp = client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ARCH_UC_03_E3_already_archived(self, teacher_client, teacher_course):
        """409 when course already archived."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-UC-04 — Restore Archived Entity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_04:
    """Restore archived entities."""

    def test_ARCH_UC_04_restore_course(self, teacher_client, teacher_user, teacher_course):
        """Restore an archived course."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.archived_at = timezone.now()
        teacher_course.archived_by = teacher_user
        teacher_course.save()
        resp = teacher_client.post(f"/api/v1/courses/{teacher_course.id}/restore")
        assert resp.status_code == status.HTTP_200_OK
        teacher_course.refresh_from_db()
        assert teacher_course.status == CourseStatus.ACTIVE

    def test_ARCH_UC_04_restore_assignment_template(self, admin_client, admin_user, assignment_template):
        """Restore an archived assignment_template."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.archived_at = timezone.now()
        assignment_template.archived_by = admin_user
        assignment_template.save()
        resp = admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/restore")
        assert resp.status_code == status.HTTP_200_OK
        assignment_template.refresh_from_db()
        assert assignment_template.status == AssignmentTemplateStatus.ACTIVE

    def test_ARCH_UC_04_restore_assignment(
        self, teacher_client, teacher_user, teacher_assignment
    ):
        """Restore an archived assignment."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.archived_by = teacher_user
        teacher_assignment.save()
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/restore")
        assert resp.status_code == status.HTTP_200_OK
        teacher_assignment.refresh_from_db()
        assert teacher_assignment.status == AssignmentStatus.ACTIVE

    def test_ARCH_UC_04_E3_not_archived(self, teacher_client, teacher_course):
        """409 when trying to restore an ACTIVE entity."""
        resp = teacher_client.post(f"/api/v1/courses/{teacher_course.id}/restore")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_ARCH_UC_04_E4_restore_assignment_blocked_by_course(
        self, teacher_client, teacher_user, teacher_assignment
    ):
        """409 when restoring assignment whose course is archived (ARCH-CN-14)."""
        teacher_assignment.course.status = CourseStatus.ARCHIVED
        teacher_assignment.course.save()
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.archived_by = teacher_user
        teacher_assignment.save()
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/restore")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "course" in resp.json()["detail"].lower()

    def test_ARCH_UC_04_E4_restore_assignment_blocked_by_assignment_template(
        self, teacher_client, teacher_user, teacher_assignment
    ):
        """409 when restoring assignment whose assignment_template is archived (ARCH-CN-14)."""
        teacher_assignment.assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        teacher_assignment.assignment_template.save()
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.archived_by = teacher_user
        teacher_assignment.save()
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/restore")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "assignment template" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# ARCH-UC-05 — List and Filter Archived Records
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_05:
    """Default active-only list filtering and includeArchived opt-in."""

    def test_ARCH_UC_05_courses_default_excludes_archived(
        self, admin_client, teacher_course
    ):
        """Default course list excludes archived courses."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = admin_client.get("/api/v1/courses/")
        assert resp.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in resp.json()["results"]]
        assert teacher_course.id not in ids

    def test_ARCH_UC_05_courses_include_archived(self, admin_client, teacher_course):
        """includeArchived=true includes archived courses."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = admin_client.get("/api/v1/courses/?includeArchived=true")
        assert resp.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in resp.json()["results"]]
        assert teacher_course.id in ids

    def test_ARCH_UC_05_assignment_templates_default_excludes_archived(
        self, admin_client, assignment_template
    ):
        """Default assignment_template list excludes archived."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        resp = admin_client.get("/api/v1/assignment-templates/")
        ids = [a["id"] for a in resp.json()["results"]]
        assert assignment_template.id not in ids

    def test_ARCH_UC_05_assignment_templates_include_archived(self, admin_client, assignment_template):
        """includeArchived=true includes archived assignment_templates."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        resp = admin_client.get("/api/v1/assignment-templates/?includeArchived=true")
        ids = [a["id"] for a in resp.json()["results"]]
        assert assignment_template.id in ids

    def test_ARCH_UC_05_assignments_default_excludes_archived(
        self, admin_client, teacher_assignment
    ):
        """Default assignment list for course excludes archived."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        course_id = teacher_assignment.course_id
        resp = admin_client.get(f"/api/v1/assignments/courses/{course_id}")
        ids = [a["id"] for a in resp.json()["results"]]
        assert teacher_assignment.id not in ids

    def test_ARCH_UC_05_assignments_include_archived(
        self, admin_client, teacher_assignment
    ):
        """includeArchived=true includes archived assignments."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        course_id = teacher_assignment.course_id
        resp = admin_client.get(
            f"/api/v1/assignments/courses/{course_id}?includeArchived=true"
        )
        ids = [a["id"] for a in resp.json()["results"]]
        assert teacher_assignment.id in ids

    def test_ARCH_UC_05_E2_invalid_include_archived_courses(
        self, admin_client, teacher_course
    ):
        """Invalid includeArchived value returns 400 for courses."""
        resp = admin_client.get("/api/v1/courses/?includeArchived=foo")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_ARCH_UC_05_E2_invalid_include_archived_assignment_templates(
        self, admin_client, assignment_template
    ):
        """Invalid includeArchived value returns 400 for assignment_templates."""
        resp = admin_client.get("/api/v1/assignment-templates/?includeArchived=foo")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_ARCH_UC_05_E2_invalid_include_archived_assignments(
        self, admin_client, teacher_assignment
    ):
        """Invalid includeArchived value returns 400 for assignments."""
        course_id = teacher_assignment.course_id
        resp = admin_client.get(f"/api/v1/assignments/courses/{course_id}?includeArchived=foo")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# ARCH-UC-06 — Purge Archived Entity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_06:
    """Purge (hard delete) archived entities."""

    def test_ARCH_UC_06_admin_purge_course(self, admin_client, teacher_course):
        """Admin can purge an archived course."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = admin_client.delete(f"/api/v1/courses/{teacher_course.id}?purge=true")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_ARCH_UC_06_admin_purge_assignment_template(self, admin_client, assignment_template):
        """Admin can purge an archived assignment_template when lifecycle eligibility checks pass."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        resp = admin_client.delete(f"/api/v1/assignment-templates/{assignment_template.id}?purge=true")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_ARCH_UC_06_admin_purge_assignment(self, admin_client, teacher_assignment):
        """Admin can purge an archived assignment with no progressed submissions."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        resp = admin_client.delete(
            f"/api/v1/assignments/{teacher_assignment.id}?purge=true"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_ARCH_UC_06_assignment_archive_bundle_generation_and_download(
        self,
        teacher_client,
        teacher_assignment,
        settings,
        tmp_path,
    ):
        """Archived assignments can generate and download a human-readable archive bundle."""
        settings.ARTIFACT_ROOT = tmp_path / "artifacts"
        Path(settings.ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)

        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.save(update_fields=["status", "archived_at"])

        generate = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle"
        )
        assert generate.status_code == status.HTTP_201_CREATED
        payload = generate.json()
        assert payload["assignmentId"] == teacher_assignment.id
        assert payload["identifiable"] is True
        assert payload["filename"].endswith(".zip")

        artifact = AssignmentArchiveArtifact.objects.get(assignment=teacher_assignment)
        assert Path(artifact.file_path).exists()

        download = teacher_client.get(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle/download"
        )
        assert download.status_code == status.HTTP_200_OK
        archive = ZipFile(io.BytesIO(b"".join(download.streaming_content)))
        names = set(archive.namelist())
        assert any(name.endswith("manifest.json") for name in names)
        assert any(name.endswith("template/template.json") for name in names)
        assert any(name.endswith("assignment/assignment.json") for name in names)
        assert any(name.endswith("assignment/submissions.csv") for name in names)

    def test_ARCH_UC_06_archive_bundle_preserves_teacher_added_content(
        self,
        teacher_client,
        teacher_assignment,
        settings,
        tmp_path,
    ):
        """Archived assignment bundles include teacher-added questions and rubric extensions."""
        settings.ARTIFACT_ROOT = tmp_path / "artifacts"
        Path(settings.ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)

        question_resp = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/questions",
            {
                "type": "SHORT_ANSWER",
                "prompt": "Explain the teacher extension.",
                "maxPoints": 5,
            },
            format="json",
        )
        assert question_resp.status_code == status.HTTP_201_CREATED

        criterion_resp = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/teacher-criteria",
            {
                "title": "Teacher commentary",
                "description": "Extension criterion",
                "weight": 0.25,
            },
            format="json",
        )
        assert criterion_resp.status_code == status.HTTP_201_CREATED
        criterion_id = criterion_resp.json()["teacherCriteria"][0]["id"]

        level_resp = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/teacher-criteria/{criterion_id}/levels",
            {
                "label": "Added level",
                "description": "Teacher-owned rubric level",
                "points": 2,
            },
            format="json",
        )
        assert level_resp.status_code == status.HTTP_201_CREATED

        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.save(update_fields=["status", "archived_at"])

        generate = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle"
        )
        assert generate.status_code == status.HTTP_201_CREATED

        download = teacher_client.get(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle/download"
        )
        assert download.status_code == status.HTTP_200_OK

        archive = ZipFile(io.BytesIO(b"".join(download.streaming_content)))
        content_name = next(
            name for name in archive.namelist() if name.endswith("assignment/content.json")
        )
        content = json.loads(archive.read(content_name).decode("utf-8"))

        prompts = [question["prompt"] for question in content["questions"]]
        assert "Explain the teacher extension." in prompts
        teacher_criteria = content["teacherCriteria"]
        assert [criterion["title"] for criterion in teacher_criteria] == ["Teacher commentary"]
        assert teacher_criteria[0]["levels"][0]["label"] == "Added level"

    def test_ARCH_UC_06_archive_bundle_uses_frozen_template_snapshot(
        self,
        teacher_client,
        teacher_assignment,
        settings,
        tmp_path,
    ):
        """Archived bundles keep the template metadata captured when the assignment was created."""
        settings.ARTIFACT_ROOT = tmp_path / "artifacts"
        Path(settings.ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)

        original_title = teacher_assignment.assignment_template.title
        teacher_assignment.assignment_template.category = "Original category"
        teacher_assignment.assignment_template.save(update_fields=["category"])

        teacher_assignment.assignment_template.title = "Mutated researcher title"
        teacher_assignment.assignment_template.category = "Mutated category"
        teacher_assignment.assignment_template.save(update_fields=["title", "category"])

        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.save(update_fields=["status", "archived_at"])

        generate = teacher_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle"
        )
        assert generate.status_code == status.HTTP_201_CREATED

        download = teacher_client.get(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle/download"
        )
        assert download.status_code == status.HTTP_200_OK

        archive = ZipFile(io.BytesIO(b"".join(download.streaming_content)))
        template_name = next(
            name for name in archive.namelist() if name.endswith("template/template.json")
        )
        content_name = next(
            name for name in archive.namelist() if name.endswith("assignment/content.json")
        )
        template_payload = json.loads(archive.read(template_name).decode("utf-8"))
        content_payload = json.loads(archive.read(content_name).decode("utf-8"))

        assert template_payload["title"] == original_title
        assert template_payload["category"] == "Original category"
        assert content_payload["assignmentTemplateTitle"] == original_title
        assert content_payload["category"] == "Original category"

    def test_ARCH_UC_06_purging_assignment_removes_archive_bundle(
        self,
        admin_client,
        teacher_assignment,
        settings,
        tmp_path,
    ):
        """Purging an archived assignment also deletes its generated archive bundle."""
        settings.ARTIFACT_ROOT = tmp_path / "artifacts"
        Path(settings.ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)

        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.save(update_fields=["status", "archived_at"])

        artifact = admin_client.post(
            f"/api/v1/assignments/{teacher_assignment.id}/archive-bundle"
        )
        assert artifact.status_code == status.HTTP_201_CREATED
        file_path = Path(AssignmentArchiveArtifact.objects.get(assignment=teacher_assignment).file_path)
        assert file_path.exists()

        purge = admin_client.delete(f"/api/v1/assignments/{teacher_assignment.id}?purge=true")
        assert purge.status_code == status.HTTP_204_NO_CONTENT
        assert not AssignmentArchiveArtifact.objects.filter(
            assignment_id=teacher_assignment.id
        ).exists()
        assert not file_path.exists()

    def test_ARCH_UC_06_E1_non_admin_forbidden(self, teacher_client, teacher_course):
        """Non-admin purge returns 403."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.delete(f"/api/v1/courses/{teacher_course.id}?purge=true")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ARCH_UC_06_E2_not_archived(self, admin_client, teacher_course):
        """409 when entity is not archived."""
        resp = admin_client.delete(f"/api/v1/courses/{teacher_course.id}?purge=true")
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-UC-07 — Audit Lifecycle Mutations
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_07:
    """Audit records emitted for lifecycle mutations."""

    def test_ARCH_UC_07_archive_emits_audit(self, admin_client, assignment_template):
        """Archive creates an audit log entry."""
        admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert AuditLog.objects.filter(
            action=AuditAction.ARCHIVE,
            target_resource_type="AssignmentTemplate",
            target_resource_id=assignment_template.id,
        ).exists()

    def test_ARCH_UC_07_restore_emits_audit(self, admin_client, admin_user, assignment_template):
        """Restore creates an audit log entry."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.archived_at = timezone.now()
        assignment_template.archived_by = admin_user
        assignment_template.save()
        admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/restore")
        assert AuditLog.objects.filter(
            action=AuditAction.RESTORE,
            target_resource_type="AssignmentTemplate",
            target_resource_id=assignment_template.id,
        ).exists()

    def test_ARCH_UC_07_purge_emits_audit(self, admin_client, assignment_template):
        """Purge creates an audit log entry."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        admin_client.delete(f"/api/v1/assignment-templates/{assignment_template.id}?purge=true")
        assert AuditLog.objects.filter(
            action=AuditAction.PURGE,
            target_resource_type="AssignmentTemplate",
        ).exists()

    def test_ARCH_CN_09_audit_has_status_transition(self, admin_client, assignment_template):
        """Lifecycle audit payload includes old/new status values."""
        admin_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        row = AuditLog.objects.filter(
            action=AuditAction.ARCHIVE,
            target_resource_type="AssignmentTemplate",
            target_resource_id=assignment_template.id,
        ).order_by("-id").first()
        assert row is not None
        assert row.old_value == {"status": "ACTIVE"}
        assert row.new_value == {"status": "ARCHIVED"}

    def test_ARCH_CN_09_denied_archive_emits_audit(self, teacher_client, assignment_template):
        """Denied lifecycle attempts are audited with DENIED outcome."""
        resp = teacher_client.post(f"/api/v1/assignment-templates/{assignment_template.id}/archive")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        row = AuditLog.objects.filter(
            action=AuditAction.ARCHIVE,
            target_resource_type="AssignmentTemplate",
            target_resource_id=assignment_template.id,
        ).order_by("-id").first()
        assert row is not None
        assert row.outcome == AuditOutcome.DENIED


# ---------------------------------------------------------------------------
# ARCH-CN-03 — Archived AssignmentTemplate Blocks Assignment Creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_03:
    """Archived assignment_template blocks new assignment creation."""

    def test_ARCH_CN_03_assignment_create_blocked(
        self, teacher_client, teacher_user, teacher_course, assignment_template
    ):
        """409 when creating assignment from archived assignment_template."""
        assignment_template.status = AssignmentTemplateStatus.ARCHIVED
        assignment_template.save()
        resp = teacher_client.post(
            "/api/v1/assignments/",
            {
                "assignmentTemplateId": assignment_template.id,
                "audienceType": "COURSE",
                "courseId": teacher_course.id,
                "openAt": timezone.now().isoformat(),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-CN-05 — Archived Course Blocks Course Mutations
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_05:
    """Archived course blocks enrollment and assignment mutations."""

    def test_ARCH_CN_05_create_assignment_blocked(
        self, teacher_client, teacher_course, assignment_template
    ):
        """409 when creating assignment for archived course."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.post(
            "/api/v1/assignments/",
            {
                "assignmentTemplateId": assignment_template.id,
                "audienceType": "COURSE",
                "courseId": teacher_course.id,
                "openAt": timezone.now().isoformat(),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_ARCH_CN_05_add_student_blocked(
        self, teacher_client, teacher_course
    ):
        """409 when adding a student to archived course."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.post(
            f"/api/v1/courses/{teacher_course.id}/students",
            {"name": "Blocked Student", "consent": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_ARCH_CN_05_remove_student_blocked(
        self, teacher_client, teacher_course, student_user
    ):
        """409 when removing student from archived course."""
        Enrollment.objects.create(
            course=teacher_course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.delete(
            f"/api/v1/courses/{teacher_course.id}/students/{student_user.id}"
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-CN-07 — Purge Eligibility Gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_07:
    """Purge blocked by dependency rules."""

    def test_ARCH_CN_07_purge_assignment_template_with_assignments(
        self, admin_client, teacher_assignment
    ):
        """Cannot purge assignment_template while live assignments still depend on it."""
        asmt = teacher_assignment.assignment_template
        asmt.status = AssignmentTemplateStatus.ARCHIVED
        asmt.save()
        resp = admin_client.delete(f"/api/v1/assignment-templates/{asmt.id}?purge=true")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_ARCH_CN_07_purge_course_with_active_assignments(
        self, admin_client, teacher_assignment
    ):
        """Cannot purge course that has active assignments."""
        course = teacher_assignment.course
        course.status = CourseStatus.ARCHIVED
        course.save()
        # Assignment is still ACTIVE
        resp = admin_client.delete(f"/api/v1/courses/{course.id}?purge=true")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_ARCH_CN_07_purge_assignment_with_progressed_submissions(
        self, admin_client, teacher_assignment
    ):
        """Cannot purge assignment with progressed submissions."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        SubmissionFactory(
            assignment=teacher_assignment, status=SubmissionStatus.IN_PROGRESS
        )
        resp = admin_client.delete(
            f"/api/v1/assignments/{teacher_assignment.id}?purge=true"
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-CN-13 — Course Archive Cascade Policy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_13:
    """Course archive cascades to active assignments."""

    def test_ARCH_CN_13_cascade_archives_assignments(
        self, teacher_client, teacher_user, teacher_course, assignment_template
    ):
        """Archiving a course cascade-archives its ACTIVE assignments."""
        a1 = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assignment_template=assignment_template
        )
        a2 = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assignment_template=assignment_template
        )
        resp = teacher_client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        assert resp.status_code == status.HTTP_200_OK
        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a1.status == AssignmentStatus.ARCHIVED
        assert a2.status == AssignmentStatus.ARCHIVED
        assert a1.archived_at is not None
        assert a2.archived_at is not None


# ---------------------------------------------------------------------------
# ARCH-CN-14 — Restore Preconditions and Non-cascade Policy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_14:
    """Restore preconditions and non-cascade behaviour."""

    def test_ARCH_CN_14_course_restore_does_not_restore_assignments(
        self, teacher_client, teacher_user, teacher_course, assignment_template
    ):
        """Restoring a course does NOT cascade-restore its assignments."""
        asgn = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assignment_template=assignment_template
        )
        # Archive course (cascades to assignments)
        teacher_client.post(f"/api/v1/courses/{teacher_course.id}/archive")
        asgn.refresh_from_db()
        assert asgn.status == AssignmentStatus.ARCHIVED

        # Restore course
        teacher_client.post(f"/api/v1/courses/{teacher_course.id}/restore")
        teacher_course.refresh_from_db()
        assert teacher_course.status == CourseStatus.ACTIVE

        # Assignment remains archived
        asgn.refresh_from_db()
        assert asgn.status == AssignmentStatus.ARCHIVED
