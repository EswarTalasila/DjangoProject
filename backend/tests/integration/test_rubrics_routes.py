"""FR-06 Rubric route integration tests — v5 traceability scheme.

Test IDs follow RBR-UC-## convention from FR-06 section 12.
"""

import pytest

from rubrics.models import Rubric, RubricStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_RUBRIC_PAYLOAD = {
    "title": "Writing Rubric",
    "description": "Evaluates writing quality",
    "criteria": [
        {
            "title": "Grammar",
            "description": "Correct grammar usage",
            "orderIndex": 0,
            "weight": 1.0,
            "levels": [
                {"label": "Excellent", "points": 4, "description": "No errors", "orderIndex": 0},
                {"label": "Good", "points": 3, "description": "Minor errors", "orderIndex": 1},
                {"label": "Fair", "points": 2, "description": "Some errors", "orderIndex": 2},
                {"label": "Poor", "points": 1, "description": "Many errors", "orderIndex": 3},
            ],
        },
        {
            "title": "Content",
            "description": "Depth of content",
            "orderIndex": 1,
            "weight": 2.0,
            "levels": [
                {"label": "Excellent", "points": 4, "orderIndex": 0},
                {"label": "Good", "points": 3, "orderIndex": 1},
            ],
        },
    ],
}

MINIMAL_RUBRIC_PAYLOAD = {
    "title": "Simple Rubric",
}


def _make_rubric(admin_user, **overrides):
    defaults = dict(title="Test Rubric", created_by=admin_user)
    defaults.update(overrides)
    return Rubric.objects.create(**defaults)


# ===========================================================================
# RBR-UC-01 — Create Rubric
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_01:
    """Create rubric (POST /api/v1/rubrics/)."""

    def test_RBR_UC_01_ADMIN(self, api_client, admin_user):
        """Admin can create a rubric with criteria and levels."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post("/api/v1/rubrics/", VALID_RUBRIC_PAYLOAD, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Writing Rubric"
        assert data["status"] == "ACTIVE"
        assert len(data["criteria"]) == 2
        assert len(data["criteria"][0]["levels"]) == 4
        assert data["criteria"][1]["weight"] == 2.0

    def test_RBR_UC_01_RESEARCHER(self, api_client, researcher_user):
        """Researcher can create a rubric."""
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.post("/api/v1/rubrics/", MINIMAL_RUBRIC_PAYLOAD, format="json")
        assert resp.status_code == 201

    def test_RBR_UC_01_E2_TEACHER(self, api_client, teacher_user):
        """Teacher cannot create a rubric (403)."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post("/api/v1/rubrics/", MINIMAL_RUBRIC_PAYLOAD, format="json")
        assert resp.status_code == 403

    def test_RBR_UC_01_E2_STUDENT(self, api_client, student_user):
        """Student cannot create a rubric (403)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.post("/api/v1/rubrics/", MINIMAL_RUBRIC_PAYLOAD, format="json")
        assert resp.status_code == 403


# ===========================================================================
# RBR-UC-02 — List Rubrics
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_02:
    """List rubrics (GET /api/v1/rubrics/)."""

    def test_RBR_UC_02_ADMIN(self, api_client, admin_user):
        """Admin can list rubrics."""
        _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/rubrics/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_RBR_UC_02_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can list rubrics (read-only)."""
        _make_rubric(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/rubrics/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_RBR_UC_02_student_denied(self, api_client, student_user):
        """Student cannot list rubrics (403)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get("/api/v1/rubrics/")
        assert resp.status_code == 403


# ===========================================================================
# RBR-UC-03 — Get Rubric Detail
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_03:
    """Get rubric detail (GET /api/v1/rubrics/{id})."""

    def test_RBR_UC_03_ADMIN(self, api_client, admin_user):
        """Admin can view rubric detail."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == r.id

    def test_RBR_UC_03_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can view rubric detail (read-only)."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 200

    def test_RBR_UC_03_E1_not_found(self, api_client, teacher_user):
        """Non-existent rubric returns 404."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/rubrics/99999")
        assert resp.status_code == 404


# ===========================================================================
# RBR-UC-04 — Update Rubric
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_04:
    """Update rubric (PATCH /api/v1/rubrics/{id})."""

    def test_RBR_UC_04_ADMIN(self, api_client, admin_user):
        """Admin can update an unreferenced rubric."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/rubrics/{r.id}",
            {"title": "Updated Rubric", "criteria": []},
            format="json",
        )
        assert resp.status_code == 200
        r.refresh_from_db()
        assert r.title == "Updated Rubric"

    def test_RBR_UC_04_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot update rubric (403)."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/rubrics/{r.id}", {"title": "Nope"}, format="json"
        )
        assert resp.status_code == 403

    def test_RBR_UC_04_E3_referenced(self, api_client, admin_user):
        """Update blocked when questions reference rubric (409)."""
        from assessments.models import Assessment, GradingMode, Question, QuestionKind

        r = _make_rubric(admin_user)
        a = Assessment.objects.create(
            title="A", grading_mode=GradingMode.MANUAL, created_by_admin=admin_user
        )
        Question.objects.create(
            assessment=a,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q",
            max_points=10,
            rubric=r,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/rubrics/{r.id}", {"title": "Nope"}, format="json"
        )
        assert resp.status_code == 409
        assert "referenced" in resp.json()["detail"].lower()


# ===========================================================================
# RBR-UC-05 — Delete Rubric
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_05:
    """Delete rubric (DELETE /api/v1/rubrics/{id})."""

    def test_RBR_UC_05_ADMIN(self, api_client, admin_user):
        """Admin can delete an unreferenced rubric."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 204
        assert not Rubric.objects.filter(id=r.id).exists()

    def test_RBR_UC_05_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot delete rubric (403)."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 403

    def test_RBR_UC_05_E3_referenced(self, api_client, admin_user):
        """Delete blocked when questions reference rubric (409)."""
        from assessments.models import Assessment, GradingMode, Question, QuestionKind

        r = _make_rubric(admin_user)
        a = Assessment.objects.create(
            title="A", grading_mode=GradingMode.MANUAL, created_by_admin=admin_user
        )
        Question.objects.create(
            assessment=a,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q",
            max_points=10,
            rubric=r,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 409
        assert Rubric.objects.filter(id=r.id).exists()


# ===========================================================================
# RBR-UC-06 — Archive Rubric
# ===========================================================================
@pytest.mark.django_db
class TestRBR_UC_06:
    """Archive rubric (POST /api/v1/rubrics/{id}/archive)."""

    def test_RBR_UC_06_ADMIN(self, api_client, admin_user):
        """Admin can archive a rubric."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f"/api/v1/rubrics/{r.id}/archive")
        assert resp.status_code == 200
        r.refresh_from_db()
        assert r.status == RubricStatus.ARCHIVED

    def test_RBR_UC_06_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot archive rubric (403)."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(f"/api/v1/rubrics/{r.id}/archive")
        assert resp.status_code == 403

    def test_RBR_UC_06_E3_already_archived(self, api_client, admin_user):
        """Archiving already-archived rubric returns 409."""
        r = _make_rubric(admin_user, status=RubricStatus.ARCHIVED)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f"/api/v1/rubrics/{r.id}/archive")
        assert resp.status_code == 409
