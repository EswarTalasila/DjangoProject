"""Integration tests for assignments errors."""

import pytest
from django.utils import timezone

from assignment_templates.models import AssignmentTemplate, GradingMode

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestAssignmentErrors:
    def test_create_assignment_requires_course_id_for_course_audience(
        self, api_client, teacher_user, admin_user
    ):
        """Test that create assignment requires course id for course audience."""
        assignment_template = AssignmentTemplate.objects.create(
            title="Test AssignmentTemplate",
            grading_mode=GradingMode.AUTO,
            created_by_admin=admin_user,
        )
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": assignment_template.id,
            "audienceType": "COURSE",
            "openAt": timezone.now().isoformat(),
        }
        response = api_client.post("/api/v1/assignments/", payload, format="json")
        assert response.status_code == 400
        assert b"courseId must be set" in response.content

    def test_assignment_detail_not_found_returns_404(self, api_client, teacher_user):
        """Test that assignment detail not found returns 404."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/assignments/999")
        assert response.status_code == 404
        assert b"Assignment not found" in response.content
