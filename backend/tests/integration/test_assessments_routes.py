"""FR-06 Assessment route integration tests — v5 traceability scheme.

Test IDs follow ASMT-UC-## convention from FR-06-Assessments.md spec.
"""

import pytest
from django.utils import timezone

from assessments.models import Assessment, GradingMode, ScoringPolicy
from assignments.models import Assignment
from courses.models import Course

pytestmark = pytest.mark.integration



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_MCQ_PAYLOAD = {
    "title": "Assessment A",
    "gradingMode": "AUTO",
    "questions": [
        {
            "type": "MULTIPLE_CHOICE",
            "prompt": "Pick one",
            "maxPoints": 5,
            "data": {"choices": [{"prompt": "A", "score": 1}], "selectAll": False},
        }
    ],
}

VALID_SHORT_ANSWER_PAYLOAD = {
    "title": "SA Assessment",
    "gradingMode": "HYBRID",
    "questions": [
        {
            "type": "SHORT_ANSWER",
            "prompt": "Explain",
            "maxPoints": 10,
            "data": {"trim": True, "caseSensitive": False},
            "gradingStrategy": "AUTO",
        }
    ],
}


def _make_assessment(admin_user, **overrides):
    defaults = dict(title="Test Assessment", grading_mode=GradingMode.AUTO, created_by_admin=admin_user)
    defaults.update(overrides)
    return Assessment.objects.create(**defaults)


def _reference_assessment(assessment, teacher_user):
    """Create an assignment that references the assessment, blocking mutation."""
    course = Course.objects.create(name="Ref Course", teacher_profile=teacher_user.teacher_profile)
    return Assignment.objects.create(
        assessment=assessment,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=timezone.now(),
    )


# ===========================================================================
# ASMT-UC-01 — Create Assessment
# ===========================================================================
@pytest.mark.django_db
class TestASMT_UC_01:
    """Create assessment (POST /api/v1/assessments/)."""

    def test_ASMT_UC_01_ADMIN(self, api_client, admin_user):
        """Admin can create an assessment."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post("/api/v1/assessments/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Assessment A"
        assert data["gradingMode"] == "AUTO"
        assert data["scoringPolicy"] == "STANDARD"
        assert len(data["questions"]) == 1

    def test_ASMT_UC_01_RESEARCHER(self, api_client, researcher_user):
        """Researcher can create an assessment."""
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.post("/api/v1/assessments/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 201

    def test_ASMT_UC_01_E2_TEACHER(self, api_client, teacher_user):
        """Teacher cannot create an assessment (403)."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(
            "/api/v1/assessments/",
            {"title": "Nope", "gradingMode": "AUTO", "questions": []},
            format="json",
        )
        assert resp.status_code == 403

    def test_ASMT_UC_01_E2_STUDENT(self, api_client, student_user):
        """Student cannot create an assessment (403)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.post("/api/v1/assessments/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 403

    def test_ASMT_UC_01_E4_invalid_grading_mode(self, api_client, admin_user):
        """Unsupported grading mode is rejected with 400."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assessments/",
            {"title": "Bad Mode", "gradingMode": "INVALID_MODE", "questions": []},
            format="json",
        )
        assert resp.status_code == 400

    def test_ASMT_UC_01_completion_scoring_policy(self, api_client, admin_user):
        """Assessment can be created with COMPLETION scoring policy."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "title": "Participation Check",
            "gradingMode": "HYBRID",
            "scoringPolicy": "COMPLETION",
            "questions": [
                {
                    "type": "SHORT_ANSWER",
                    "prompt": "Any reflection",
                    "maxPoints": 1,
                    "data": {"trim": True, "caseSensitive": False},
                    "gradingStrategy": "AUTO",
                }
            ],
        }
        resp = api_client.post("/api/v1/assessments/", payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["scoringPolicy"] == "COMPLETION"
        created = Assessment.objects.get(id=data["id"])
        assert created.scoring_policy == ScoringPolicy.COMPLETION


# ===========================================================================
# ASMT-UC-02 — List Assessments
# ===========================================================================
@pytest.mark.django_db
class TestASMT_UC_02:
    """List assessments (GET /api/v1/assessments/)."""

    def test_ASMT_UC_02_ADMIN(self, api_client, admin_user):
        """Admin can list assessments."""
        _make_assessment(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/assessments/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_ASMT_UC_02_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can list assessments."""
        _make_assessment(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get("/api/v1/assessments/")
        assert resp.status_code == 200

    def test_ASMT_UC_02_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can list assessments (read-only)."""
        _make_assessment(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/assessments/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_ASMT_CN_02_student_cannot_list(self, api_client, student_user):
        """Student cannot list assessments (403 — ASMT-CN-02)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get("/api/v1/assessments/")
        assert resp.status_code == 403


# ===========================================================================
# ASMT-UC-03 — Get Assessment Detail
# ===========================================================================
@pytest.mark.django_db
class TestASMT_UC_03:
    """Get assessment detail (GET /api/v1/assessments/{id})."""

    def test_ASMT_UC_03_ADMIN(self, api_client, admin_user):
        """Admin can view assessment detail."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == a.id

    def test_ASMT_UC_03_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can view assessment detail."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 200

    def test_ASMT_UC_03_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can view assessment detail (read-only)."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 200

    def test_ASMT_CN_02_student_cannot_view(self, api_client, admin_user, student_user):
        """Student cannot view assessment detail (403 — ASMT-CN-02)."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 403

    def test_ASMT_UC_03_E1_not_found(self, api_client, teacher_user):
        """Non-existent assessment returns 404."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/assessments/99999")
        assert resp.status_code == 404


# ===========================================================================
# ASMT-UC-04 — Update Assessment
# ===========================================================================
@pytest.mark.django_db
class TestASMT_UC_04:
    """Update assessment (PATCH /api/v1/assessments/{id})."""

    def test_ASMT_UC_04_ADMIN(self, api_client, admin_user):
        """Admin can update an unreferenced assessment."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assessments/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 200
        a.refresh_from_db()
        assert a.title == "SA Assessment"

    def test_ASMT_UC_04_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can update an unreferenced assessment."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.patch(
            f"/api/v1/assessments/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 200

    def test_ASMT_UC_04_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot update assessment (403)."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assessments/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 403

    def test_ASMT_UC_04_E3_referenced(self, api_client, admin_user, teacher_user):
        """Update blocked when assignments reference assessment (409 — ASMT-CN-06)."""
        a = _make_assessment(admin_user)
        _reference_assessment(a, teacher_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assessments/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 409
        assert "referenced" in resp.json()["detail"].lower()


# ===========================================================================
# ASMT-UC-05 — Delete Assessment
# ===========================================================================
@pytest.mark.django_db
class TestASMT_UC_05:
    """Delete assessment (DELETE /api/v1/assessments/{id})."""

    def test_ASMT_UC_05_ADMIN(self, api_client, admin_user):
        """Plain DELETE is blocked; caller must archive/purge."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 409
        assert "archive" in resp.json()["detail"].lower()
        assert Assessment.objects.filter(id=a.id).exists()

    def test_ASMT_UC_05_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher plain DELETE is also blocked by lifecycle policy."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.delete(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 409

    def test_ASMT_UC_05_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot delete assessment (403)."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 403

    def test_ASMT_UC_05_E3_referenced(self, api_client, admin_user, teacher_user):
        """Referenced assessment still returns conflict on plain DELETE."""
        a = _make_assessment(admin_user)
        _reference_assessment(a, teacher_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 409
        assert Assessment.objects.filter(id=a.id).exists()

    def test_ASMT_CN_05_unreferenced_delete_requires_archive(self, api_client, admin_user, teacher_user):
        """Unreferenced assessment requires archive/purge (no plain hard delete)."""
        a_referenced = _make_assessment(admin_user, title="Referenced")
        a_free = _make_assessment(admin_user, title="Free")
        _reference_assessment(a_referenced, teacher_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assessments/{a_free.id}")
        assert resp.status_code == 409
        assert Assessment.objects.filter(id=a_referenced.id).exists()
        assert Assessment.objects.filter(id=a_free.id).exists()


# ===========================================================================
# ASMT-CN-02 — No Student Access (additional)
# ===========================================================================
@pytest.mark.django_db
class TestASMT_CN_02:
    """No student access to any ASMT endpoint (ASMT-CN-02)."""

    def test_student_cannot_update(self, api_client, admin_user, student_user):
        """Student cannot update assessment."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.patch(f"/api/v1/assessments/{a.id}", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 403

    def test_student_cannot_delete(self, api_client, admin_user, student_user):
        """Student cannot delete assessment."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.delete(f"/api/v1/assessments/{a.id}")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, api_client, admin_user):
        """Unauthenticated request is denied."""
        a = _make_assessment(admin_user)
        resp = api_client.get(f"/api/v1/assessments/{a.id}")
        assert resp.status_code in (401, 403)
