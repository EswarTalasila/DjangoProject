"""Integration tests for submissions routes."""

import pytest
from django.utils import timezone

from assessments.models import Assessment, GradingMode, Question, QuestionKind
from assignments.models import Assignment
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, ShortAnswerAnswer, Submission, SubmissionStatus

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestSubmissionRoutes:
    def _setup_course_assignment(self, teacher_user, student_user, admin_user):
        assessment = Assessment.objects.create(
            title="Assessment",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        question = Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Describe",
            max_points=5.0,
            auto_gradable=False,
            graded=False,
        )
        course = Course.objects.create(name="Biology", teacher_profile=teacher_user.teacher_profile)
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

    def test_student_can_submit_assignment(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that student can submit assignment."""
        assignment, question = self._setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {
                    "questionId": question.id,
                    "type": "SHORT_ANSWER",
                    "data": {"text": "My answer"},
                }
            ],
        }
        response = api_client.post(
            f"/api/v1/assignments/{assignment.id}/submissions", payload, format="json"
        )
        assert response.status_code == 201
        submission = Submission.objects.get(assignment=assignment, student=student_user)
        assert submission.status == SubmissionStatus.GRADED
        assert Answer.objects.filter(submission=submission).count() == 1

    def test_save_draft_sets_in_progress(self, api_client, teacher_user, student_user, admin_user):
        """Test that save draft sets in progress."""
        assignment, question = self._setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        payload = {
            "answers": [
                {
                    "questionId": question.id,
                    "type": "SHORT_ANSWER",
                    "data": {"text": "Draft"},
                }
            ]
        }
        response = api_client.patch(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/draft/",
            payload,
            format="json",
        )
        assert response.status_code == 200
        submission = Submission.objects.get(assignment=assignment, student=student_user)
        assert submission.status == SubmissionStatus.IN_PROGRESS

    def test_override_score_requires_teacher(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that override score requires teacher."""
        assignment, question = self._setup_course_assignment(teacher_user, student_user, admin_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.SUBMITTED,
        )
        answer = Answer.objects.create(
            submission=submission,
            question=question,
            answer_type="SHORT_ANSWER",
            score=0.0,
            skipped=False,
        )
        ShortAnswerAnswer.objects.create(answer=answer, text="Initial")

        api_client.force_authenticate(user=student_user)
        response = api_client.patch(
            f"/api/v1/submissions/{submission.id}/override-score", [5], format="json"
        )
        assert response.status_code == 403

        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(
            f"/api/v1/submissions/{submission.id}/override-score", [5], format="json"
        )
        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.status == SubmissionStatus.GRADED
        assert submission.score == 5

    def test_teacher_can_list_assignment_submissions(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that teacher can list assignment submissions."""
        assignment, _question = self._setup_course_assignment(
            teacher_user, student_user, admin_user
        )
        Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.SUBMITTED,
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_edit_submission_updates_status(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that edit submission updates status."""
        assignment, question = self._setup_course_assignment(teacher_user, student_user, admin_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.IN_PROGRESS,
        )
        answer = Answer.objects.create(
            submission=submission,
            question=question,
            answer_type="SHORT_ANSWER",
            score=0.0,
            skipped=False,
        )
        ShortAnswerAnswer.objects.create(answer=answer, text="Draft")

        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": assignment.id,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [
                {
                    "questionId": question.id,
                    "type": "SHORT_ANSWER",
                    "data": {"text": "Final"},
                }
            ],
        }
        response = api_client.patch("/api/v1/submissions/", payload, format="json")
        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.status == SubmissionStatus.GRADED

    def test_get_submission_by_id(self, api_client, teacher_user, student_user, admin_user):
        """Test that get submission by id."""
        assignment, _ = self._setup_course_assignment(teacher_user, student_user, admin_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.SUBMITTED,
        )
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f"/api/v1/submissions/{submission.id}")
        assert response.status_code == 200
        assert response.json()["id"] == submission.id

    def test_list_mine_requires_user_id(self, api_client, student_user):
        """Test that list mine requires user id."""
        api_client.force_authenticate(user=student_user)
        response = api_client.get("/api/v1/submissions/mine")
        assert response.status_code == 400

    def test_list_mine_returns_user_submissions(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that list mine returns user submissions."""
        assignment, _ = self._setup_course_assignment(teacher_user, student_user, admin_user)
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.SUBMITTED,
        )
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f"/api/v1/submissions/mine?userId={student_user.id}")
        assert response.status_code == 200
        payload = response.json()["results"]
        assert payload[0]["id"] == submission.id

    def test_teacher_submissions_route(self, api_client, teacher_user, admin_user):
        """Test that teacher submissions route."""
        assessment = Assessment.objects.create(
            title="Self",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        assignment = Assignment.objects.create(
            assessment=assessment,
            audience_type="TEACHER",
            course=None,
            created_by=teacher_user,
            open_at=timezone.now(),
            due_at=None,
            teacher=teacher_user,
        )
        Submission.objects.create(
            assignment=assignment,
            teacher=teacher_user,
            status=SubmissionStatus.SUBMITTED,
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/teachers/{teacher_user.id}/submissions")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1
