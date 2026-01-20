"""Integration tests for visualizations routes."""

import pytest
from django.utils import timezone

from assessments.models import Assessment, GradingMode, Question, QuestionKind
from assignments.models import Assignment
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, ShortAnswerAnswer, Submission, SubmissionStatus


@pytest.mark.django_db
class TestVisualizationRoutes:
    def test_teacher_can_view_visualizations(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that teacher can view visualizations."""
        assessment = Assessment.objects.create(
            title="Assessment",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        question = Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q",
            max_points=5.0,
            auto_gradable=False,
            graded=True,
        )
        course = Course.objects.create(name="Art", teacher_profile=teacher_user.teacher_profile)
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
        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status=SubmissionStatus.GRADED,
            score=5,
            submitted_at=timezone.now(),
        )
        answer = Answer.objects.create(
            submission=submission,
            question=question,
            answer_type="SHORT_ANSWER",
            score=5,
            skipped=False,
        )
        ShortAnswerAnswer.objects.create(answer=answer, text="Answer")

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post("/api/v1/visualization/", {}, format="json")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["courseName"] == "Art"

    def test_student_cannot_view_visualizations(self, api_client, student_user):
        """Test that student cannot view visualizations."""
        api_client.force_authenticate(user=student_user)
        response = api_client.post("/api/v1/visualization/", {}, format="json")
        assert response.status_code == 403
