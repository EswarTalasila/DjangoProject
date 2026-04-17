"""FR-05 Courses integration tests — v5 traceability naming."""

import pytest

from accounts.models import Role, StudentProfile, TeacherProfile, User, UserRole
from courses.models import Course, Enrollment, EnrollmentStatus

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestCourseRoutes:
    # ── CRS-UC-01: Create Course ──

    def test_CRS_UC_01_TEACHER(self, api_client, teacher_user):
        """Teacher can create a course; returns 201 with course DTO."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post("/api/v1/courses/", {"name": "Biology"}, format="json")
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Biology"
        assert body["teacherId"] == teacher_user.teacher_profile.id
        assert Course.objects.filter(name="Biology").exists()

    def test_CRS_UC_01_E1(self, api_client, admin_user):
        """Non-teacher (admin) cannot create a course; returns 403."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post("/api/v1/courses/", {"name": "Physics"}, format="json")
        assert response.status_code == 403

    # ── CRS-UC-02: List Courses ──

    def test_CRS_UC_02_TEACHER(self, api_client, teacher_user):
        """Teacher sees only their own courses."""
        Course.objects.create(name="My Course", teacher_profile=teacher_user.teacher_profile)
        other_teacher = User.objects.create_user(
            username="other-teacher", email="other@example.com", name="Other", password="pass123"
        )
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        other_profile = TeacherProfile.objects.create(user=other_teacher)
        Course.objects.create(name="Other Course", teacher_profile=other_profile)

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "My Course"

    def test_CRS_UC_02_STUDENT(self, api_client, student_user, teacher_user):
        """Student sees only their actively enrolled courses."""
        course = Course.objects.create(name="Enrolled", teacher_profile=teacher_user.teacher_profile)
        other = Course.objects.create(name="Not Enrolled", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=student_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Enrolled"

    def test_CRS_UC_02_STUDENT_E1(self, api_client, student_user, teacher_user):
        """Student does not see courses with DROPPED enrollment."""
        course = Course.objects.create(name="Dropped", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.DROPPED
        )
        api_client.force_authenticate(user=student_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 0

    def test_CRS_UC_01_E2(self, api_client, student_user):
        """Student cannot create a course; returns 403."""
        api_client.force_authenticate(user=student_user)
        response = api_client.post("/api/v1/courses/", {"name": "Nope"}, format="json")
        assert response.status_code == 403

    def test_CRS_UC_02_RESEARCHER(self, api_client, researcher_user, teacher_user):
        """Researcher sees all courses."""
        Course.objects.create(name="Course A", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=researcher_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        assert len(response.json()["results"]) >= 1

    def test_CRS_UC_02_include_archived_marks_archived_rows(self, api_client, teacher_user):
        """includeArchived returns archived courses with ARCHIVED status in the DTO."""
        course = Course.objects.create(
            name="Archived Course",
            teacher_profile=teacher_user.teacher_profile,
            status="ARCHIVED",
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/courses/", {"includeArchived": "true"})
        assert response.status_code == 200
        results = response.json()["results"]
        archived = next(row for row in results if row["id"] == course.id)
        assert archived["status"] == "ARCHIVED"

    # ── CRS-UC-03: Get Course Detail ──

    def test_CRS_UC_03_TEACHER(self, api_client, teacher_user):
        """Teacher can view own course detail."""
        course = Course.objects.create(name="Detail", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/courses/{course.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Detail"
        assert "teacherName" in body
        assert "createdAt" in body

    def test_CRS_UC_03_E1(self, api_client, teacher_user):
        """Course not found returns 404."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/courses/999999")
        assert response.status_code == 404

    def test_CRS_UC_03_STUDENT(self, api_client, student_user, teacher_user):
        """Enrolled student can view course detail."""
        course = Course.objects.create(name="Visible", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f"/api/v1/courses/{course.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Visible"

    def test_CRS_UC_03_STUDENT_E1(self, api_client, student_user, teacher_user):
        """Student not enrolled in course is denied."""
        course = Course.objects.create(name="Hidden", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f"/api/v1/courses/{course.id}")
        assert response.status_code == 403

    # ── CRS-UC-04: Update Course ──

    def test_CRS_UC_04_TEACHER(self, api_client, teacher_user):
        """Owner teacher can rename course."""
        course = Course.objects.create(name="Old", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(f"/api/v1/courses/{course.id}", {"name": "New"}, format="json")
        assert response.status_code == 200
        course.refresh_from_db()
        assert course.name == "New"

    def test_CRS_UC_04_E1(self, api_client, teacher_user):
        """Non-owner teacher is denied."""
        other = User.objects.create_user(
            username="other-t", email="other-t@x.com", name="Other", password="pass"
        )
        UserRole.objects.create(user=other, role=Role.TEACHER)
        other_profile = TeacherProfile.objects.create(user=other)
        course = Course.objects.create(name="Theirs", teacher_profile=other_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(f"/api/v1/courses/{course.id}", {"name": "Mine"}, format="json")
        assert response.status_code == 403

    # ── CRS-UC-05: Delete Course (409 gate) ──

    def test_CRS_UC_05_TEACHER(self, api_client, teacher_user):
        """Course deletion returns 409 — archival not yet available."""
        course = Course.objects.create(name="Delete Me", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/courses/{course.id}")
        assert response.status_code == 409
        assert "archive" in response.json()["detail"].lower()
        assert Course.objects.filter(id=course.id).exists()

    # ── CRS-UC-06: List Students ──

    def test_CRS_UC_06_TEACHER(self, api_client, teacher_user, student_user):
        """Teacher lists active students in course."""
        course = Course.objects.create(name="Roster", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/courses/{course.id}/students")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["username"] == student_user.username

    # ── CRS-UC-07: Add Student (nested endpoint) ──

    def test_CRS_UC_07_TEACHER(self, api_client, teacher_user):
        """Teacher adds student via POST /courses/{id}/students."""
        course = Course.objects.create(name="Add Student", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            f"/api/v1/courses/{course.id}/students",
            {"name": "New Student", "consent": True},
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "New Student"
        assert body["role"] == "STUDENT"
        assert Enrollment.objects.filter(course=course, status=EnrollmentStatus.ACTIVE).exists()

    def test_CRS_UC_07_E1(self, api_client, teacher_user):
        """Student creation rejects client-supplied username."""
        course = Course.objects.create(name="No Username", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            f"/api/v1/courses/{course.id}/students",
            {"name": "Student", "username": "hacker"},
            format="json",
        )
        assert response.status_code == 400

    # ── CRS-UC-08: Remove Student (DROPPED) ──

    def test_CRS_UC_08_TEACHER(self, api_client, teacher_user, student_user):
        """Remove sets enrollment to DROPPED; user account preserved."""
        course = Course.objects.create(name="Drop", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/courses/{course.id}/students/{student_user.id}")
        assert response.status_code == 204
        enrollment = Enrollment.objects.get(course=course, student_profile=student_user.student_profile)
        assert enrollment.status == EnrollmentStatus.DROPPED
        assert User.objects.filter(id=student_user.id).exists()

    def test_CRS_UC_08_E2(self, api_client, teacher_user, student_user):
        """Removing an already-DROPPED student returns 404 (not found in active roster)."""
        course = Course.objects.create(name="Already Dropped", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.DROPPED
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/courses/{course.id}/students/{student_user.id}")
        assert response.status_code == 404

    # ── Constraint tests ──

    def test_CRS_CN_03(self, api_client, teacher_user):
        """Bulk student endpoint no longer exists; returns 404."""
        course = Course.objects.create(name="No Bulk", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/students/bulk/",
            [{"name": "A", "courseId": course.id}],
            format="json",
        )
        assert response.status_code == 404

    def test_CRS_CN_04(self, api_client, teacher_user, student_user):
        """Active-only roster: DROPPED students excluded from list."""
        course = Course.objects.create(name="Filter", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.DROPPED
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/courses/{course.id}/students")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 0

    def test_CRS_CN_05(self, api_client, teacher_user, student_user):
        """Removing student preserves User account (no hard-delete)."""
        course = Course.objects.create(name="Preserve", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=teacher_user)
        api_client.delete(f"/api/v1/courses/{course.id}/students/{student_user.id}")
        assert User.objects.filter(id=student_user.id).exists()

    def test_CRS_CN_06(self, api_client, teacher_user, student_user):
        """Student can be enrolled in multiple courses simultaneously."""
        c1 = Course.objects.create(name="C1", teacher_profile=teacher_user.teacher_profile)
        c2 = Course.objects.create(name="C2", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=c1, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        Enrollment.objects.create(
            course=c2, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        assert Enrollment.objects.filter(student_profile=student_user.student_profile).count() == 2

    def test_CRS_CN_09(self, api_client, teacher_user):
        """Distinct usernames generated for same-name students."""
        course = Course.objects.create(name="Names", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        r1 = api_client.post(
            f"/api/v1/courses/{course.id}/students",
            {"name": "Same Name"},
            format="json",
        )
        c2 = Course.objects.create(name="Names2", teacher_profile=teacher_user.teacher_profile)
        r2 = api_client.post(
            f"/api/v1/courses/{c2.id}/students",
            {"name": "Same Name"},
            format="json",
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["username"] != r2.json()["username"]

    def test_CRS_CN_11(self, api_client, teacher_user, student_user):
        """DROPPED enrollment record is preserved, not deleted."""
        course = Course.objects.create(name="Lifecycle", teacher_profile=teacher_user.teacher_profile)
        enrollment = Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status=EnrollmentStatus.ACTIVE
        )
        api_client.force_authenticate(user=teacher_user)
        api_client.delete(f"/api/v1/courses/{course.id}/students/{student_user.id}")
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.DROPPED

    def test_CRS_CN_12(self, api_client, teacher_user):
        """Course deletion blocked until archival capability exists (409)."""
        course = Course.objects.create(name="No Archive", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/courses/{course.id}")
        assert response.status_code == 409
