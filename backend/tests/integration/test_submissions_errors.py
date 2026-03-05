"""Integration tests for submissions errors."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.django_db
class TestSubmissionErrors:
    def test_create_submission_missing_assignment_returns_404(self, api_client, student_user):
        """Test that create submission missing assignment returns 404."""
        api_client.force_authenticate(user=student_user)
        payload = {
            "assignmentId": 999,
            "studentId": student_user.id,
            "status": "SUBMITTED",
            "answers": [],
        }
        response = api_client.post(
            "/api/v1/assignments/999/submissions",
            payload,
            format="json",
        )
        assert response.status_code == 404
        assert b"Assignment not found" in response.content

    def test_get_student_submission_missing_returns_404(
        self, api_client, student_user, teacher_user, admin_user
    ):
        """Test that get student submission missing returns 404."""
        from django.utils import timezone

        from assessments.models import Assessment, GradingMode
        from assignments.models import Assignment
        from courses.models import Course, Enrollment, EnrollmentStatus

        assessment = Assessment.objects.create(
            title="Missing Submission",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(
            name="Missing Course", teacher_profile=teacher_user.teacher_profile
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
        api_client.force_authenticate(user=student_user)
        response = api_client.get(
            f"/api/v1/students/{student_user.id}/assignments/{assignment.id}/submission/"
        )
        assert response.status_code == 404
        assert b"Submission not found" in response.content
