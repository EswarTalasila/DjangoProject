"""Integration tests for courses routes."""

import pytest

from accounts.models import User
from courses.models import Course, Enrollment

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestCourseRoutes:
    def test_teacher_can_create_course(self, api_client, teacher_user):
        """Test that teacher can create course."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post("/api/v1/courses/", {"name": "Biology"}, format="json")
        assert response.status_code == 201
        assert Course.objects.filter(name="Biology").exists()

    def test_admin_cannot_create_course(self, api_client, admin_user):
        """Test that admin cannot create course."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post("/api/v1/courses/", {"name": "Physics"}, format="json")
        assert response.status_code == 403

    def test_list_courses_by_role(self, api_client, teacher_user, admin_user):
        """Test that list courses by role."""
        Course.objects.create(name="Teacher Course", teacher_profile=teacher_user.teacher_profile)
        Course.objects.create(name="Admin Visible", teacher_profile=teacher_user.teacher_profile)

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2

    def test_course_detail_update_delete(self, api_client, teacher_user):
        """Test that course detail update delete."""
        course = Course.objects.create(
            name="Old Name", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f"/api/v1/courses/{course.id}")
        assert response.status_code == 200

        response = api_client.patch(
            f"/api/v1/courses/{course.id}", {"name": "New Name"}, format="json"
        )
        assert response.status_code == 200
        course.refresh_from_db()
        assert course.name == "New Name"

        response = api_client.delete(f"/api/v1/courses/{course.id}")
        assert response.status_code == 204
        assert not Course.objects.filter(id=course.id).exists()

    def test_teacher_list_students_in_course(self, api_client, teacher_user, student_user):
        """Test that teacher list students in course."""
        course = Course.objects.create(name="Math", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status="ACTIVE"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f"/api/v1/courses/{course.id}/students")
        assert response.status_code == 200
        payload = response.json()["results"]
        assert payload[0]["username"] == student_user.username

    def test_add_student_endpoint_creates_enrollment(self, api_client, teacher_user):
        """Test that add student endpoint creates enrollment."""
        course = Course.objects.create(name="History", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "name": "New Student",
            "courseId": course.id,
            "consent": True,
        }
        response = api_client.post("/api/v1/students/", payload, format="json")
        assert response.status_code == 201
        assert Enrollment.objects.filter(course=course).exists()

    def test_bulk_add_students_returns_count(self, api_client, teacher_user):
        """Test that bulk add students returns count."""
        course = Course.objects.create(name="Geo", teacher_profile=teacher_user.teacher_profile)
        api_client.force_authenticate(user=teacher_user)
        payload = [
            {
                "name": "Student One",
                "courseId": course.id,
                "consent": True,
            },
            {
                "name": "Student Two",
                "courseId": course.id,
                "consent": False,
            },
        ]
        response = api_client.post("/api/v1/students/bulk/", payload, format="json")
        assert response.status_code == 201
        assert response.json() == 2

    def test_same_name_creates_distinct_usernames(self, api_client, teacher_user):
        """Adding two students with the same name generates unique usernames."""
        course_one = Course.objects.create(
            name="Course One", teacher_profile=teacher_user.teacher_profile
        )
        course_two = Course.objects.create(
            name="Course Two", teacher_profile=teacher_user.teacher_profile
        )

        api_client.force_authenticate(user=teacher_user)
        first_payload = {
            "name": "Shared Student",
            "courseId": course_one.id,
            "consent": True,
        }
        first_response = api_client.post("/api/v1/students/", first_payload, format="json")
        assert first_response.status_code == 201

        second_payload = {
            "name": "Shared Student",
            "courseId": course_two.id,
            "consent": True,
        }
        second_response = api_client.post("/api/v1/students/", second_payload, format="json")
        assert second_response.status_code == 201

        usernames = {
            enrollment.student_profile.user.username
            for enrollment in Enrollment.objects.filter(course__in=[course_one, course_two])
        }
        assert len(usernames) == 2

    def test_remove_student_deletes_user(self, api_client, teacher_user, student_user):
        """Test that remove student deletes user."""
        course = Course.objects.create(name="Chem", teacher_profile=teacher_user.teacher_profile)
        Enrollment.objects.create(
            course=course, student_profile=student_user.student_profile, status="ACTIVE"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/courses/{course.id}/students/{student_user.id}")
        assert response.status_code == 204
        assert not Enrollment.objects.filter(course=course).exists()
        assert Course.objects.filter(id=course.id).exists()
        assert not User.objects.filter(id=student_user.id).exists()
