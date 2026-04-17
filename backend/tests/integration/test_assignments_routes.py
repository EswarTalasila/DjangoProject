"""Integration tests for assignments routes — FR-07 traceability."""

from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import Role, StudentProfile, TeacherProfile, UserRole
from assignment_templates.image_services import upload_question_image
from assignment_templates.models import AssignmentTemplate, AssignmentTemplateStatus, GradingMode, Question, QuestionKind
from assignments.models import Assignment, AssignmentStatus
from core.media.models import ImageAsset
from assignments.services._content import snapshot_assignment_content
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, Submission, SubmissionStatus
from tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assignment_template(admin_user, **kwargs):
    return AssignmentTemplate.objects.create(
        title=kwargs.get("title", "Test AssignmentTemplate"),
        grading_mode=kwargs.get("grading_mode", GradingMode.AUTO),
        created_by_admin=admin_user,
        status=kwargs.get("status", AssignmentTemplateStatus.ACTIVE),
    )


def _make_course(teacher_user):
    return Course.objects.create(name="Test Course", teacher_profile=teacher_user.teacher_profile)


def _make_assignment(assignment_template, course, teacher_user, **kwargs):
    assignment = Assignment.objects.create(
        title=kwargs.get("title", None),
        assignment_template=assignment_template,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=kwargs.get("open_at", timezone.now()),
        due_at=kwargs.get("due_at", None),
        status=kwargs.get("status", AssignmentStatus.ACTIVE),
    )
    snapshot_assignment_content(assignment, assignment_template, creator_user_id=teacher_user.id)
    return assignment


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


def _make_png_upload(name: str = "question.png") -> SimpleUploadedFile:
    data = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb1"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(name, data, content_type="image/png")


# ===========================================================================
# ASGN-UC-01 — Create Assignment
# ===========================================================================

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestCreateAssignment:
    """ASGN-UC-01 tests."""

    def test_ASGN_UC_01_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher creates assignment; submissions are provisioned atomically."""
        assignment_template = _make_assignment_template(admin_user)
        Question.objects.create(
            assignment_template=assignment_template,
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
            "assignmentTemplateId": assignment_template.id,
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

    def test_ASGN_UC_01_E1_missing_title(self, api_client, teacher_user, admin_user):
        """Missing assignment title returns 400 and does not fall back to template title."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assignmentTemplateId": assignment_template.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 400
        assert "title" in resp.json()

    def test_ASGN_UC_01_E2_not_teacher(self, api_client, student_user, admin_user):
        """Non-teacher cannot create assignments (403)."""
        assignment_template = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
            "audienceType": "COURSE",
            "courseId": 999,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 403

    def test_ASGN_UC_01_E3_not_course_owner(self, api_client, teacher_user, admin_user):
        """Teacher who doesn't own the course gets 403 (ASGN-CN-10)."""
        assignment_template = _make_assignment_template(admin_user)
        other_teacher = _second_teacher()
        course = _make_course(other_teacher)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 403

    def test_ASGN_UC_01_E5_archived_assignment_template(self, api_client, teacher_user, admin_user):
        """Creating assignment from archived assignment_template returns 409 (ASGN-CN-04)."""
        assignment_template = _make_assignment_template(admin_user, status=AssignmentTemplateStatus.ARCHIVED)
        course = _make_course(teacher_user)

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        resp = api_client.post("/api/v1/assignments/", payload, format="json")
        assert resp.status_code == 409

    def test_ASGN_UC_01_E6_invalid_scheduling(self, api_client, teacher_user, admin_user):
        """openAt >= dueAt returns 400 (ASGN-CN-07)."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
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
        assignment_template = _make_assignment_template(admin_user)
        Question.objects.create(
            assignment_template=assignment_template,
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
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
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
        assignment_template = _make_assignment_template(admin_user)
        Question.objects.create(
            assignment_template=assignment_template,
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
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
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
        assignment_template = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_ADMIN(self, api_client, teacher_user, admin_user):
        """Admin can list assignments for any course."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_RESEARCHER(self, api_client, teacher_user, admin_user, researcher_user):
        """Researcher can list assignments for any course."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_02_E3_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """Teacher cannot list assignments for a course they don't own (403)."""
        other_teacher = _second_teacher()
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(other_teacher)
        _make_assignment(assignment_template, course, other_teacher)

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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_03_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher sees assignments they created."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/users/{teacher_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_UC_03_RESEARCHER_CROSS_USER(
        self, api_client, teacher_user, student_user, researcher_user, admin_user
    ):
        """Researcher can list assignments for other users."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assignment_template, course, teacher_user)

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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        now = timezone.now()

        # Future assignment (not yet open)
        Assignment.objects.create(
            assignment_template=assignment_template,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=now + timedelta(days=7),
            due_at=None,
        )
        # Past due assignment
        Assignment.objects.create(
            assignment_template=assignment_template,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=now - timedelta(days=14),
            due_at=now - timedelta(days=1),
        )
        # Currently open assignment
        _make_assignment(assignment_template, course, teacher_user, open_at=now - timedelta(hours=1))

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_ASGN_CN_09_archived_hides_from_student_list(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Archived assignments are hidden from student lists (ASGN-CN-09)."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        _make_assignment(assignment_template, course, teacher_user, status=AssignmentStatus.ARCHIVED)

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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == assignment.id
        assert resp.json()["status"] == "ACTIVE"
        assert resp.json()["assignmentTemplateTitle"] == assignment_template.title

    def test_ASGN_UC_04_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can view assignment for their own course."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == assignment.id

    def test_ASGN_UC_04_STUDENT_ENROLLED(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Enrolled student can view assignment detail."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 200

    def test_ASGN_UC_04_E2_student_not_enrolled(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Unenrolled student gets 403."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_E2_student_dropped(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Dropped students cannot view assignment detail."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.DROPPED,
        )
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_E3_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """Teacher cannot view assignment for a course they don't own (403)."""
        other_teacher = _second_teacher()
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assignment_template, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_04_TEMPLATE_STUDENT_ENROLLED(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Enrolled student can fetch assignment template questions."""
        assignment_template = _make_assignment_template(admin_user)
        Question.objects.create(
            assignment_template=assignment_template,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Explain your process",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 200
        assert resp.json()["id"] == assignment_template.id
        assert len(resp.json()["questions"]) == 1
        assert resp.json()["questions"][0]["prompt"] == "Explain your process"

    def test_ASGN_UC_04_TEMPLATE_E2_student_not_enrolled(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Unenrolled student cannot fetch assignment template (403)."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 403

    def test_ASGN_UC_04_TEMPLATE_E2_student_dropped(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Dropped students cannot fetch assignment template."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.DROPPED,
        )
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignments/{assignment.id}/template")
        assert resp.status_code == 403


# ===========================================================================
# ASGN-UC-04A — Extend Assignment Content
# ===========================================================================


@pytest.mark.django_db
class TestExtendAssignmentContent:
    """Assignment-local teacher extension routes."""

    def test_teacher_can_add_assignment_local_question_and_provision_answers(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher adds a local question and existing submissions receive answer shells."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.NOT_STARTED,
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {
                "type": "SHORT_ANSWER",
                "prompt": "Teacher follow-up",
                "maxPoints": 4,
            },
            format="json",
        )

        assert resp.status_code == 201
        payload = resp.json()
        teacher_questions = [q for q in payload["questions"] if q["origin"] == "TEACHER_ADDITION"]
        assert len(teacher_questions) == 1
        assert teacher_questions[0]["prompt"] == "Teacher follow-up"
        assert Answer.objects.filter(submission=submission).count() == 1

    def test_teacher_can_update_and_delete_assignment_local_question(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher can edit and delete only teacher-authored assignment-local questions."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _enroll(course, student_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.NOT_STARTED,
        )
        api_client.force_authenticate(user=teacher_user)
        create_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {
                "type": "SHORT_ANSWER",
                "prompt": "Teacher follow-up",
                "maxPoints": 4,
            },
            format="json",
        )
        question_id = next(
            question["id"]
            for question in create_resp.json()["questions"]
            if question["origin"] == "TEACHER_ADDITION"
        )
        update_resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}",
            {
                "type": "NUMBER_SCALE",
                "prompt": "Teacher follow-up revised",
                "maxPoints": 6,
            },
            format="json",
        )
        assert update_resp.status_code == 200
        updated_question = next(
            question
            for question in update_resp.json()["questions"]
            if question["id"] == question_id
        )
        assert updated_question["prompt"] == "Teacher follow-up revised"
        assert updated_question["type"] == "NUMBER_SCALE"
        assert updated_question["maxPoints"] == 6

        delete_resp = api_client.delete(f"/api/v1/assignments/{assignment.id}/questions/{question_id}")
        assert delete_resp.status_code == 200
        assert all(
            question["id"] != question_id
            for question in delete_resp.json()["questions"]
        )
        assert Answer.objects.filter(submission=submission).count() == 0

    def test_teacher_question_delete_cleans_up_orphaned_image_asset(
        self, api_client, teacher_user, admin_user, settings, tmp_path
    ):
        """Deleting a teacher-authored question removes its orphaned image blob and asset."""
        settings.MEDIA_ROOT = str(tmp_path)
        settings.IMAGE_ROOT = tmp_path / "images"

        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        create_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {
                "type": "SHORT_ANSWER",
                "prompt": "Teacher image prompt",
                "maxPoints": 4,
            },
            format="json",
        )
        question_id = next(
            question["id"]
            for question in create_resp.json()["questions"]
            if question["origin"] == "TEACHER_ADDITION"
        )

        upload_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}/image",
            {"file": _make_png_upload()},
        )
        assert upload_resp.status_code == 201
        asset_id = upload_resp.json()["id"]
        asset = ImageAsset.objects.get(id=asset_id)
        blob_path = Path(settings.IMAGE_ROOT) / asset.storage_key
        assert blob_path.exists()

        delete_resp = api_client.delete(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}"
        )
        assert delete_resp.status_code == 200

        asset.refresh_from_db()
        assert asset.status == "DELETED"
        assert asset.deleted_at is not None
        assert not blob_path.exists()

    def test_teacher_question_delete_keeps_reused_template_image_asset(
        self, api_client, teacher_user, admin_user, settings, tmp_path
    ):
        """Deleting a teacher-authored question preserves assets still referenced by a template."""
        settings.MEDIA_ROOT = str(tmp_path)
        settings.IMAGE_ROOT = tmp_path / "images"

        assignment_template = _make_assignment_template(admin_user)
        template_question = Question.objects.create(
            assignment_template=assignment_template,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Researcher prompt",
            max_points=4.0,
            auto_gradable=False,
            graded=False,
        )
        template_image = upload_question_image(
            template_question,
            _make_png_upload("template.png"),
            uploader_id=admin_user.id,
        )
        asset = ImageAsset.objects.get(id=template_image["id"])
        blob_path = Path(settings.IMAGE_ROOT) / asset.storage_key
        assert blob_path.exists()

        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        create_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {
                "type": "SHORT_ANSWER",
                "prompt": "Teacher reuse prompt",
                "maxPoints": 4,
            },
            format="json",
        )
        question_id = next(
            question["id"]
            for question in create_resp.json()["questions"]
            if question["origin"] == "TEACHER_ADDITION"
        )

        reuse_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}/image/reuse",
            {"assetId": str(asset.id)},
            format="json",
        )
        assert reuse_resp.status_code == 200

        delete_resp = api_client.delete(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}"
        )
        assert delete_resp.status_code == 200

        asset.refresh_from_db()
        template_question.refresh_from_db()
        assert asset.status == "ACTIVE"
        assert asset.deleted_at is None
        assert blob_path.exists()
        assert template_question.image is not None

    def test_inherited_assignment_question_cannot_be_updated_or_deleted(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher cannot mutate locked researcher-provided assignment questions."""
        assignment_template = _make_assignment_template(admin_user)
        inherited = Question.objects.create(
            assignment_template=assignment_template,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Researcher prompt",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)
        inherited_assignment_question = assignment.questions.get(
            source_template_question=inherited
        )

        api_client.force_authenticate(user=teacher_user)
        update_resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}/questions/{inherited_assignment_question.id}",
            {"prompt": "Teacher override"},
            format="json",
        )
        delete_resp = api_client.delete(
            f"/api/v1/assignments/{assignment.id}/questions/{inherited_assignment_question.id}"
        )

        assert update_resp.status_code == 404
        assert delete_resp.status_code == 404
        assert "Teacher question not found." in update_resp.json()["detail"]
        assert "Teacher question not found." in delete_resp.json()["detail"]

    def test_admin_can_update_and_delete_teacher_added_question(
        self, api_client, teacher_user, admin_user
    ):
        """Admin override can manage teacher-authored assignment-local questions."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        create_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {"type": "SHORT_ANSWER", "prompt": "Teacher follow-up", "maxPoints": 4},
            format="json",
        )
        question_id = next(
            question["id"]
            for question in create_resp.json()["questions"]
            if question["origin"] == "TEACHER_ADDITION"
        )

        api_client.force_authenticate(user=admin_user)
        update_resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}/questions/{question_id}",
            {"prompt": "Admin revised follow-up", "maxPoints": 5},
            format="json",
        )
        delete_resp = api_client.delete(f"/api/v1/assignments/{assignment.id}/questions/{question_id}")

        assert update_resp.status_code == 200
        assert any(
            question["prompt"] == "Admin revised follow-up"
            for question in update_resp.json()["questions"]
        )
        assert delete_resp.status_code == 200
        assert all(
            question["id"] != question_id for question in delete_resp.json()["questions"]
        )

    def test_teacher_can_add_assignment_local_criterion(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher adds a local rubric criterion layered onto the assignment."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {
                "title": "Local rigor",
                "description": "Check local classroom expectations.",
                "weight": 2,
            },
            format="json",
        )

        assert resp.status_code == 201
        payload = resp.json()
        assert len(payload["teacherCriteria"]) == 1
        assert payload["teacherCriteria"][0]["title"] == "Local rigor"
        assert payload["teacherCriteria"][0]["levels"] == []

    def test_teacher_can_reorder_only_teacher_added_questions(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher-added questions can be reordered without moving inherited template questions."""
        assignment_template = _make_assignment_template(admin_user)
        Question.objects.create(
            assignment_template=assignment_template,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Researcher prompt",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        first = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {"type": "SHORT_ANSWER", "prompt": "Teacher A", "maxPoints": 1},
            format="json",
        )
        second = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {"type": "SHORT_ANSWER", "prompt": "Teacher B", "maxPoints": 1},
            format="json",
        )
        assert first.status_code == 201
        assert second.status_code == 201

        teacher_ids = [
            question["id"]
            for question in second.json()["questions"]
            if question["origin"] == "TEACHER_ADDITION"
        ]
        resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions/reorder",
            {"orderedIds": list(reversed(teacher_ids))},
            format="json",
        )

        assert resp.status_code == 200
        prompts = [question["prompt"] for question in resp.json()["questions"]]
        assert prompts == ["Researcher prompt", "Teacher B", "Teacher A"]

    def test_teacher_can_add_levels_and_reorder_teacher_criteria(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher criteria support local levels and can be reordered without affecting locked rubric content."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        first = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {"title": "Teacher Criterion A", "description": "", "weight": 1},
            format="json",
        )
        second = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {"title": "Teacher Criterion B", "description": "", "weight": 2},
            format="json",
        )
        assert first.status_code == 201
        assert second.status_code == 201

        criteria = second.json()["teacherCriteria"]
        first_id = criteria[0]["id"]
        second_id = criteria[1]["id"]

        level_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{first_id}/levels",
            {"label": "Exceeds", "description": "Local evidence is strong.", "points": 4},
            format="json",
        )
        assert level_resp.status_code == 201
        level_payload = next(
            criterion for criterion in level_resp.json()["teacherCriteria"] if criterion["id"] == first_id
        )
        assert level_payload["levels"][0]["label"] == "Exceeds"

        reorder_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/reorder",
            {"orderedIds": [second_id, first_id]},
            format="json",
        )
        assert reorder_resp.status_code == 200
        reordered_titles = [criterion["title"] for criterion in reorder_resp.json()["teacherCriteria"]]
        assert reordered_titles == ["Teacher Criterion B", "Teacher Criterion A"]

    def test_teacher_can_reorder_levels_for_teacher_criterion(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher-owned criterion levels can be reordered independently of locked rubric content."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        criterion_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {"title": "Local rigor", "description": "", "weight": 1},
            format="json",
        )
        criterion_id = criterion_resp.json()["teacherCriteria"][0]["id"]
        first_level = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels",
            {"label": "Meets", "description": "", "points": 2},
            format="json",
        )
        second_level = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels",
            {"label": "Exceeds", "description": "", "points": 4},
            format="json",
        )
        assert first_level.status_code == 201
        assert second_level.status_code == 201
        level_ids = [
            level["id"]
            for level in second_level.json()["teacherCriteria"][0]["levels"]
        ]

        reorder_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels/reorder",
            {"orderedIds": list(reversed(level_ids))},
            format="json",
        )
        assert reorder_resp.status_code == 200
        labels = reorder_resp.json()["teacherCriteria"][0]["levels"]
        assert [level["label"] for level in labels] == ["Exceeds", "Meets"]

    def test_teacher_can_update_and_delete_local_criterion_and_level(
        self, api_client, teacher_user, admin_user
    ):
        """Teacher can edit and delete local rubric criteria and levels."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        criterion_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {"title": "Local rigor", "description": "", "weight": 1},
            format="json",
        )
        criterion_id = criterion_resp.json()["teacherCriteria"][0]["id"]
        level_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels",
            {"label": "Meets", "description": "", "points": 2},
            format="json",
        )
        level_id = level_resp.json()["teacherCriteria"][0]["levels"][0]["id"]

        update_criterion_resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}",
            {"title": "Local rigor revised", "description": "Updated", "weight": 1.5},
            format="json",
        )
        assert update_criterion_resp.status_code == 200
        updated_criterion = update_criterion_resp.json()["teacherCriteria"][0]
        assert updated_criterion["title"] == "Local rigor revised"
        assert updated_criterion["description"] == "Updated"
        assert updated_criterion["weight"] == 1.5

        update_level_resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels/{level_id}",
            {"label": "Exceeds", "description": "Updated level", "points": 3},
            format="json",
        )
        assert update_level_resp.status_code == 200
        updated_level = update_level_resp.json()["teacherCriteria"][0]["levels"][0]
        assert updated_level["label"] == "Exceeds"
        assert updated_level["description"] == "Updated level"
        assert updated_level["points"] == 3

        delete_level_resp = api_client.delete(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}/levels/{level_id}"
        )
        assert delete_level_resp.status_code == 200
        assert delete_level_resp.json()["teacherCriteria"][0]["levels"] == []

        delete_criterion_resp = api_client.delete(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria/{criterion_id}"
        )
        assert delete_criterion_resp.status_code == 200
        assert delete_criterion_resp.json()["teacherCriteria"] == []

    def test_archived_assignment_rejects_extension_routes(
        self, api_client, teacher_user, admin_user
    ):
        """Archived assignments reject new questions and criteria with 409."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assignment_template,
            course,
            teacher_user,
            status=AssignmentStatus.ARCHIVED,
        )

        api_client.force_authenticate(user=teacher_user)
        q_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/questions",
            {"type": "SHORT_ANSWER", "prompt": "Blocked", "maxPoints": 1},
            format="json",
        )
        c_resp = api_client.post(
            f"/api/v1/assignments/{assignment.id}/teacher-criteria",
            {"title": "Blocked", "weight": 1},
            format="json",
        )

        assert q_resp.status_code == 409
        assert c_resp.status_code == 409
        assert "cannot be extended" in q_resp.json()["detail"].lower()


# ===========================================================================
# ASGN-UC-05 — Update Assignment Scheduling
# ===========================================================================


@pytest.mark.django_db
class TestUpdateAssignment:
    """ASGN-UC-05 tests."""

    def test_ASGN_UC_05_TEACHER_CREATOR(self, api_client, teacher_user, admin_user):
        """Creator can update scheduling."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()
        assignment = _make_assignment(
            assignment_template, course, teacher_user, open_at=now, due_at=now + timedelta(days=7)
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
        assignment_template = _make_assignment_template(admin_user)
        other_teacher = _second_teacher()
        course = _make_course(other_teacher)
        assignment = _make_assignment(assignment_template, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignments/{assignment.id}",
            {"dueAt": (timezone.now() + timedelta(days=14)).isoformat()},
            format="json",
        )
        assert resp.status_code == 403

    def test_ASGN_UC_05_E3_archived(self, api_client, teacher_user, admin_user):
        """Archived assignment cannot be updated (409)."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assignment_template, course, teacher_user, status=AssignmentStatus.ARCHIVED
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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        now = timezone.now()
        assignment = _make_assignment(
            assignment_template, course, teacher_user, open_at=now, due_at=now + timedelta(days=7)
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
        """Creator cannot plain-delete an assignment and is directed to archive-first flow."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)
        Submission.objects.create(
            assignment=assignment, student=student_user, status=SubmissionStatus.NOT_STARTED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 409
        assert "archive" in resp.json()["detail"].lower()
        assert Assignment.objects.filter(id=assignment.id).exists()
        assert Submission.objects.filter(assignment=assignment, student=student_user).exists()

    def test_ASGN_UC_06_E2_not_creator(self, api_client, teacher_user, admin_user):
        """Non-creator teacher cannot delete (403)."""
        other_teacher = _second_teacher()
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assignment_template, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 403

    def test_ASGN_UC_06_E3_submissions_progressed(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Plain DELETE remains blocked even when submissions have progressed."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)
        Submission.objects.create(
            assignment=assignment, student=student_user, status=SubmissionStatus.IN_PROGRESS
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 409
        assert Assignment.objects.filter(id=assignment.id).exists()
        assert Submission.objects.filter(assignment=assignment, student=student_user).exists()

    def test_ASGN_CN_06_creator_can_delete(self, api_client, teacher_user, admin_user):
        """Creator must archive first instead of plain-deleting an assignment."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 409
        assert Assignment.objects.filter(id=assignment.id).exists()

    def test_ASGN_CN_06_archived_assignment_still_requires_purge_flag(
        self, api_client, teacher_user, admin_user
    ):
        """Archived assignments still require ?purge=true for permanent removal."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assignment_template,
            course,
            teacher_user,
            status=AssignmentStatus.ARCHIVED,
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert resp.status_code == 409
        assert "purge=true" in resp.json()["detail"].lower()
        assert Assignment.objects.filter(id=assignment.id).exists()


# ===========================================================================
# ASGN-UC-07 — Archive Assignment
# ===========================================================================


@pytest.mark.django_db
class TestArchiveAssignment:
    """ASGN-UC-07 tests."""

    def test_ASGN_UC_07_TEACHER_CREATOR(self, api_client, teacher_user, admin_user):
        """Creator can archive an active assignment."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.ARCHIVED

    def test_ASGN_UC_07_E2_not_creator(self, api_client, teacher_user, admin_user):
        """Non-creator teacher cannot archive (403)."""
        other_teacher = _second_teacher()
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assignment_template, course, other_teacher)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 403

    def test_ASGN_UC_07_E3_already_archived(self, api_client, teacher_user, admin_user):
        """Already-archived assignment returns 409."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assignment_template, course, teacher_user, status=AssignmentStatus.ARCHIVED
        )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/assignments/{assignment.id}/archive")
        assert resp.status_code == 409

    def test_ASGN_CN_09_archived_blocks_new_submissions(
        self, api_client, teacher_user, admin_user
    ):
        """Archived assignments remain visible to teacher but status is ARCHIVED."""
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        assignment = _make_assignment(
            assignment_template, course, teacher_user, status=AssignmentStatus.ARCHIVED
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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(other_teacher)
        assignment = _make_assignment(assignment_template, course, other_teacher)

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
        assignment_template = _make_assignment_template(admin_user)
        course = _make_course(teacher_user)
        _make_assignment(assignment_template, course, teacher_user)

        api_client.force_authenticate(user=teacher_user)

        resp = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        data = resp.json()
        assert "results" in data
        assert "count" in data

        resp = api_client.get(f"/api/v1/assignments/users/{teacher_user.id}")
        data = resp.json()
        assert "results" in data
        assert "count" in data
