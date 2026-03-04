"""Integration tests for FR-09 Visualization endpoints."""

import pytest
from django.utils import timezone

from accounts.models import SudoGrant, SudoPermission
from assessments.models import GradingMode
from courses.models import EnrollmentStatus
from submissions.models import AnswerType, NumberScaleAnswer, SubmissionStatus
from tests.factories import (
    AnswerFactory,
    AssessmentFactory,
    AssignmentFactory,
    CourseFactory,
    EnrollmentFactory,
    QuestionFactory,
    StudentProfileFactory,
    SubmissionFactory,
)

DASHBOARD_URL = "/api/v1/visualizations/dashboard"
COURSE_URL = "/api/v1/visualizations/courses/{}/summary"
ASSIGNMENT_URL = "/api/v1/visualizations/assignments/{}/summary"
MOOD_URL = "/api/v1/visualizations/assignments/{}/mood-meter"


def _seed_course(teacher_user, *, n_students=3, n_graded=2, score=80.0, admin_user=None):
    """Create a course with enrollments, an assignment, and graded submissions."""
    course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
    assessment = AssessmentFactory(
        grading_mode=GradingMode.AUTO,
        created_by_admin=admin_user or teacher_user,
        category="math",
    )
    assignment = AssignmentFactory(
        assessment=assessment,
        course=course,
        created_by=teacher_user,
        open_at=timezone.now(),
    )

    students = []
    for _ in range(n_students):
        sp = StudentProfileFactory(created_by=admin_user or teacher_user)
        EnrollmentFactory(course=course, student_profile=sp)
        students.append(sp.user)

    for i, student in enumerate(students[:n_graded]):
        SubmissionFactory(
            assignment=assignment,
            student=student,
            status=SubmissionStatus.GRADED,
            score=score + i,
            submitted_at=timezone.now(),
        )

    # One SUBMITTED (pending) if we have more students than graded
    if n_students > n_graded:
        SubmissionFactory(
            assignment=assignment,
            student=students[n_graded],
            status=SubmissionStatus.SUBMITTED,
            submitted_at=timezone.now(),
        )

    return course, assignment, students


# ===========================================================================
# VIZ-UC-01 — Dashboard
# ===========================================================================


@pytest.mark.django_db
class TestVizDashboard:
    def test_VIZ_UC_01_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin sees all courses on dashboard."""
        _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "generatedAt" in data
        assert len(data["courses"]) == 1
        assert "courseId" in data["courses"][0]
        assert "courseName" in data["courses"][0]

    def test_VIZ_UC_01_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher sees only own courses."""
        _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        courses = resp.json()["courses"]
        assert len(courses) == 1
        c = courses[0]
        assert c["enrolledCount"] == 3
        assert c["assignmentCount"] == 1
        assert c["avgScore"] is not None
        assert c["pendingGrades"] == 1

    def test_VIZ_UC_01_RESEARCHER(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher with VIEW_IDENTIFIABLE_VIZ sees identifiable fields."""
        _seed_course(teacher_user, admin_user=admin_user)
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.VIEW_IDENTIFIABLE_VIZ.value],
        )
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        c = resp.json()["courses"][0]
        assert "courseId" in c
        assert "courseName" in c

    def test_VIZ_UC_01_RESEARCHER_anonymized(
        self, api_client, researcher_user, teacher_user, admin_user
    ):
        """Researcher without VIEW_IDENTIFIABLE_VIZ sees anonymized data (VIZ-CN-01)."""
        _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        c = resp.json()["courses"][0]
        assert "courseId" not in c
        assert "courseName" not in c
        # Numeric aggregates still present
        assert "enrolledCount" in c
        assert "avgScore" in c

    def test_VIZ_UC_01_E1_student_forbidden(self, api_client, student_user):
        """Student gets 403."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 403

    def test_VIZ_UC_01_E2_unauthenticated(self, api_client):
        """Unauthenticated gets 401."""
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 401

    def test_VIZ_CN_05_null_scores_dashboard(self, api_client, teacher_user, admin_user):
        """avgScore is null when no graded submissions exist (VIZ-CN-05)."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        c = resp.json()["courses"][0]
        assert c["avgScore"] is None
        assert c["avgCompletionRate"] is None


# ===========================================================================
# VIZ-UC-02 — Course Summary
# ===========================================================================


@pytest.mark.django_db
class TestVizCourseSummary:
    def test_VIZ_UC_02_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin can view any course summary."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "generatedAt" in data
        assert "filters" in data
        assert "courseId" in data
        assert len(data["assignments"]) == 1

    def test_VIZ_UC_02_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher sees own course summary."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 200
        a = resp.json()["assignments"][0]
        assert a["submittedCount"] == 3  # 2 graded + 1 submitted
        assert a["totalStudents"] == 3
        assert a["gradedCount"] == 2
        assert a["avgScore"] is not None
        assert a["pendingGrades"] == 1

    def test_VIZ_UC_02_RESEARCHER_anonymized(
        self, api_client, researcher_user, teacher_user, admin_user
    ):
        """Anonymized researcher sees no identifiable fields (VIZ-CN-01)."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "courseId" not in data
        assert "courseName" not in data
        a = data["assignments"][0]
        assert "assignmentId" not in a
        assert "assessmentTitle" not in a
        assert "assessmentCategory" in a  # Non-identifying retained

    def test_VIZ_UC_02_TEACHER_filter_by_category(self, api_client, teacher_user, admin_user):
        """Category filter works."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        # Create second assignment with different category
        assessment2 = AssessmentFactory(
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
            category="science",
        )
        AssignmentFactory(assessment=assessment2, course=course, created_by=teacher_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_URL.format(course.id), {"category": "math"})
        assert resp.status_code == 200
        assert len(resp.json()["assignments"]) == 1

    def test_VIZ_UC_02_TEACHER_filter_by_date_range(self, api_client, teacher_user, admin_user):
        """Date range filter works on assignment open_at."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        today = timezone.now().date().isoformat()
        resp = api_client.get(
            COURSE_URL.format(course.id), {"startDate": today, "endDate": today}
        )
        assert resp.status_code == 200
        assert len(resp.json()["assignments"]) == 1

    def test_VIZ_UC_02_E1_course_not_found(self, api_client, teacher_user):
        """404 for missing course."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_URL.format(99999))
        assert resp.status_code == 404

    def test_VIZ_UC_02_E2_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """403 for teacher accessing another teacher's course (VIZ-CN-03)."""
        from accounts.models import TeacherProfile, UserRole, Role
        from tests.factories import UserFactory

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        course, _, _ = _seed_course(other_teacher, admin_user=admin_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 403

    def test_VIZ_UC_02_E3_student_forbidden(self, api_client, student_user, teacher_user, admin_user):
        """Student gets 403."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 403

    def test_VIZ_UC_02_E4_unauthenticated(self, api_client, teacher_user, admin_user):
        """Unauthenticated gets 401."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        resp = api_client.get(COURSE_URL.format(course.id))
        assert resp.status_code == 401

    def test_VIZ_UC_02_E5_invalid_query_param(self, api_client, teacher_user, admin_user):
        """Invalid query param type returns 400."""
        course, _, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(COURSE_URL.format(course.id), {"assessmentId": "not-an-int"})
        assert resp.status_code == 400


# ===========================================================================
# VIZ-UC-03 — Assignment Grade Summary
# ===========================================================================


@pytest.mark.django_db
class TestVizAssignmentSummary:
    def test_VIZ_UC_03_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin can view any assignment summary."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "generatedAt" in data
        assert "filters" in data
        assert "assignmentId" in data
        assert "distribution" in data
        assert len(data["distribution"]) == 5

    def test_VIZ_UC_03_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher sees grade summary for own assignment."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user, score=75.0)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalStudents"] == 3
        assert data["submittedCount"] == 3
        assert data["gradedCount"] == 2
        assert data["avgScore"] is not None
        assert data["medianScore"] is not None
        assert data["highScore"] is not None
        assert data["lowScore"] is not None

    def test_VIZ_UC_03_RESEARCHER_anonymized(
        self, api_client, researcher_user, teacher_user, admin_user
    ):
        """Anonymized researcher — no assignmentId/assessmentTitle (VIZ-CN-01)."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "assignmentId" not in data
        assert "assessmentTitle" not in data
        assert "assessmentCategory" in data
        assert "distribution" in data

    def test_VIZ_UC_03_TEACHER_filter_by_date_range(self, api_client, teacher_user, admin_user):
        """Date range filter on submitted_at works."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        today = timezone.now().date().isoformat()
        resp = api_client.get(
            ASSIGNMENT_URL.format(assignment.id), {"startDate": today, "endDate": today}
        )
        assert resp.status_code == 200

    def test_VIZ_UC_03_E1_not_found(self, api_client, teacher_user):
        """404 for missing assignment."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(99999))
        assert resp.status_code == 404

    def test_VIZ_UC_03_E2_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """403 for teacher accessing other teacher's assignment (VIZ-CN-03)."""
        from accounts.models import TeacherProfile, UserRole, Role
        from tests.factories import UserFactory

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other)
        _, assignment, _ = _seed_course(other, admin_user=admin_user)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 403

    def test_VIZ_UC_03_E3_student_forbidden(self, api_client, student_user, teacher_user, admin_user):
        """Student gets 403."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 403

    def test_VIZ_UC_03_E4_unauthenticated(self, api_client, teacher_user, admin_user):
        """Unauthenticated gets 401."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert resp.status_code == 401

    def test_VIZ_UC_03_E5_invalid_query_param(self, api_client, teacher_user, admin_user):
        """Invalid query param type returns 400."""
        _, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id), {"startDate": "bad-date"})
        assert resp.status_code == 400

    def test_VIZ_CN_02_distribution_bins(self, api_client, teacher_user, admin_user):
        """Distribution bins are correct per VIZ-CN-02."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(created_by_admin=admin_user)
        assignment = AssignmentFactory(assessment=assessment, course=course, created_by=teacher_user)
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        scores = [45, 62, 73, 85, 95]
        for s in scores:
            sp2 = StudentProfileFactory(created_by=admin_user)
            EnrollmentFactory(course=course, student_profile=sp2)
            SubmissionFactory(
                assignment=assignment,
                student=sp2.user,
                status=SubmissionStatus.GRADED,
                score=float(s),
                submitted_at=timezone.now(),
            )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        dist = {d["range"]: d["count"] for d in resp.json()["distribution"]}
        assert dist["0-59"] == 1
        assert dist["60-69"] == 1
        assert dist["70-79"] == 1
        assert dist["80-89"] == 1
        assert dist["90-100"] == 1

    def test_VIZ_CN_02_null_scores(self, api_client, teacher_user, admin_user):
        """Null stats with zero graded submissions (VIZ-CN-05)."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(created_by_admin=admin_user)
        assignment = AssignmentFactory(assessment=assessment, course=course, created_by=teacher_user)
        sp = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        data = resp.json()
        assert data["avgScore"] is None
        assert data["medianScore"] is None
        assert data["highScore"] is None
        assert data["lowScore"] is None
        assert all(d["count"] == 0 for d in data["distribution"])

    def test_VIZ_CN_02_boundary_scores(self, api_client, teacher_user, admin_user):
        """Scores at boundaries and outside 0-100 range (VIZ-CN-02)."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(created_by_admin=admin_user)
        assignment = AssignmentFactory(assessment=assessment, course=course, created_by=teacher_user)

        # 59.5 rounds to 60 → 60-69 bin; 105 → 90-100; -5 → 0-59
        for s in [59.5, 105, -5]:
            sp = StudentProfileFactory(created_by=admin_user)
            EnrollmentFactory(course=course, student_profile=sp)
            SubmissionFactory(
                assignment=assignment,
                student=sp.user,
                status=SubmissionStatus.GRADED,
                score=s,
                submitted_at=timezone.now(),
            )

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        dist = {d["range"]: d["count"] for d in resp.json()["distribution"]}
        assert dist["0-59"] == 1   # -5 clamped
        assert dist["60-69"] == 1  # 59.5 rounds to 60
        assert dist["90-100"] == 1  # 105 clamped


# ===========================================================================
# VIZ-UC-04 — Mood Meter Summary
# ===========================================================================


@pytest.mark.django_db
class TestVizMoodMeter:
    def test_VIZ_UC_04_ADMIN(self, api_client, admin_user, teacher_user):
        """Admin can view mood meter summary."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "generatedAt" in data
        assert "quadrants" in data
        assert len(data["quadrants"]) == 4

    def test_VIZ_UC_04_TEACHER(self, api_client, teacher_user, admin_user):
        """Teacher can view mood meter for own course."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 200

    def test_VIZ_UC_04_RESEARCHER(self, api_client, researcher_user, teacher_user, admin_user):
        """Researcher can view mood meter."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 200
        # Anonymized: no assignmentId
        assert "assignmentId" not in resp.json()

    def test_VIZ_UC_04_E1_not_found(self, api_client, teacher_user):
        """404 for missing assignment."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(MOOD_URL.format(99999))
        assert resp.status_code == 404

    def test_VIZ_UC_04_E2_non_mood_meter_409(self, api_client, teacher_user, admin_user):
        """409 for non-mood-meter assignment (VIZ-CN-04)."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Incompatible assessment type."

    def test_VIZ_UC_04_E3_teacher_not_owner(self, api_client, teacher_user, admin_user):
        """403 for teacher accessing other teacher's mood meter (VIZ-CN-03)."""
        from accounts.models import TeacherProfile, UserRole, Role
        from tests.factories import UserFactory

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other)
        course = CourseFactory(teacher_profile=other.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=other
        )
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 403

    def test_VIZ_UC_04_E4_student_forbidden(self, api_client, student_user, teacher_user, admin_user):
        """Student gets 403."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 403

    def test_VIZ_UC_04_E5_unauthenticated(self, api_client, teacher_user, admin_user):
        """Unauthenticated gets 401."""
        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment, course=course, created_by=teacher_user
        )
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 401

    def test_VIZ_UC_04_quadrant_aggregation(self, api_client, teacher_user, admin_user):
        """Mood meter quadrants are derived from DB-backed row/col values."""
        from assessments.models import NumberScaleQuestion, QuestionKind

        course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
        assessment = AssessmentFactory(
            grading_mode=GradingMode.MOOD_METER,
            created_by_admin=admin_user,
        )
        assignment = AssignmentFactory(
            assessment=assessment,
            course=course,
            created_by=teacher_user,
        )

        row_q = QuestionFactory(
            assessment=assessment,
            question_type=QuestionKind.NUMBER_SCALE,
            kind=QuestionKind.NUMBER_SCALE,
        )
        col_q = QuestionFactory(
            assessment=assessment,
            question_type=QuestionKind.NUMBER_SCALE,
            kind=QuestionKind.NUMBER_SCALE,
        )
        NumberScaleQuestion.objects.create(question=row_q, min=1, max=5, target=3)
        NumberScaleQuestion.objects.create(question=col_q, min=1, max=5, target=3)

        # Submission 1: High Energy / Positive (4,4)
        sp1 = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp1, status=EnrollmentStatus.ACTIVE)
        sub1 = SubmissionFactory(
            assignment=assignment,
            student=sp1.user,
            status=SubmissionStatus.GRADED,
            submitted_at=timezone.now(),
        )
        a1r = AnswerFactory(submission=sub1, question=row_q, answer_type=AnswerType.NUMBER_SCALE)
        a1c = AnswerFactory(submission=sub1, question=col_q, answer_type=AnswerType.NUMBER_SCALE)
        NumberScaleAnswer.objects.create(answer=a1r, val=4)
        NumberScaleAnswer.objects.create(answer=a1c, val=4)

        # Submission 2: Low Energy / Negative (2,1)
        sp2 = StudentProfileFactory(created_by=admin_user)
        EnrollmentFactory(course=course, student_profile=sp2, status=EnrollmentStatus.ACTIVE)
        sub2 = SubmissionFactory(
            assignment=assignment,
            student=sp2.user,
            status=SubmissionStatus.GRADED,
            submitted_at=timezone.now(),
        )
        a2r = AnswerFactory(submission=sub2, question=row_q, answer_type=AnswerType.NUMBER_SCALE)
        a2c = AnswerFactory(submission=sub2, question=col_q, answer_type=AnswerType.NUMBER_SCALE)
        NumberScaleAnswer.objects.create(answer=a2r, val=2)
        NumberScaleAnswer.objects.create(answer=a2c, val=1)

        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(MOOD_URL.format(assignment.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalResponses"] == 2
        by_label = {item["label"]: item["count"] for item in data["quadrants"]}
        assert by_label["High Energy / Positive"] == 1
        assert by_label["Low Energy / Negative"] == 1
        assert by_label["High Energy / Negative"] == 0
        assert by_label["Low Energy / Positive"] == 0


# ===========================================================================
# VIZ-CN-01 — Researcher Anonymization (cross-cutting)
# ===========================================================================


@pytest.mark.django_db
class TestVizAnonymization:
    def test_VIZ_CN_01_researcher_with_sudo_sees_ids(
        self, api_client, researcher_user, teacher_user, admin_user
    ):
        """Researcher with VIEW_IDENTIFIABLE_VIZ sees all identifiable fields."""
        course, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.VIEW_IDENTIFIABLE_VIZ.value],
        )
        api_client.force_authenticate(user=researcher_user)

        # Dashboard
        resp = api_client.get(DASHBOARD_URL)
        assert "courseId" in resp.json()["courses"][0]

        # Course summary
        resp = api_client.get(COURSE_URL.format(course.id))
        assert "courseId" in resp.json()
        assert "assignmentId" in resp.json()["assignments"][0]

        # Assignment summary
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        assert "assignmentId" in resp.json()

    def test_VIZ_CN_01_researcher_without_sudo_anonymized(
        self, api_client, researcher_user, teacher_user, admin_user
    ):
        """Researcher without sudo sees no identifiable fields anywhere."""
        course, assignment, _ = _seed_course(teacher_user, admin_user=admin_user)
        api_client.force_authenticate(user=researcher_user)

        # Dashboard
        resp = api_client.get(DASHBOARD_URL)
        c = resp.json()["courses"][0]
        assert "courseId" not in c
        assert "courseName" not in c

        # Course summary
        resp = api_client.get(COURSE_URL.format(course.id))
        data = resp.json()
        assert "courseId" not in data
        assert "courseName" not in data
        a = data["assignments"][0]
        assert "assignmentId" not in a
        assert "assessmentTitle" not in a

        # Assignment summary
        resp = api_client.get(ASSIGNMENT_URL.format(assignment.id))
        data = resp.json()
        assert "assignmentId" not in data
        assert "assessmentTitle" not in data
