"""Integration tests for workflows."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User, UserRole
from assessments.models import Question


def login(client: APIClient, username: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        {"username": username, "password": password},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['accessToken']}")
    return payload


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
        UserRole.objects.create(user=admin, role=Role.ADMIN)

        admin_client = APIClient()
        step("Admin login")
        login(admin_client, admin.username, "adminpass")

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
            "username": "teacher@example.com",
            "password": "teacherpass",
            "name": "Teacher",
            "role": "ROLE_TEACHER",
        }
        response = admin_client.post("/api/v1/auth/createuser", teacher_payload, format="json")
        assert response.status_code == 200

        teacher_client = APIClient()
        step("Teacher login")
        login(teacher_client, teacher_payload["username"], "teacherpass")

        step("Teacher creates course")
        course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Workflow Course"}, format="json"
        )
        assert course_response.status_code == 200
        course_id = course_response.json()["id"]

        student_payload = {
            "name": "Student",
            "username": "student@example.com",
            "courseId": course_id,
            "consent": True,
        }
        step("Teacher creates student")
        student_response = teacher_client.post("/api/v1/students/", student_payload, format="json")
        assert student_response.status_code == 200
        student_id = student_response.json()["id"]

        step("Admin sets student password")
        set_password = admin_client.post(
            f"/api/v1/auth/users/{student_id}/set-password",
            "studentpass",
            content_type="text/plain",
        )
        assert set_password.status_code == 200

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
        login(student_client, student_payload["username"], "studentpass")

        step("Student fetches assignments")
        assignments_response = student_client.get(f"/api/v1/assignments/users/{student_id}")
        assert assignments_response.status_code == 200
        assert any(a["id"] == assignment_id for a in assignments_response.json())

        step("Student saves draft submission")
        draft_response = student_client.put(
            f"/api/v1/students/{student_id}/assignments/{assignment_id}/draft",
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
        assert any(s["id"] == submission_id for s in submissions_response.json())

        step("Teacher overrides score")
        override_response = teacher_client.patch(
            f"/api/v1/submissions/{submission_id}/override-score",
            [5],
            format="json",
        )
        assert override_response.status_code == 200
        assert override_response.json()["score"] == 5
