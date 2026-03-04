"""FR-14 Lifecycle and Archival integration tests.

Tests verify archive/restore/purge behaviour across all ARCH-managed
entities (Assessment, Assignment, Course) through the REST API.

Naming convention per FR-14 Section 8:
  - test_ARCH_UC_##      : use-case coverage
  - test_ARCH_UC_##_E#   : error-path coverage
  - test_ARCH_CN_##      : constraint coverage
"""

from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, TeacherProfile, UserRole
from assessments.models import AssessmentStatus
from assignments.models import AssignmentStatus
from core.models import AuditAction, AuditLog
from courses.models import CourseStatus
from submissions.models import SubmissionStatus
from tests.factories import (
    AssessmentFactory,
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
def assessment():
    return AssessmentFactory()


@pytest.fixture
def teacher_assignment(teacher_user, teacher_course, assessment):
    return AssignmentFactory(
        created_by=teacher_user,
        course=teacher_course,
        assessment=assessment,
    )


# ---------------------------------------------------------------------------
# ARCH-UC-01 — Archive Assessment Template
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_UC_01:
    """Archive assessment template."""

    def test_ARCH_UC_01_ADMIN(self, admin_client, assessment):
        """Admin can archive an assessment."""
        resp = admin_client.post(f"/api/v1/assessments/{assessment.id}/archive")
        assert resp.status_code == status.HTTP_200_OK
        assessment.refresh_from_db()
        assert assessment.status == AssessmentStatus.ARCHIVED
        assert assessment.archived_at is not None

    def test_ARCH_UC_01_RESEARCHER(self, researcher_client, assessment):
        """Researcher can archive an assessment."""
        resp = researcher_client.post(f"/api/v1/assessments/{assessment.id}/archive")
        assert resp.status_code == status.HTTP_200_OK

    def test_ARCH_UC_01_E1_not_found(self, admin_client):
        """404 for non-existent assessment."""
        resp = admin_client.post("/api/v1/assessments/99999/archive")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ARCH_UC_01_E2_teacher_forbidden(self, teacher_client, assessment):
        """Teacher cannot archive assessments."""
        resp = teacher_client.post(f"/api/v1/assessments/{assessment.id}/archive")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ARCH_UC_01_E3_already_archived(self, admin_client, assessment):
        """409 when assessment already archived."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        resp = admin_client.post(f"/api/v1/assessments/{assessment.id}/archive")
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

    def test_ARCH_UC_04_restore_assessment(self, admin_client, admin_user, assessment):
        """Restore an archived assessment."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.archived_at = timezone.now()
        assessment.archived_by = admin_user
        assessment.save()
        resp = admin_client.post(f"/api/v1/assessments/{assessment.id}/restore")
        assert resp.status_code == status.HTTP_200_OK
        assessment.refresh_from_db()
        assert assessment.status == AssessmentStatus.ACTIVE

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

    def test_ARCH_UC_04_E4_restore_assignment_blocked_by_assessment(
        self, teacher_client, teacher_user, teacher_assignment
    ):
        """409 when restoring assignment whose assessment is archived (ARCH-CN-14)."""
        teacher_assignment.assessment.status = AssessmentStatus.ARCHIVED
        teacher_assignment.assessment.save()
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.archived_at = timezone.now()
        teacher_assignment.archived_by = teacher_user
        teacher_assignment.save()
        resp = teacher_client.post(f"/api/v1/assignments/{teacher_assignment.id}/restore")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "assessment" in resp.json()["detail"].lower()


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

    def test_ARCH_UC_05_assessments_default_excludes_archived(
        self, admin_client, assessment
    ):
        """Default assessment list excludes archived."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        resp = admin_client.get("/api/v1/assessments/")
        ids = [a["id"] for a in resp.json()["results"]]
        assert assessment.id not in ids

    def test_ARCH_UC_05_assessments_include_archived(self, admin_client, assessment):
        """includeArchived=true includes archived assessments."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        resp = admin_client.get("/api/v1/assessments/?includeArchived=true")
        ids = [a["id"] for a in resp.json()["results"]]
        assert assessment.id in ids

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

    def test_ARCH_UC_06_admin_purge_assessment(self, admin_client, assessment):
        """Admin can purge an archived assessment with no assignments."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        resp = admin_client.delete(f"/api/v1/assessments/{assessment.id}?purge=true")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_ARCH_UC_06_admin_purge_assignment(self, admin_client, teacher_assignment):
        """Admin can purge an archived assignment with no progressed submissions."""
        teacher_assignment.status = AssignmentStatus.ARCHIVED
        teacher_assignment.save()
        resp = admin_client.delete(
            f"/api/v1/assignments/{teacher_assignment.id}?purge=true"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

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

    def test_ARCH_UC_07_archive_emits_audit(self, admin_client, assessment):
        """Archive creates an audit log entry."""
        admin_client.post(f"/api/v1/assessments/{assessment.id}/archive")
        assert AuditLog.objects.filter(
            action=AuditAction.ARCHIVE,
            target_resource_type="Assessment",
            target_resource_id=assessment.id,
        ).exists()

    def test_ARCH_UC_07_restore_emits_audit(self, admin_client, admin_user, assessment):
        """Restore creates an audit log entry."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.archived_at = timezone.now()
        assessment.archived_by = admin_user
        assessment.save()
        admin_client.post(f"/api/v1/assessments/{assessment.id}/restore")
        assert AuditLog.objects.filter(
            action=AuditAction.RESTORE,
            target_resource_type="Assessment",
            target_resource_id=assessment.id,
        ).exists()

    def test_ARCH_UC_07_purge_emits_audit(self, admin_client, assessment):
        """Purge creates an audit log entry."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        admin_client.delete(f"/api/v1/assessments/{assessment.id}?purge=true")
        assert AuditLog.objects.filter(
            action=AuditAction.PURGE,
            target_resource_type="Assessment",
        ).exists()


# ---------------------------------------------------------------------------
# ARCH-CN-03 — Archived Assessment Blocks Assignment Creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_03:
    """Archived assessment blocks new assignment creation."""

    def test_ARCH_CN_03_assignment_create_blocked(
        self, teacher_client, teacher_user, teacher_course, assessment
    ):
        """409 when creating assignment from archived assessment."""
        assessment.status = AssessmentStatus.ARCHIVED
        assessment.save()
        resp = teacher_client.post(
            "/api/v1/assignments/",
            {
                "assessmentId": assessment.id,
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
        self, teacher_client, teacher_course, assessment
    ):
        """409 when creating assignment for archived course."""
        teacher_course.status = CourseStatus.ARCHIVED
        teacher_course.save()
        resp = teacher_client.post(
            "/api/v1/assignments/",
            {
                "assessmentId": assessment.id,
                "audienceType": "COURSE",
                "courseId": teacher_course.id,
                "openAt": timezone.now().isoformat(),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# ARCH-CN-07 — Purge Eligibility Gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestARCH_CN_07:
    """Purge blocked by dependency rules."""

    def test_ARCH_CN_07_purge_assessment_with_assignments(
        self, admin_client, teacher_assignment
    ):
        """Cannot purge assessment that has assignments."""
        asmt = teacher_assignment.assessment
        asmt.status = AssessmentStatus.ARCHIVED
        asmt.save()
        resp = admin_client.delete(f"/api/v1/assessments/{asmt.id}?purge=true")
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
        self, teacher_client, teacher_user, teacher_course, assessment
    ):
        """Archiving a course cascade-archives its ACTIVE assignments."""
        a1 = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assessment=assessment
        )
        a2 = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assessment=assessment
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
        self, teacher_client, teacher_user, teacher_course, assessment
    ):
        """Restoring a course does NOT cascade-restore its assignments."""
        asgn = AssignmentFactory(
            created_by=teacher_user, course=teacher_course, assessment=assessment
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
