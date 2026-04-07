"""Integration tests for assignments routes — FR-07 traceability."""

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import Role, StudentProfile, TeacherProfile, UserRole
from assessments.models import Assessment, AssessmentStatus, GradingMode, Question, QuestionKind
from assignments.models import Assignment, AssignmentStatus
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, Submission, SubmissionStatus
from tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assessment(admin_user, **kwargs):
    return Assessment.objects.create(
        title=kwargs.get("title", "Test Assessment"),
        grading_mode=kwargs.get("grading_mode", GradingMode.AUTO),
        created_by_admin=admin_user,
        status=kwargs.get("status", AssessmentStatus.ACTIVE),
    )


def _make_course(teacher_user):
    return Course.objects.create(name="Test Course", teacher_profile=teacher_user.teacher_profile)


def _make_assignment(assessment, course, teacher_user, **kwargs):
    return Assignment.objects.create(
        title=kwargs.get("title", None),
        assessment=assessment,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=kwargs.get("open_at", timezone.now()),
        due_at=kwargs.get("due_at", None),
        status=kwargs.get("status", AssignmentStatus.ACTIVE),
    )


def _enroll(course, student_user):
    Enrollment.objects.create(
        course=course,
        student_profile=student_user.student_profile,
        status=EnrollmentStatus.ACTIVE,
    )


def _second_teacher():
    user = UserFactory()
    UserRole.objects.create(user=user, role=Role.TEACHER)
    TeacherProfile.objects.create(user=user)
    return user


# ===========================================================================
# ASGN-UC-01 — Create Assignment
# ===========================================================================

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestCreateAssignment:
    """ASGN-UC-01 tests."""

    def test_ASGN_UC_01_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher creates assignment; submissions are provisioned atomically."""
        assessment = _make_assessment(admin_user)
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.NUMBER_SCALE,
            kind=QuestionKind.NUMBER_SCALE,
            prompt="Rate 1-5",
            max_points=5.0,
            auto_gradable=True,
            graded=False,
        )
        course = _make_course(teacher_user)
        _enroll(course, student_user)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "ACTIVE"
        assert data["courseId"] == course.id
        assert data["title"] == "Week 1 Intro Check-in"

        assignment = Assignment.objects.get(id=data["id"])
        assert assignment.title == "Week 1 Intro Check-in"
        subs = Submission.objects.filter(assignment=assignment, student=student_user)
        assert subs.count() == 1
        assert Answer.objects.filter(submission=subs.first()).count() == 1

    def test_ASGN_UC_01_E2_not_teacher(self, api_client, student_user, admin_user):
        """Non-teacher cannot create assignments (403)."""
        assessment = _make_assessment(admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": 999,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 403

    def test_ASGN_UC_01_E3_not_course_owner(self, api_client, teacher_user, admin_user):
        """Teacher who doesn't own the course gets 403 (ASGN-CN-10)."""
        assessment = _make_assessment(admin_user)
        other_teacher = _second_teacher()
        course = _make_course(other_teacher)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 403

    def test_ASGN_UC_01_E5_archived_assessment(self, api_client, teacher_user, admin_user):
        """Creating assignment from archived assessment returns 409 (ASGN-CN-04)."""
        assessment = _make_assessment(admin_user, status=AssessmentStatus.ARCHIVED)
        course = _make_course(teacher_user)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 409

    def test_ASGN_UC_01_E6_invalid_scheduling(self, api_client, teacher_user, admin_user):
        """openAt >= dueAt returns 400 (ASGN-CN-07)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": now.isoformat(),
            "dueAt": (now - timedelta(hours=1)).isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 400

    def test_ASGN_CN_05_submissions_created_atomically(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Submissions are created atomically for all enrolled students."""
        assessment = _make_assessment(admin_user)
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.MULTIPLE_CHOICE,
            kind=QuestionKind.MULTIPLE_CHOICE,
            prompt="Pick one",
            max_points=5.0,
            auto_gradable=True,
            graded=False,
        )
        course = _make_course(teacher_user)
        _enroll(course, student_user)

        # Enroll a second student
        student2 = UserFactory()
        UserRole.objects.create(user=student2, role=Role.STUDENT)
        StudentProfile.objects.create(user=student2, created_by=admin_user)
        Enrollment.objects.create(
            course=course,
            student_profile=student2.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 201
        asgn = Assignment.objects.get(id=resp.json()["id"])
        assert Submission.objects.filter(assignment=asgn).count() == 2

    def test_ASGN_CN_05_dropped_students_do_not_receive_submissions(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Only ACTIVE enrollments receive placeholder submissions."""
        assessment = _make_assessment(admin_user)
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Describe your approach",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = _make_course(teacher_user)
        _enroll(course, student_user)

        dropped_student = UserFactory()
        UserRole.objects.create(user=dropped_student, role=Role.STUDENT)
        StudentProfile.objects.create(user=dropped_student, created_by=admin_user)
        Enrollment.objects.create(
            course=course,
            student_profile=dropped_student.student_profile,
            status=EnrollmentStatus.DROPPED,
        )

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 201

        assignment = Assignment.objects.get(id=resp.json()["id"])
        assert Submission.objects.filter(assignment=assignment, student=student_user).count() == 1
        assert (
            Submission.objects.filter(assignment=assignment, student=dropped_student).count() == 0
        )

    def test_ASGN_CN_11_teacher_audience_type_rejected(
        self, api_client, teacher_user, admin_user
    ):
        """TEACHER audience type is rejected with 400."""
        assessment = _make_assessment(admin_user)
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "TEACHER",
            "targetTeacherId": teacher_user.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 400


# ===========================================================================
# ASGN-UC-02 — List Assignments by Course
# ===========================================================================


@pytest.mark.django_db
class TestListByCourse:
    """ASGN-UC-02 tests."""

    def test_ASGN_UC_02_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can list assignments for their own course."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_ADMIN(self, api_client, teacher_user, admin_user):
        """Admin can list assignments for any course."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_RESEARCHER(self, api_client, teacher_user, admin_user, researcher_user):
        """Researcher can list assignments for any course."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_E3_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """Teacher cannot list assignments for a course they don't own (403)."""
        other_teacher = _second_teacher()
        assessment = _make_assessment(admin_user)
        course = _make_course(other_teacher)
        _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 403


# ===========================================================================
# ASGN-UC-03 — List Assignments for User
# ===========================================================================


@pytest.mark.django_db
class TestListForUser:
    """ASGN-UC-03 tests."""

    def test_ASGN_UC_03_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student sees active assignments from enrolled courses."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_03_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher sees assignments they created."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/users/{teacher_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_03_RESEARCHER_CROSS_USER(
        self, api_client, teacher_user, student_user, researcher_user, admin_user
    ):
        """Researcher can list assignments for other users."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_03_E2_forbidden_cross_user(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot list another user's assignments (403)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{teacher_user.id}")
        assert resp.status_code == 403

    def test_ASGN_CN_08_student_time_filter(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student doesn't see future assignments or past-due assignments (ASGN-CN-08)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        now = timezone.now()

        # Future assignment (not yet open)
        Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=now + timedelta(days=7),
            due_at=None,
        )
        # Past due assignment
        Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=now - timedelta(days=14),
            due_at=now - timedelta(days=1),
        )
        # Currently open assignment
        _make_assignment(assessment, course, teacher_user, open_at=now - timedelta(hours=1))

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_CN_09_archived_hides_from_student_list(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Archived assignments are hidden from student lists (ASGN-CN-09)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assessment, course, teacher_user, status=AssignmentStatus.ARCHIVED)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 0


# ===========================================================================
# ASGN-UC-04 — Get Assignment Detail
# ===========================================================================


@pytest.mark.django_db
class TestGetDetail:
    """ASGN-UC-04 tests."""

    def test_ASGN_UC_04_ADMIN(self, api_client, teacher_user, admin_user):
        """Admin can view any assignment."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == assignment.id
        assert resp.json()["status"] == "ACTIVE"
        assert resp.json()["assessmentTitle"] == assessment.title

    def test_ASGN_UC_04_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can view assignment for their own course."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == assignment.id

    def test_ASGN_UC_04_STUDENT_ENROLLED(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Enrolled student can view assignment detail."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200

    def test_ASGN_UC_04_E2_student_not_enrolled(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Unenrolled student gets 403."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_E2_student_dropped(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Dropped students cannot view assignment detail."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.DROPPED,
        )
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_E3_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """Teacher cannot view assignment for a course they don't own (403)."""
        other_teacher = _second_teacher()
        assessment = _make_assessment(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_TEMPLATE_STUDENT_ENROLLED(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Enrolled student can fetch assignment template questions."""
        assessment = _make_assessment(admin_user)
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Explain your process",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 200
        assert resp.json()["id"] == assessment.id
        assert len(resp.json()["questions"]) == 1
        assert resp.json()["questions"][0]["prompt"] == "Explain your process"

    def test_ASGN_UC_04_TEMPLATE_E2_student_not_enrolled(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Unenrolled student cannot fetch assignment template (403)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 403

    def test_ASGN_UC_04_TEMPLATE_E2_student_dropped(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Dropped students cannot fetch assignment template."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.DROPPED,
        )
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 403


# ===========================================================================
# ASGN-UC-05 — Update Assignment Scheduling
# ===========================================================================


@pytest.mark.django_db
class TestUpdateAssignment:
    """ASGN-UC-05 tests."""

    def test_ASGN_UC_05_TEACHER_CREATOR(self, api_client, teacher_user, admin_user):
        """Creator can update scheduling."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()
        assignment = _make_assignment(
            assessment, course, teacher_user, open_at=now, due_at=now + timedelta(days=7)
        )

        new_due = now + timedelta(days=14)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"title": "Updated Week 2 Quiz", "dueAt": new_due.isoformat()},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"
        assert resp.json()["title"] == "Updated Week 2 Quiz"
        assignment.refresh_from_db()
        assert assignment.title == "Updated Week 2 Quiz"
        assert assignment.due_at is not None

    def test_ASGN_UC_05_E2_not_creator(self, api_client, teacher_user, admin_user):
        """Non-creator teacher gets 403."""
        assessment = _make_assessment(admin_user)
        other_teacher = _second_teacher()
        course = _make_course(other_teacher)
        assignment = _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"dueAt": (timezone.now() + timedelta(days=14)).isoformat()},
            format="json",
        )
        assert resp.status_code == 403

    def test_ASGN_UC_05_E3_archived(self, api_client, teacher_user, admin_user):
        """Archived assignment cannot be updated (409)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assessment, course, teacher_user, status=AssignmentStatus.ARCHIVED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"dueAt": (timezone.now() + timedelta(days=14)).isoformat()},
            format="json",
        )
        assert resp.status_code == 409

    def test_ASGN_UC_05_E4_invalid_scheduling(self, api_client, teacher_user, admin_user):
        """openAt >= dueAt on update returns 400."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()
        assignment = _make_assignment(
            assessment, course, teacher_user, open_at=now, due_at=now + timedelta(days=7)
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"dueAt": (now - timedelta(hours=1)).isoformat()},
            format="json",
        )
        assert resp.status_code == 400


# ===========================================================================
# ASGN-UC-06 — Delete Assignment
# ===========================================================================


@pytest.mark.django_db
class TestDeleteAssignment:
    """ASGN-UC-06 tests."""

    def test_ASGN_UC_06_TEACHER_CREATOR(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Creator can DELETE assignment with NOT_STARTED submissions."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)
        Submission.objects.create(
            assignment=assignment, student=student_user, status=SubmissionStatus.NOT_STARTED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 204
        assert not Assignment.objects.filter(id=assignment.id).exists()

    def test_ASGN_UC_06_E2_not_creator(self, api_client, teacher_user, admin_user):
        """Non-creator teacher cannot delete (403)."""
        other_teacher = _second_teacher()
        assessment = _make_assessment(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_06_E3_submissions_progressed(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Creator can DELETE assignment even with progressed submissions."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)
        Submission.objects.create(
            assignment=assignment, student=student_user, status=SubmissionStatus.IN_PROGRESS
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 204
        assert not Assignment.objects.filter(id=assignment.id).exists()

    def test_ASGN_CN_06_creator_can_delete(self, api_client, teacher_user, admin_user):
        """Creator can DELETE an assignment."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 204
        assert not Assignment.objects.filter(id=assignment.id).exists()


# ===========================================================================
# ASGN-UC-07 — Archive Assignment
# ===========================================================================


@pytest.mark.django_db
class TestArchiveAssignment:
    """ASGN-UC-07 tests."""

    def test_ASGN_UC_07_TEACHER_CREATOR(self, api_client, teacher_user, admin_user):
        """Creator can archive an active assignment."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.ARCHIVED

    def test_ASGN_UC_07_E2_not_creator(self, api_client, teacher_user, admin_user):
        """Non-creator teacher cannot archive (403)."""
        other_teacher = _second_teacher()
        assessment = _make_assessment(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 403

    def test_ASGN_UC_07_E3_already_archived(self, api_client, teacher_user, admin_user):
        """Already-archived assignment returns 409."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assessment, course, teacher_user, status=AssignmentStatus.ARCHIVED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 409

    def test_ASGN_CN_09_archived_blocks_new_submissions(
        self, api_client, teacher_user, admin_user
    ):
        """Archived assignments remain visible to teacher but status is ARCHIVED."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assessment, course, teacher_user, status=AssignmentStatus.ARCHIVED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"


# ===========================================================================
# Additional constraint tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignmentConstraints:
    """Cross-cutting constraint tests."""

    def test_ASGN_CN_01_creator_ownership_on_all_mutations(
        self, api_client, teacher_user, admin_user
    ):
        """Only the creator can update/delete/archive — tested as a bundle."""
        other_teacher = _second_teacher()
        assessment = _make_assessment(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assessment, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)

        # PATCH → 403
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"dueAt": (timezone.now() + timedelta(days=14)).isoformat()},
            format="json",
        )
        assert resp.status_code == 403

        # DELETE → 403 (not creator)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

        # Archive → 403
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 403

    def test_assignment_not_found_returns_404(self, api_client, teacher_user):
        """GET/PATCH/DELETE on non-existent assignment returns 404."""
        api_client.force_authenticate(user=teacher_user)
        for method in ["get", "delete"]:
            resp = getattr(api_client, method)("/api/v1/assignments/99999")
            assert resp.status_code == 404

        resp = api_client.patch(
            "/api/v1/assignments/99999",
            {"dueAt": timezone.now().isoformat()},
            format="json",
        )
        assert resp.status_code == 404

    def test_paginated_list_endpoints(self, api_client, teacher_user, admin_user):
        """List endpoints return paginated responses (ASGN item 13)."""
        assessment = _make_assessment(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assessment, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)

        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        data = resp.json()
        assert "results" in data
        assert "count" in data

        resp = api_client.get(f"/api/v1/assignments/users/{teacher_user.id}")
        data = resp.json()
        assert "results" in data
        assert "count" in data
