"""Integration tests for workflows extended."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
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


def create_admin_client(username: str, password: str) -> tuple[User, APIClient]:
    admin = User.objects.create_user(username=username, name="Admin", password=password)
    admin.is_staff = True
    admin.save()
    client = APIClient()
    login(client, admin.username, password)
    return admin, client


def create_teacher_client(admin_client: APIClient, username: str, password: str) -> APIClient:
    payload = {
        "username": username,
        "password": password,
        "name": "Teacher",
        "role": "ROLE_TEACHER",
    }
    response = admin_client.post("/api/v1/auth/createuser", payload, format="json")
    assert response.status_code == 200
    client = APIClient()
    login(client, username, password)
    return client


def create_student(
    teacher_client: APIClient,
    name: str,
    username: str,
    course_id: int,
    consent: bool = True,
) -> int:
    payload = {
        "name": name,
        "username": username,
        "courseId": course_id,
        "consent": consent,
    }
    response = teacher_client.post("/api/v1/students/", payload, format="json")
    assert response.status_code == 200
    return response.json()["id"]


def set_password(admin_client: APIClient, user_id: int, password: str) -> None:
    response = admin_client.post(
        f"/api/v1/auth/users/{user_id}/set-password",
        password,
        content_type="text/plain",
    )
    assert response.status_code == 200


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
        assert course_response.status_code == 200
        course_id = course_response.json()["id"]

        step("Teacher updates course")
        update_response = teacher_client.put(
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
        assert any(course["id"] == course_id for course in list_response.json())

        step("Teacher adds student")
        student_id = create_student(
            teacher_client,
            "Student One",
            "student-course@example.com",
            course_id,
        )

        step("Teacher lists students")
        students_response = teacher_client.get(f"/api/v1/courses/{course_id}/students")
        assert students_response.status_code == 200
        assert any(student["id"] == student_id for student in students_response.json())

        step("Teacher removes student")
        remove_response = teacher_client.delete(
            f"/api/v1/courses/{course_id}/students/{student_id}"
        )
        assert remove_response.status_code == 200

        step("Teacher confirms student removed")
        students_response = teacher_client.get(f"/api/v1/courses/{course_id}/students")
        assert students_response.status_code == 200
        assert not students_response.json()

        step("Teacher deletes course")
        delete_response = teacher_client.delete(f"/api/v1/courses/{course_id}")
        assert delete_response.status_code == 204

        step("Teacher verifies course missing")
        missing_response = teacher_client.get(f"/api/v1/courses/{course_id}")
        assert missing_response.status_code == 404
        assert b"Course not found" in missing_response.content

    @pytest.mark.integration
    @pytest.mark.workflow
    @pytest.mark.workflow_admin
    def test_assessment_crud_workflow(self):
        """Test that assessment crud workflow."""
        step("Create admin and login")
        _, admin_client = create_admin_client("admin-assess@example.com", "adminpass")

        step("Create teacher and login")
        teacher_client = create_teacher_client(
            admin_client, "teacher-assess@example.com", "teacherpass"
        )

        step("Teacher cannot create assessment")
        teacher_response = teacher_client.post(
            "/api/v1/assessments/",
            {"title": "Forbidden", "gradingMode": "AUTO", "questions": []},
            format="json",
        )
        assert teacher_response.status_code == 403

        step("Admin creates assessment")
        assessment_payload = {
            "title": "Assessment A",
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
            "/api/v1/assessments/", assessment_payload, format="json"
        )
        assert create_response.status_code == 201
        assessment_id = create_response.json()["id"]

        step("Admin updates assessment")
        update_payload = {
            "title": "Assessment A Updated",
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
        update_response = admin_client.put(
            f"/api/v1/assessments/{assessment_id}",
            update_payload,
            format="json",
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Assessment A Updated"
        assert Question.objects.filter(assessment_id=assessment_id).count() == 1

        step("Teacher lists assessments")
        list_response = teacher_client.get("/api/v1/assessments/")
        assert list_response.status_code == 200
        assert any(item["id"] == assessment_id for item in list_response.json())

        step("Teacher cannot delete assessment")
        forbidden_delete = teacher_client.delete(f"/api/v1/assessments/{assessment_id}")
        assert forbidden_delete.status_code == 403

        step("Admin deletes assessment")
        delete_response = admin_client.delete(f"/api/v1/assessments/{assessment_id}")
        assert delete_response.status_code == 200

        step("Admin confirms assessment removed")
        missing_response = admin_client.get(f"/api/v1/assessments/{assessment_id}")
        assert missing_response.status_code == 404
        assert b"Assessment not found" in missing_response.content

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

        step("Admin creates assessment")
        assessment_payload = {
            "title": "Submission Assessment",
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
        assessment_response = admin_client.post(
            "/api/v1/assessments/", assessment_payload, format="json"
        )
        assert assessment_response.status_code == 201
        assessment_id = assessment_response.json()["id"]
        question_id = assessment_response.json()["questions"][0]["id"]

        step("Teacher creates courses")
        course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Course A"}, format="json"
        )
        assert course_response.status_code == 200
        course_id = course_response.json()["id"]
        other_course_response = teacher_client.post(
            "/api/v1/courses/", {"name": "Course B"}, format="json"
        )
        assert other_course_response.status_code == 200
        other_course_id = other_course_response.json()["id"]

        step("Teacher creates assignment for Course A")
        assignment_payload = {
            "assessmentId": assessment_id,
            "audienceType": "COURSE",
            "courseId": course_id,
            "openAt": timezone.now().isoformat(),
        }
        assignment_response = teacher_client.post(
            "/api/v1/assignments/", assignment_payload, format="json"
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        step("Teacher creates students")
        student_id = create_student(
            teacher_client,
            "Student One",
            "student-sub@example.com",
            course_id,
        )
        other_student_id = create_student(
            teacher_client,
            "Student Two",
            "student-sub-other@example.com",
            other_course_id,
        )

        step("Admin sets student passwords")
        set_password(admin_client, student_id, "studentpass")
        set_password(admin_client, other_student_id, "otherpass")

        step("Other teacher cannot list submissions for Course A")
        forbidden_list = other_teacher_client.get(
            f"/api/v1/assignments/{assignment_id}/submissions"
        )
        assert forbidden_list.status_code == 403

        step("Other student cannot draft in Course A")
        other_student_client = APIClient()
        login(other_student_client, "student-sub-other@example.com", "otherpass")
        draft_response = other_student_client.put(
            f"/api/v1/students/{other_student_id}/assignments/{assignment_id}/draft",
            {"answers": []},
            format="json",
        )
        assert draft_response.status_code == 403

        step("Student logs in")
        student_client = APIClient()
        login(student_client, "student-sub@example.com", "studentpass")

        step("Student saves draft")
        draft_response = student_client.put(
            f"/api/v1/students/{student_id}/assignments/{assignment_id}/draft",
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
        list_mine = student_client.get(f"/api/v1/submissions/mine?userId={student_id}")
        assert list_mine.status_code == 200
        assert any(item["id"] == submission_id for item in list_mine.json())

        step("Teacher reviews submissions")
        review_response = teacher_client.get(f"/api/v1/assignments/{assignment_id}/submissions")
        assert review_response.status_code == 200
        assert any(item["id"] == submission_id for item in review_response.json())

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

        step("Teacher-self assess workflow")
        teacher_self_assess = teacher_client.post(
            f"/api/v1/assessments/{assessment_id}/teacher-self-assess",
            [
                {
                    "questionId": question_id,
                    "type": "SHORT_ANSWER",
                    "data": {"text": "Self"},
                }
            ],
            format="json",
        )
        assert teacher_self_assess.status_code == 201

        step("Invalid assignment returns 404")
        missing = student_client.put(
            f"/api/v1/students/{student_id}/assignments/999999/draft",
            {"answers": []},
            format="json",
        )
        assert missing.status_code == 404
        assert b"Assignment not found" in missing.content
