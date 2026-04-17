"""Integration tests for workflows extended."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from assignment_templates.models import Question


def login(client: APIClient, username: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/sessions",
        {"identifier": username, "password": password},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    access_cookie = response.cookies.get("access_token")
    assert access_cookie is not None
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_cookie.value}")
    return payload


def step(message: str) -> None:
    print(f"[workflow] {message}")


def create_admin_client(username: str, password: str) -> tuple[User, APIClient]:
    admin = User.objects.create_user(username=username, name="Admin", password=password)
    admin.is_staff = True
    admin.save()
    client = APIClient()
    client.force_authenticate(user=admin)
    return admin, client


def create_teacher_client(
    admin_client: APIClient, email_identifier: str, password: str
) -> APIClient:
    payload = {
        "email": (
            f"{email_identifier}.contact@example.com"
            if "@" not in email_identifier
            else email_identifier
        ),
        "password": password,
        "name": "Teacher",
        "role": "ROLE_TEACHER",
    }
    response = admin_client.post("/api/v1/users", payload, format="json")
    assert response.status_code == 201
    created_teacher = User.objects.get(email=payload["email"])
    client = APIClient()
    login(client, created_teacher.username, password)
    return client


def create_student(
    teacher_client: APIClient,
    name: str,
    course_id: int,
    consent: bool = True,
    password: str | None = None,
) -> tuple[int, str]:
    resolved_password = password or "studentpass"
    payload = {
        "name": name,
        "consent": consent,
        "password": resolved_password,
    }
    response = teacher_client.post(
        f"/api/v1/courses/{course_id}/students", payload, format="json"
    )
    assert response.status_code == 201
    return response.json()["id"], response.json()["username"]


@pytest.mark.django_db
class TestExtendedWorkflows:
    @pytest.mark.integration
    @pytest.mark.workflow
    @pytest.mark.workflow_teacher
    def test_course_crud_workflow(self):
        """Test that course crud workflow."""
        step("Create admin and login")
        _, admin_client = create_admin_client("admin-course@example.com", "adminpass")

        step("Create teacher and login")
        teacher_client = create_teacher_client(
            admin_client, "teacher-course@example.com", "teacherpass"
        )

        step("Teacher creates course")
        course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Biology"}, format="json"
        )
        assert course_response.status_code == 201
        course_id = course_response.json()["id"]

        step("Teacher updates course")
        update_response = teacher_client.patch(
            f"/api/v1/courses/{course_id}", {"name": "Biology 101"}, format="json"
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Biology 101"

        step("Teacher gets course")
        get_response = teacher_client.get(f"/api/v1/courses/{course_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == course_id

        step("Teacher lists courses")
        list_response = teacher_client.get("/api/v1/courses/")
        assert list_response.status_code == 200
        assert any(course["id"] == course_id for course in list_response.json()["results"])

        step("Teacher adds student")
        student_id, _ = create_student(
            teacher_client,
            "Student One",
            course_id,
        )

        step("Teacher lists students")
        students_response = teacher_client.get(f"/api/v1/courses/{course_id}/students")
        assert students_response.status_code == 200
        assert any(student["id"] == student_id for student in students_response.json()["results"])

        step("Teacher removes student")
        remove_response = teacher_client.delete(
            f"/api/v1/courses/{course_id}/students/{student_id}"
        )
        assert remove_response.status_code == 204

        step("Teacher confirms student removed")
        students_response = teacher_client.get(f"/api/v1/courses/{course_id}/students")
        assert students_response.status_code == 200
        assert not students_response.json()["results"]

        step("Teacher attempts to delete course (409 archival gate)")
        delete_response = teacher_client.delete(f"/api/v1/courses/{course_id}")
        assert delete_response.status_code == 409
        assert "archive" in delete_response.json()["detail"].lower()

    @pytest.mark.integration
    @pytest.mark.workflow
    @pytest.mark.workflow_admin
    def test_assignment_template_crud_workflow(self):
        """Test that assignment_template crud workflow."""
        step("Create admin and login")
        _, admin_client = create_admin_client("admin-assess@example.com", "adminpass")

        step("Create teacher and login")
        teacher_client = create_teacher_client(
            admin_client, "teacher-assess@example.com", "teacherpass"
        )

        step("Teacher cannot create assignment_template")
        teacher_response = teacher_client.post(
            "/api/v1/assignment-templates/",
            {"title": "Forbidden", "gradingMode": "AUTO", "questions": []},
            format="json",
        )
        assert teacher_response.status_code == 403

        step("Admin creates assignment_template")
        assignment_template_payload = {
            "title": "AssignmentTemplate A",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "SHORT_ANSWER",
                    "prompt": "Describe",
                    "maxPoints": 5,
                    "data": {"trim": True, "caseSensitive": False},
                },
                {
                    "type": "NUMBER_SCALE",
                    "prompt": "Rate",
                    "maxPoints": 3,
                    "data": {"min": 1, "max": 5, "target": 3},
                },
            ],
        }
        create_response = admin_client.post(
            "/api/v1/assignment-templates/", assignment_template_payload, format="json"
        )
        assert create_response.status_code == 201
        assignment_template_id = create_response.json()["id"]

        step("Admin updates assignment_template")
        update_payload = {
            "title": "AssignmentTemplate A Updated",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "MULTIPLE_CHOICE",
                    "prompt": "Pick",
                    "maxPoints": 2,
                    "data": {
                        "selectAll": False,
                        "choices": [
                            {"prompt": "A", "score": 1},
                            {"prompt": "B", "score": 2},
                        ],
                    },
                }
            ],
        }
        update_response = admin_client.patch(
            f"/api/v1/assignment-templates/{assignment_template_id}",
            update_payload,
            format="json",
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "AssignmentTemplate A Updated"
        assert Question.objects.filter(assignment_template_id=assignment_template_id).count() == 1

        step("Teacher lists assignment_templates")
        list_response = teacher_client.get("/api/v1/assignment-templates/")
        assert list_response.status_code == 200
        assert any(item["id"] == assignment_template_id for item in list_response.json()["results"])

        step("Teacher cannot delete assignment_template")
        forbidden_delete = teacher_client.delete(f"/api/v1/assignment-templates/{assignment_template_id}")
        assert forbidden_delete.status_code == 403

        step("Admin deletes unused assignment_template")
        delete_response = admin_client.delete(f"/api/v1/assignment-templates/{assignment_template_id}")
        assert delete_response.status_code == 204

        step("Admin confirms assignment_template removed")
        missing_response = admin_client.get(f"/api/v1/assignment-templates/{assignment_template_id}")
        assert missing_response.status_code == 404
        assert b"AssignmentTemplate not found" in missing_response.content

    @pytest.mark.integration
    @pytest.mark.workflow
    @pytest.mark.workflow_admin
    @pytest.mark.workflow_teacher
    @pytest.mark.workflow_student
    @pytest.mark.workflow_error
    def test_submission_workflow_with_errors(self):
        """Test that submission workflow with errors."""
        step("Create admin and login")
        _admin, admin_client = create_admin_client("admin-sub@example.com", "adminpass")

        step("Create teacher and login")
        teacher_client = create_teacher_client(
            admin_client, "teacher-sub@example.com", "teacherpass"
        )
        step("Create second teacher and login")
        other_teacher_client = create_teacher_client(
            admin_client, "teacher-sub-alt@example.com", "teacherpass"
        )

        step("Admin creates assignment_template")
        assignment_template_payload = {
            "title": "Submission AssignmentTemplate",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "SHORT_ANSWER",
                    "prompt": "Describe",
                    "maxPoints": 5,
                    "data": {"trim": True, "caseSensitive": False},
                }
            ],
        }
        assignment_template_response = admin_client.post(
            "/api/v1/assignment-templates/", assignment_template_payload, format="json"
        )
        assert assignment_template_response.status_code == 201
        assignment_template_id = assignment_template_response.json()["id"]

        step("Teacher creates courses")
        course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Course A"}, format="json"
        )
        assert course_response.status_code == 201
        course_id = course_response.json()["id"]
        other_course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Course B"}, format="json"
        )
        assert other_course_response.status_code == 201
        other_course_id = other_course_response.json()["id"]

        step("Teacher creates assignment for Course A")
        assignment_payload = {
            "title": "Submission Workflow Assignment",
            "assignmentTemplateId": assignment_template_id,
            "audienceType": "COURSE",
            "courseId": course_id,
            "openAt": timezone.now().isoformat(),
        }
        assignment_response = teacher_client.post(
            "/api/v1/assignments/", assignment_payload, format="json"
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]
        assignment_content_response = teacher_client.get(
            f"/api/v1/assignments/{assignment_id}/template"
        )
        assert assignment_content_response.status_code == 200
        question_id = assignment_content_response.json()["questions"][0]["id"]

        step("Teacher creates students")
        student_id, student_username = create_student(
            teacher_client,
            "Student One",
            course_id,
            password="studentpass",
        )
        other_student_id, other_student_username = create_student(
            teacher_client,
            "Student Two",
            other_course_id,
            password="otherpass",
        )

        step("Other teacher cannot list submissions for Course A")
        forbidden_list = other_teacher_client.get(
            f"/api/v1/assignments/{assignment_id}/submissions"
        )
        assert forbidden_list.status_code == 403

        step("Other student cannot draft in Course A")
        other_student_client = APIClient()
        login(other_student_client, other_student_username, "otherpass")
        draft_response = other_student_client.patch(
            f"/api/v1/students/{other_student_id}/assignments/{assignment_id}/draft/",
            {"answers": []},
            format="json",
        )
        assert draft_response.status_code == 403

        step("Student logs in")
        student_client = APIClient()
        login(student_client, student_username, "studentpass")

        step("Student saves draft")
        draft_response = student_client.patch(
            f"/api/v1/students/{student_id}/assignments/{assignment_id}/draft/",
            {
                "answers": [
                    {
                        "questionId": question_id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Draft"},
                    }
                ]
            },
            format="json",
        )
        assert draft_response.status_code == 200

        step("Student submits final answers")
        submit_response = student_client.post(
            f"/api/v1/assignments/{assignment_id}/submissions",
            {
                "assignmentId": assignment_id,
                "studentId": student_id,
                "status": "SUBMITTED",
                "answers": [
                    {
                        "questionId": question_id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Final"},
                    }
                ],
            },
            format="json",
        )
        assert submit_response.status_code == 201
        submission_id = submit_response.json()["id"]

        step("Student lists own submissions")
        list_me = student_client.get("/api/v1/submissions/me")
        assert list_me.status_code == 200
        assert any(item["id"] == submission_id for item in list_me.json()["results"])

        step("Teacher reviews submissions")
        review_response = teacher_client.get(f"/api/v1/assignments/{assignment_id}/submissions")
        assert review_response.status_code == 200
        assert any(item["id"] == submission_id for item in review_response.json()["results"])

        step("Teacher overrides score")
        override_response = teacher_client.patch(
            f"/api/v1/submissions/{submission_id}/override-score",
            [5],
            format="json",
        )
        assert override_response.status_code == 200
        assert override_response.json()["score"] == 5

        step("Other teacher cannot override score")
        forbidden_override = other_teacher_client.patch(
            f"/api/v1/submissions/{submission_id}/override-score",
            [4],
            format="json",
        )
        assert forbidden_override.status_code == 403

        step("Invalid assignment returns 404")
        missing = student_client.patch(
            f"/api/v1/students/{student_id}/assignments/999999/draft/",
            {"answers": []},
            format="json",
        )
        assert missing.status_code == 404
        assert b"Assignment not found" in missing.content
