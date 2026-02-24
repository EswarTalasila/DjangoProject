"""Integration tests for workflows."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from assessments.models import Question


def login(client: APIClient, username: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/sessions",
        {"identifier": username, "password": password},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['accessToken']}")
    return payload


def admin_authenticate(client: APIClient, user: User) -> None:
    """Authenticate admin via force_authenticate (admins are blocked from API login)."""
    client.force_authenticate(user=user)


def step(message: str) -> None:
    print(f"[workflow] {message}")


@pytest.mark.django_db
class TestWorkflows:
    @pytest.mark.integration
    @pytest.mark.workflow
    @pytest.mark.workflow_teacher
    @pytest.mark.workflow_student
    def test_teacher_student_full_flow(self):
        """Test that teacher student full flow."""
        step("Create admin account")
        admin = User.objects.create_user(
            username="admin@example.com",
            name="Admin",
            password="adminpass",
        )
        admin.is_staff = True
        admin.save()

        admin_client = APIClient()
        step("Admin login (force_authenticate — admins blocked from API login)")
        admin_authenticate(admin_client, admin)

        step("Admin creates assessment")
        assessment_payload = {
            "title": "Workflow Assessment",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "SHORT_ANSWER",
                    "prompt": "Describe your day",
                    "maxPoints": 5,
                    "data": {"trim": True, "caseSensitive": False},
                }
            ],
        }
        assessment_response = admin_client.post(
            "/api/v1/assessments/", assessment_payload, format="json"
        )
        assert assessment_response.status_code == 201
        assessment_id = assessment_response.json()["id"]
        question = Question.objects.filter(assessment_id=assessment_id).first()
        assert question is not None

        step("Admin creates teacher")
        teacher_payload = {
            "email": "teacher@example.com",
            "password": "teacherpass",
            "name": "Teacher",
            "role": "ROLE_TEACHER",
        }
        response = admin_client.post("/api/v1/users", teacher_payload, format="json")
        assert response.status_code == 201
        teacher_username = User.objects.get(email="teacher@example.com").username

        teacher_client = APIClient()
        step("Teacher login")
        login(teacher_client, teacher_username, "teacherpass")

        step("Teacher creates course")
        course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Workflow Course"}, format="json"
        )
        assert course_response.status_code == 201
        course_id = course_response.json()["id"]

        student_payload = {
            "name": "Student",
            "courseId": course_id,
            "consent": True,
            "password": "studentpass",
        }
        step("Teacher creates student")
        student_response = teacher_client.post("/api/v1/students/", student_payload, format="json")
        assert student_response.status_code == 201
        student_id = student_response.json()["id"]
        student_username = student_response.json()["username"]

        assignment_payload = {
            "assessmentId": assessment_id,
            "audienceType": "COURSE",
            "courseId": course_id,
            "openAt": timezone.now().isoformat(),
        }
        step("Teacher creates assignment")
        assignment_response = teacher_client.post(
            "/api/v1/assignments/", assignment_payload, format="json"
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        student_client = APIClient()
        step("Student login")
        login(student_client, student_username, "studentpass")

        step("Student fetches assignments")
        assignments_response = student_client.get(f"/api/v1/assignments/users/{student_id}")
        assert assignments_response.status_code == 200
        assert any(a["id"] == assignment_id for a in assignments_response.json()["results"])

        step("Student saves draft submission")
        draft_response = student_client.patch(
            f"/api/v1/students/{student_id}/assignments/{assignment_id}/draft/",
            {
                "answers": [
                    {
                        "questionId": question.id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Draft"},
                    }
                ]
            },
            format="json",
        )
        assert draft_response.status_code == 200
        assert draft_response.json()["status"] == "IN_PROGRESS"

        step("Student submits final answers")
        submit_response = student_client.post(
            f"/api/v1/assignments/{assignment_id}/submissions",
            {
                "assignmentId": assignment_id,
                "studentId": student_id,
                "status": "SUBMITTED",
                "answers": [
                    {
                        "questionId": question.id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Final"},
                    }
                ],
            },
            format="json",
        )
        assert submit_response.status_code == 201
        assert submit_response.json()["status"] == "GRADED"
        submission_id = submit_response.json()["id"]

        step("Teacher reviews submissions")
        submissions_response = teacher_client.get(
            f"/api/v1/assignments/{assignment_id}/submissions"
        )
        assert submissions_response.status_code == 200
        assert any(s["id"] == submission_id for s in submissions_response.json()["results"])

        step("Teacher overrides score")
        override_response = teacher_client.patch(
            f"/api/v1/submissions/{submission_id}/override-score",
            [5],
            format="json",
        )
        assert override_response.status_code == 200
        assert override_response.json()["score"] == 5
