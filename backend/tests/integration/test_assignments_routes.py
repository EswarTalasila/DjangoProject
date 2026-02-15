"""Integration tests for assignments routes."""

import pytest
from django.utils import timezone

from assessments.models import Assessment, GradingMode, Question, QuestionKind
from assignments.models import Assignment
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import Answer, Submission


@pytest.mark.django_db
class TestAssignmentRoutes:
    def test_create_assignment_creates_submissions(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that create assignment creates submissions."""
        assessment = Assessment.objects.create(
            title="Assessment",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.NUMBER_SCALE,
            kind=QuestionKind.NUMBER_SCALE,
            prompt="Scale",
            max_points=5.0,
            auto_gradable=True,
            graded=False,
        )
        course = Course.objects.create(name="Science", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )

        api_client.force_authenticate(user=teacher_user)
        payload = {
            "assessmentId": assessment.id,
            "audienceType": "COURSE",
            "courseId": course.id,
            "openAt": timezone.now().isoformat(),
        }
        response = api_client.post("/api/v1/assignments/", payload, format="json")
        assert response.status_code == 201
        assignment = Assignment.objects.get(course=course)
        submissions = Submission.objects.filter(assignment=assignment, student=student_user)
        assert submissions.count() == 1
        assert Answer.objects.filter(submission=submissions.first()).count() == 1

    def test_list_assignments_for_user(self, api_client, teacher_user, student_user, admin_user):
        """Test that list assignments for user."""
        assessment = Assessment.objects.create(
            title="Assessment 2",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(name="English", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )
        Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=timezone.now(),
            due_at=None,
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_assignment_detail(self, api_client, teacher_user, admin_user):
        """Test that get assignment detail."""
        assessment = Assessment.objects.create(
            title="Assessment Detail",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(name="Music", teacher_profile=teacher_user.teacher_profile)
        assignment = Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=timezone.now(),
            due_at=None,
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/assignments/{assignment.id}")
        assert response.status_code == 200
        assert response.json()["id"] == assignment.id

    def test_list_assignments_by_course(self, api_client, teacher_user, admin_user, researcher_user):
        """Test that list assignments by course."""
        assessment = Assessment.objects.create(
            title="Assessment Course",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(name="Drama", teacher_profile=teacher_user.teacher_profile)
        Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=timezone.now(),
            due_at=None,
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

        api_client.force_authenticate(user=researcher_user)
        researcher_response = api_client.get(f"/api/v1/assignments/courses/{course.id}")
        assert researcher_response.status_code == 200
        assert len(researcher_response.json()) == 1

    def test_list_assignments_for_user_researcher_cross_user(
        self, api_client, teacher_user, student_user, researcher_user, admin_user
    ):
        """Researcher can list assignments for other users."""
        assessment = Assessment.objects.create(
            title="Assessment Researcher User List",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(name="Biology", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )
        Assignment.objects.create(
            assessment=assessment,
            audience_type="COURSE",
            course=course,
            created_by=teacher_user,
            open_at=timezone.now(),
            due_at=None,
        )

        api_client.force_authenticate(user=researcher_user)
        response = api_client.get(f"/api/v1/assignments/users/{student_user.id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_delete_assignment_removes_submissions(
        self, api_client, teacher_user, student_user, admin_user
    ):
        """Test that delete assignment removes submissions."""
        assessment = Assessment.objects.create(
            title="Assessment 3",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        course = Course.objects.create(name="History", teacher_profile=teacher_user.teacher_profile)
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
        Submission.objects.create(
            assignment=assignment,
            student=student_user,
            status="NOT_STARTED",
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/assignments/{assignment.id}")
        assert response.status_code == 200
        assert not Submission.objects.filter(assignment=assignment).exists()
