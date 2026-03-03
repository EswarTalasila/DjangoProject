"""FR-08 Submissions — integration tests with traceability.

Naming convention:
  test_SUB_UC_XX_<scenario>   — use-case happy / alt paths
  test_SUB_CN_XX_<scenario>   — constraint verification
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from assessments.models import (
    Assessment,
    GradingMode,
    McqChoice,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    QuestionKind,
    ScoringPolicy,
)
from assignments.models import Assignment, AssignmentStatus
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import (
    Answer,
    AnswerType,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_course_assignment(
    teacher_user,
    student_user,
    admin_user,
    *,
    grading_mode=GradingMode.AUTO,
    scoring_policy=ScoringPolicy.STANDARD,
    question_kind=QuestionKind.SHORT_ANSWER,
    auto_gradable=False,
    assignment_status=AssignmentStatus.ACTIVE,
    open_at=None,
    due_at=None,
):
    """Create a minimal course → assessment → assignment → enrollment graph."""
    assessment = Assessment.objects.create(
        title="Assessment",
        grading_mode=grading_mode,
        scoring_policy=scoring_policy,
        created_by_admin=admin_user,
    )
    question = Question.objects.create(
        assessment=assessment,
        question_type=question_kind,
        kind=question_kind,
        prompt="Q1",
        max_points=5.0,
        auto_gradable=auto_gradable,
        graded=False,
    )
    course = Course.objects.create(
        name="Course",
        teacher_profile=teacher_user.teacher_profile,
    )
    Enrollment.objects.create(
        course=course,
        student_profile=student_user.student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    assignment = Assignment.objects.create(
        assessment=assessment,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=open_at or timezone.now(),
        due_at=due_at,
        status=assignment_status,
    )
    return assignment, question, course


def _make_mcq_assignment(teacher_user, student_user, admin_user, *, grading_mode=GradingMode.AUTO):
    """Create assignment with an MCQ question (auto-gradable)."""
    assessment = Assessment.objects.create(
        title="MCQ Assessment",
        grading_mode=grading_mode,
        scoring_policy=ScoringPolicy.STANDARD,
        created_by_admin=admin_user,
    )
    question = Question.objects.create(
        assessment=assessment,
        question_type=QuestionKind.MULTIPLE_CHOICE,
        kind=QuestionKind.MULTIPLE_CHOICE,
        prompt="Pick one",
        max_points=10.0,
        auto_gradable=True,
        graded=False,
    )
    MultipleChoiceQuestion.objects.create(question=question, select_all=False)
    McqChoice.objects.create(question=question, choice_text="Wrong", points=0)
    McqChoice.objects.create(question=question, choice_text="Right", points=10)
    course = Course.objects.create(
        name="MCQ Course",
        teacher_profile=teacher_user.teacher_profile,
    )
    Enrollment.objects.create(
        course=course,
        student_profile=student_user.student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    assignment = Assignment.objects.create(
        assessment=assessment,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=timezone.now(),
        due_at=None,
    )
    return assignment, question


def _short_answer_payload(question, student_user, text="answer"):
    return {
        "assignmentId": question.assessment_id,
        "studentId": student_user.id,
        "status": "SUBMITTED",
        "answers": [
            {"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": text}},
        ],
    }


def _make_submission(assignment, student_user, status=SubmissionStatus.NOT_STARTED):
    return Submission.objects.create(
        assignment=assignment,
        student=student_user,
        status=status,
    )


def _add_answer(submission, question, *, answer_type="SHORT_ANSWER", text="hi"):
    answer = Answer.objects.create(
        submission=submission,
        question=question,
        answer_type=answer_type,
        score=0.0,
        skipped=False,
    )
    if answer_type == AnswerType.SHORT_ANSWER:
        ShortAnswerAnswer.objects.create(answer=answer, text=text)
    return answer


# ---------------------------------------------------------------------------
# SUB-UC-01 — Save Draft
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSaveDraft:
    """SUB-UC-01: PATCH /students/{id}/assignments/{id}/draft"""

    def test_SUB_UC_01_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student saves draft — status becomes IN_PROGRESS."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "answers": [
                {"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "Draft"}},
            ]
        }
        r = api_client.patch(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/",
            payload,
            format="json",
        )
        assert r.status_code == 200
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.status == SubmissionStatus.IN_PROGRESS
        assert sub.submitted_at is None  # SUB-CN-01 fix: no submitted_at for drafts

    def test_SUB_UC_01_E2_non_student_rejected(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Non-student (teacher) cannot save draft."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.patch(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/",
            {"answers": []},
            format="json",
        )
        assert r.status_code == 403

    def test_SUB_UC_01_E3_student_id_mismatch(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot save draft for another student."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)
        assignment, question, course = _make_course_assignment(
            teacher_user, student_user, admin_user
        )
        Enrollment.objects.create(
            course=course,
            student_profile=other.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )
        api_client.force_authenticate(user=student_user)
        r = api_client.patch(
            f"/api/v1/students/{other.id}/assignments/{assignment.id}/draft/",
            {"answers": []},
            format="json",
        )
        assert r.status_code == 403

    def test_SUB_UC_01_E5_archived_assignment(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Draft save rejected with 409 when assignment is archived (SUB-CN-07)."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, assignment_status=AssignmentStatus.ARCHIVED
        )
        api_client.force_authenticate(user=student_user)
        r = api_client.patch(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/",
            {"answers": []},
            format="json",
        )
        assert r.status_code == 409

    def test_SUB_UC_01_E6_not_enrolled(self, api_client, teacher_user, student_user, admin_user):
        """Draft save rejected when student not enrolled in course."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        outsider = UserFactory()
        UserRole.objects.create(user=outsider, role=Role.STUDENT)
        StudentProfile.objects.create(user=outsider, created_by=admin_user, consent=False)
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=outsider)
        r = api_client.patch(
            f"/api/v1/students/{outsider.id}/assignments/{assignment.id}/draft/",
            {"answers": []},
            format="json",
        )
        assert r.status_code == 403

    def test_SUB_CN_10_draft_replaces_answers(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Drafts fully replace existing answers (SUB-CN-10)."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        url = f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/"
        # First draft
        api_client.patch(
            url,
            {"answers": [{"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "v1"}}]},
            format="json",
        )
        # Second draft replaces
        api_client.patch(
            url,
            {"answers": [{"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "v2"}}]},
            format="json",
        )
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.answers.count() == 1
        assert sub.answers.first().short_answer.text == "v2"


# ---------------------------------------------------------------------------
# SUB-UC-02 — Submit Assignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubmitAssignment:
    """SUB-UC-02: POST /assignments/{id}/submissions"""

    def test_SUB_UC_02_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student submits final answers — submission created."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "Final"}},
            ],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 201
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.submitted_at is not None

    def test_SUB_UC_02_E2_non_student_rejected(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher cannot submit."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 403

    def test_SUB_UC_02_E2_admin_cannot_submit(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Admin cannot submit on behalf of student (high-risk auth regression)."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=admin_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 403

    def test_SUB_UC_02_E2_researcher_cannot_submit(
        self, api_client, teacher_user, student_user, admin_user, researcher_user
    ):
        """Researcher cannot submit on behalf of student (high-risk auth regression)."""
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=researcher_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 403

    def test_SUB_UC_02_E4_archived_assignment(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Submit rejected with 409 when assignment is archived (SUB-CN-06)."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, assignment_status=AssignmentStatus.ARCHIVED
        )
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 409

    def test_SUB_UC_02_E5_not_enrolled(self, api_client, teacher_user, student_user, admin_user):
        """Submit rejected when student not enrolled."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        outsider = UserFactory()
        UserRole.objects.create(user=outsider, role=Role.STUDENT)
        StudentProfile.objects.create(user=outsider, created_by=admin_user, consent=False)
        assignment, question, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=outsider)
        payload = {
            "assignmentId": assignment.id,
            "studentId": outsider.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 403

    def test_SUB_UC_02_openAt_gate(self, api_client, teacher_user, student_user, admin_user):
        """Submit rejected when assignment has not opened yet."""
        future = timezone.now() + timedelta(days=1)
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, open_at=future
        )
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUB-UC-03 — Grade Submission (override-score)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGradeSubmission:
    """SUB-UC-03: PATCH /submissions/{id}/override-score"""

    def test_SUB_UC_03_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher can override score."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [5], format="json"
        )
        assert r.status_code == 200
        sub.refresh_from_db()
        assert sub.status == SubmissionStatus.GRADED
        assert sub.score == 5

    def test_SUB_UC_03_ADMIN(self, api_client, teacher_user, student_user, admin_user):
        """Admin can override score."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=admin_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [3], format="json"
        )
        assert r.status_code == 200
        sub.refresh_from_db()
        assert sub.score == 3

    def test_SUB_UC_03_E2_student_cannot_grade(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot override scores."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=student_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [5], format="json"
        )
        assert r.status_code == 403

    def test_SUB_UC_03_E4_teacher_not_owner(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher cannot grade assignment they don't own."""
        from tests.factories import UserFactory
        from accounts.models import Role, TeacherProfile, UserRole

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=other_teacher)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [5], format="json"
        )
        assert r.status_code == 403

    def test_SUB_CN_05_score_calculation(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Score = sum of per-answer scores (SUB-CN-05)."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        # Add second question
        q2 = Question.objects.create(
            assessment=assignment.assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q2",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question, text="a1")
        _add_answer(sub, q2, text="a2")
        api_client.force_authenticate(user=teacher_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [3, 4], format="json"
        )
        assert r.status_code == 200
        sub.refresh_from_db()
        assert sub.score == 7

    def test_SUB_CN_05_bonus_points(self, api_client, teacher_user, student_user, admin_user):
        """Extra score entry beyond answers count is bonus (SUB-CN-05)."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=teacher_user)
        # [5 for answer, 2 as bonus]
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [5, 2], format="json"
        )
        assert r.status_code == 200
        sub.refresh_from_db()
        assert sub.score == 7  # 5 + 2 bonus

    def test_SUB_UC_03_completion_policy_blocked(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Completion scoring policy blocks manual override."""
        assignment, question, _ = _make_course_assignment(
            teacher_user,
            student_user,
            admin_user,
            grading_mode=GradingMode.MANUAL,
            scoring_policy=ScoringPolicy.COMPLETION,
        )
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        _add_answer(sub, question)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [5], format="json"
        )
        assert r.status_code == 400
        assert "completion" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# SUB-UC-04 — Get Submission Detail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetSubmissionDetail:
    """SUB-UC-04: GET /submissions/{id}"""

    def test_SUB_UC_04_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student can view own submission."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 200
        assert r.json()["id"] == sub.id

    def test_SUB_UC_04_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher can view submission for their assignment."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 200

    def test_SUB_UC_04_ADMIN(self, api_client, teacher_user, student_user, admin_user):
        """Admin can view any submission."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=admin_user)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 200

    def test_SUB_UC_04_RESEARCHER(
        self, api_client, teacher_user, student_user, admin_user, researcher_user
    ):
        """Researcher can view any submission."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=researcher_user)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 200

    def test_SUB_UC_04_E2_student_cannot_view_others(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot view another student's submission."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=other)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 403

    def test_SUB_UC_04_E3_teacher_not_owner(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher cannot view submission for assignment they don't own."""
        from tests.factories import UserFactory
        from accounts.models import Role, TeacherProfile, UserRole

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=other_teacher)
        r = api_client.get(f"/api/v1/submissions/{sub.id}")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUB-UC-05 — Get Student Assignment Submission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetStudentAssignmentSubmission:
    """SUB-UC-05: GET /students/{id}/assignments/{id}/submission"""

    def test_SUB_UC_05_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student can view own submission for assignment."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        sub = _make_submission(assignment, student_user, SubmissionStatus.IN_PROGRESS)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/submission/"
        )
        assert r.status_code == 200
        assert r.json()["id"] == sub.id

    def test_SUB_UC_05_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher can view student's submission for their assignment."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/submission/"
        )
        assert r.status_code == 200

    def test_SUB_UC_05_ADMIN(self, api_client, teacher_user, student_user, admin_user):
        """Admin can view any student's submission."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=admin_user)
        r = api_client.get(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/submission/"
        )
        assert r.status_code == 200

    def test_SUB_UC_05_E3_student_cannot_view_other(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot view another student's assignment submission."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=other)
        r = api_client.get(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/submission/"
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUB-UC-06 — List Submissions by Assignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListByAssignment:
    """SUB-UC-06: GET /assignments/{id}/submissions"""

    def test_SUB_UC_06_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher can list submissions for own assignment."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_SUB_UC_06_ADMIN(self, api_client, teacher_user, student_user, admin_user):
        """Admin can list any assignment's submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=admin_user)
        r = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert r.status_code == 200

    def test_SUB_UC_06_RESEARCHER(
        self, api_client, teacher_user, student_user, admin_user, researcher_user
    ):
        """Researcher can list any assignment's submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=researcher_user)
        r = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert r.status_code == 200

    def test_SUB_UC_06_E2_student_cannot_list(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot list all submissions for an assignment."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert r.status_code == 403

    def test_SUB_UC_06_E3_teacher_not_owner(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Teacher cannot list submissions for assignment they don't own."""
        from tests.factories import UserFactory
        from accounts.models import Role, TeacherProfile, UserRole

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=other_teacher)
        r = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUB-UC-07 — List Student Submissions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListStudentSubmissions:
    """SUB-UC-07: GET /students/{id}/submissions"""

    def test_SUB_UC_07_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student can list own submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(f"/api/v1/students/{student_user.id}/submissions/")
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_SUB_UC_07_ADMIN(self, api_client, teacher_user, student_user, admin_user):
        """Admin can list any student's submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=admin_user)
        r = api_client.get(f"/api/v1/students/{student_user.id}/submissions/")
        assert r.status_code == 200

    def test_SUB_UC_07_TEACHER(self, api_client, teacher_user, student_user, admin_user):
        """Teacher can list student's submissions for courses they own."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(f"/api/v1/students/{student_user.id}/submissions/")
        assert r.status_code == 200

    def test_SUB_UC_07_E2_student_cannot_view_other(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Student cannot list another student's submissions."""
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=other)
        r = api_client.get(f"/api/v1/students/{student_user.id}/submissions/")
        assert r.status_code == 403

    def test_SUB_UC_07_RESEARCHER(
        self, api_client, teacher_user, student_user, admin_user, researcher_user
    ):
        """Researcher can list any student's submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user)
        api_client.force_authenticate(user=researcher_user)
        r = api_client.get(f"/api/v1/students/{student_user.id}/submissions/")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# SUB-UC-08 — List My Submissions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListMine:
    """SUB-UC-08: GET /submissions/mine"""

    def test_SUB_UC_08_STUDENT(self, api_client, teacher_user, student_user, admin_user):
        """Student can list own submissions."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(f"/api/v1/submissions/mine?userId={student_user.id}")
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_SUB_UC_08_E1_missing_userId(self, api_client, student_user):
        """Missing userId returns 400."""
        api_client.force_authenticate(user=student_user)
        r = api_client.get("/api/v1/submissions/mine")
        assert r.status_code == 400

    def test_SUB_UC_08_E2_self_only(self, api_client, teacher_user, student_user, admin_user):
        """Non-admin/researcher cannot query another user's submissions."""
        api_client.force_authenticate(user=student_user)
        r = api_client.get(f"/api/v1/submissions/mine?userId={teacher_user.id}")
        assert r.status_code == 403

    def test_SUB_UC_08_admin_can_query_others(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Admin can query any user's submissions."""
        api_client.force_authenticate(user=admin_user)
        r = api_client.get(f"/api/v1/submissions/mine?userId={student_user.id}")
        assert r.status_code == 200

    def test_SUB_UC_08_status_filter(self, api_client, teacher_user, student_user, admin_user):
        """Status filter narrows results."""
        assignment, _, _ = _make_course_assignment(teacher_user, student_user, admin_user)
        _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        api_client.force_authenticate(user=student_user)
        r = api_client.get(
            f"/api/v1/submissions/mine?userId={student_user.id}&status=NOT_STARTED"
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 0


# ---------------------------------------------------------------------------
# SUB-CN-03 — Auto-Grading on Submit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAutoGrading:
    """SUB-CN-03: Auto-grading on submit."""

    def test_SUB_CN_03_mcq_auto_grade(self, api_client, teacher_user, student_user, admin_user):
        """MCQ auto-grades on submit in AUTO mode → GRADED."""
        assignment, question = _make_mcq_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {
                    "questionId": question.id,
                    "type": "MULTIPLE_CHOICE",
                    "data": {"selected": [1]},  # index 1 = "Right" (10 pts)
                },
            ],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 201
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.status == SubmissionStatus.GRADED
        assert sub.score == 10.0

    def test_SUB_CN_03_hybrid_mode_stays_submitted(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """HYBRID mode: auto-scores MCQ but status stays SUBMITTED awaiting manual."""
        assignment, question = _make_mcq_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.HYBRID
        )
        # Add a short-answer question needing manual grading
        Question.objects.create(
            assessment=assignment.assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Explain",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        api_client.force_authenticate(user=student_user)
        sa_q = Question.objects.filter(
            assessment=assignment.assessment, kind=QuestionKind.SHORT_ANSWER
        ).first()
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {"questionId": question.id, "type": "MULTIPLE_CHOICE", "data": {"selected": [1]}},
                {"questionId": sa_q.id, "type": "SHORT_ANSWER", "data": {"text": "Because"}},
            ],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 201
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        # HYBRID: auto-grades MCQ but status stays SUBMITTED (needs manual for SA)
        assert sub.status == SubmissionStatus.SUBMITTED

    def test_SUB_CN_03_completion_policy(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Completion policy → score=100, status=GRADED."""
        assignment, question, _ = _make_course_assignment(
            teacher_user,
            student_user,
            admin_user,
            grading_mode=GradingMode.MANUAL,
            scoring_policy=ScoringPolicy.COMPLETION,
        )
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "Present"}},
            ],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 201
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.score == 100
        assert sub.status == SubmissionStatus.GRADED


# ---------------------------------------------------------------------------
# SUB-CN-05 — HYBRID mode scoring
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHybridScoring:
    """SUB-CN-05: HYBRID mode only applies manual scores to SHORT_ANSWER."""

    def test_SUB_CN_05_hybrid_mode_scoring(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """HYBRID override-score only touches SHORT_ANSWER, preserves auto-scored MCQ."""
        assignment, mcq_q = _make_mcq_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.HYBRID
        )
        sa_q = Question.objects.create(
            assessment=assignment.assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Explain",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        # Pre-create submission with answers
        sub = _make_submission(assignment, student_user, SubmissionStatus.SUBMITTED)
        mcq_answer = Answer.objects.create(
            submission=sub, question=mcq_q, answer_type=AnswerType.MULTIPLE_CHOICE,
            score=10.0, skipped=False,
        )
        MultipleChoiceAnswer.objects.create(answer=mcq_answer)
        MultipleChoiceSelected.objects.create(answer=mcq_answer.multiple_choice, choice_index=1)
        sa_answer = Answer.objects.create(
            submission=sub, question=sa_q, answer_type=AnswerType.SHORT_ANSWER,
            score=0.0, skipped=False,
        )
        ShortAnswerAnswer.objects.create(answer=sa_answer, text="Because reasons")

        api_client.force_authenticate(user=teacher_user)
        r = api_client.patch(
            f"/api/v1/submissions/{sub.id}/override-score", [4], format="json"
        )
        assert r.status_code == 200
        sub.refresh_from_db()
        # MCQ auto-score preserved (10) + SA manual score (4) = 14
        assert sub.score == 14.0
        assert sub.status == SubmissionStatus.GRADED


# ---------------------------------------------------------------------------
# SUB-CN-01 — Status Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStatusLifecycle:
    """SUB-CN-01: Status transitions must be forward-only."""

    def test_SUB_CN_01_draft_then_submit(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Normal flow: NOT_STARTED → IN_PROGRESS → SUBMITTED."""
        assignment, question, _ = _make_course_assignment(
            teacher_user, student_user, admin_user, grading_mode=GradingMode.MANUAL
        )
        api_client.force_authenticate(user=student_user)
        # Save draft
        api_client.patch(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/",
            {"answers": [{"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "wip"}}]},
            format="json",
        )
        sub = Submission.objects.get(assignment=assignment, student=student_user)
        assert sub.status == SubmissionStatus.IN_PROGRESS
        assert sub.submitted_at is None

        # Final submit
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {"questionId": question.id, "type": "SHORT_ANSWER", "data": {"text": "final"}},
            ],
        }
        r = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert r.status_code == 201
        sub.refresh_from_db()
        assert sub.status == SubmissionStatus.SUBMITTED
        assert sub.submitted_at is not None
