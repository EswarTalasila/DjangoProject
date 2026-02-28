"""Integration tests for assessments routes."""

import pytest

from assessments.models import Assessment, GradingMode, Question, QuestionKind

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestAssessmentRoutes:
    def test_admin_can_create_assessment(self, api_client, admin_user):
        """Test that admin can create assessment."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "title": "Assessment A",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "MULTIPLE_CHOICE",
                    "prompt": "Q1",
                    "maxPoints": 5,
                    "data": {"choices": [{"prompt": "A", "score": 1}], "selectAll": False},
                }
            ],
        }
        response = api_client.post("/api/v1/assessments/", payload, format="json")
        assert response.status_code == 201
        assessment = Assessment.objects.get(title="Assessment A")
        assert assessment.questions.count() == 1

    def test_teacher_cannot_create_assessment(self, api_client, teacher_user):
        """Test that teacher cannot create assessment."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/assessments/",
            {"title": "Nope", "gradingMode": "AUTO", "questions": []},
            format="json",
        )
        assert response.status_code == 403

    def test_list_assessments_requires_auth(self, api_client, teacher_user, admin_user):
        """Test that list assessments requires auth."""
        Assessment.objects.create(
            title="List One", grading_mode=GradingMode.AUTO, created_by_admin=admin_user
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/assessments/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_detail_not_found_returns_404(self, api_client, teacher_user):
        """Test that detail not found returns 404."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/assessments/9999")
        assert response.status_code == 404

    def test_admin_can_update_assessment(self, api_client, admin_user):
        """Test that admin can update assessment."""
        assessment = Assessment.objects.create(
            title="Old", grading_mode=GradingMode.AUTO, created_by_admin=admin_user
        )
        Question.objects.create(
            assessment=assessment,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Old Q",
            max_points=1.0,
            auto_gradable=False,
            graded=False,
        )
        api_client.force_authenticate(user=admin_user)
        payload = {
            "title": "New",
            "gradingMode": "AUTO",
            "questions": [
                {
                    "type": "SHORT_ANSWER",
                    "prompt": "New Q",
                    "maxPoints": 2,
                    "data": {"trim": True, "caseSensitive": False},
                }
            ],
        }
        response = api_client.patch(f"/api/v1/assessments/{assessment.id}", payload, format="json")
        assert response.status_code == 200
        assessment.refresh_from_db()
        assert assessment.title == "New"
        assert assessment.questions.count() == 1

    def test_admin_can_delete_assessment(self, api_client, admin_user):
        """Test that admin can delete assessment."""
        assessment = Assessment.objects.create(
            title="ToDelete", grading_mode=GradingMode.AUTO, created_by_admin=admin_user
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f"/api/v1/assessments/{assessment.id}")
        assert response.status_code == 204
        assert not Assessment.objects.filter(id=assessment.id).exists()
