"""FR-06 AssignmentTemplate route integration tests — v5 traceability scheme.

Test IDs follow ATMPL-UC-## convention from FR-06-Assignment-Templates.md spec.
"""

import pytest
from django.utils import timezone

from assignment_templates.models import AssignmentTemplate, GradingMode, ScoringPolicy
from assignments.models import Assignment
from courses.models import Course

pytestmark = pytest.mark.integration



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_MCQ_PAYLOAD = {
    "title": "AssignmentTemplate A",
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
    "title": "SA AssignmentTemplate",
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


def _make_assignment_template(admin_user, **overrides):
    defaults = dict(title="Test AssignmentTemplate", grading_mode=GradingMode.AUTO, created_by_admin=admin_user)
    defaults.update(overrides)
    return AssignmentTemplate.objects.create(**defaults)


def _reference_assignment_template(assignment_template, teacher_user):
    """Create an assignment that references the assignment_template, blocking mutation."""
    course = Course.objects.create(name="Ref Course", teacher_profile=teacher_user.teacher_profile)
    return Assignment.objects.create(
        assignment_template=assignment_template,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=timezone.now(),
    )


# ===========================================================================
# ATMPL-UC-01 — Create AssignmentTemplate
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_UC_01:
    """Create assignment_template (POST /api/v1/assignment-templates/)."""

    def test_ATMPL_UC_01_ADMIN(self, api_client, admin_user):
        """Admin can create an assignment_template."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post("/api/v1/assignment-templates/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "AssignmentTemplate A"
        assert data["gradingMode"] == "AUTO"
        assert data["scoringPolicy"] == "STANDARD"
        assert len(data["questions"]) == 1

    def test_ATMPL_UC_01_RESEARCHER(self, api_client, researcher_user):
        """Researcher can create an assignment_template."""
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.post("/api/v1/assignment-templates/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 201

    def test_ATMPL_UC_01_E2_TEACHER(self, api_client, teacher_user):
        """Teacher cannot create an assignment_template (403)."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {"title": "Nope", "gradingMode": "AUTO", "questions": []},
            format="json",
        )
        assert resp.status_code == 403

    def test_ATMPL_UC_01_E2_STUDENT(self, api_client, student_user):
        """Student cannot create an assignment_template (403)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.post("/api/v1/assignment-templates/", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 403

    def test_ATMPL_UC_01_E4_invalid_grading_mode(self, api_client, admin_user):
        """Unsupported grading mode is rejected with 400."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {"title": "Bad Mode", "gradingMode": "INVALID_MODE", "questions": []},
            format="json",
        )
        assert resp.status_code == 400

    def test_ATMPL_UC_01_completion_scoring_policy(self, api_client, admin_user):
        """AssignmentTemplate can be created with COMPLETION scoring policy."""
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
        resp = api_client.post("/api/v1/assignment-templates/", payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["scoringPolicy"] == "COMPLETION"
        created = AssignmentTemplate.objects.get(id=data["id"])
        assert created.scoring_policy == ScoringPolicy.COMPLETION


# ===========================================================================
# ATMPL-UC-02 — List AssignmentTemplates
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_UC_02:
    """List assignment_templates (GET /api/v1/assignment-templates/)."""

    def test_ATMPL_UC_02_ADMIN(self, api_client, admin_user):
        """Admin can list assignment_templates."""
        _make_assignment_template(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/assignment-templates/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_ATMPL_UC_02_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can list assignment_templates."""
        _make_assignment_template(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get("/api/v1/assignment-templates/")
        assert resp.status_code == 200

    def test_ATMPL_UC_02_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can list assignment_templates (read-only)."""
        _make_assignment_template(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/assignment-templates/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_ATMPL_CN_02_student_cannot_list(self, api_client, student_user):
        """Student cannot list assignment_templates (403 — ATMPL-CN-02)."""
        api_client.force_authenticate(user=student_user)
        resp = api_client.get("/api/v1/assignment-templates/")
        assert resp.status_code == 403


# ===========================================================================
# ATMPL-UC-03 — Get AssignmentTemplate Detail
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_UC_03:
    """Get assignment_template detail (GET /api/v1/assignment-templates/{id})."""

    def test_ATMPL_UC_03_ADMIN(self, api_client, admin_user):
        """Admin can view assignment_template detail."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == a.id

    def test_ATMPL_UC_03_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can view assignment_template detail."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 200

    def test_ATMPL_UC_03_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher can view assignment_template detail (read-only)."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 200

    def test_ATMPL_CN_02_teacher_cannot_view_draft_detail(self, api_client, admin_user, teacher_user):
        """Teacher cannot fetch draft assignment_template detail by direct ID."""
        a = _make_assignment_template(
            admin_user,
            status="DRAFT",
            title="Draft Only",
        )
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 404

    def test_ATMPL_CN_02_student_cannot_view(self, api_client, admin_user, student_user):
        """Student cannot view assignment_template detail (403 — ATMPL-CN-02)."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 403

    def test_ATMPL_UC_03_E1_not_found(self, api_client, teacher_user):
        """Non-existent assignment_template returns 404."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.get("/api/v1/assignment-templates/99999")
        assert resp.status_code == 404


# ===========================================================================
# ATMPL-UC-04 — Update AssignmentTemplate
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_UC_04:
    """Update assignment_template (PATCH /api/v1/assignment-templates/{id})."""

    def test_ATMPL_UC_04_ADMIN(self, api_client, admin_user):
        """Admin can update an unreferenced assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 200
        a.refresh_from_db()
        assert a.title == "SA AssignmentTemplate"

    def test_ATMPL_UC_04_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can update an unreferenced assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 200

    def test_ATMPL_UC_04_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot update assignment_template (403)."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 403

    def test_ATMPL_UC_04_E3_referenced(self, api_client, admin_user, teacher_user):
        """Update blocked when assignments reference assignment_template (409 — ATMPL-CN-06)."""
        a = _make_assignment_template(admin_user)
        _reference_assignment_template(a, teacher_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{a.id}", VALID_SHORT_ANSWER_PAYLOAD, format="json"
        )
        assert resp.status_code == 409
        assert "used" in resp.json()["detail"].lower()

    def test_ATMPL_CN_06_previously_used_template_cannot_be_updated(
        self, api_client, admin_user, teacher_user
    ):
        """Previously used assignment templates stay immutable after downstream assignments are removed."""
        assignment_template = _make_assignment_template(admin_user, title="Historical")
        assignment_template.used_at = timezone.now()
        assignment_template.save(update_fields=["used_at"])
        _reference_assignment_template(assignment_template, teacher_user).delete()

        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{assignment_template.id}",
            VALID_SHORT_ANSWER_PAYLOAD,
            format="json",
        )

        assert resp.status_code == 409
        assert "used" in resp.json()["detail"].lower()


# ===========================================================================
# ATMPL-UC-05 — Delete AssignmentTemplate
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_UC_05:
    """Delete assignment_template (DELETE /api/v1/assignment-templates/{id})."""

    def test_ATMPL_UC_05_ADMIN(self, api_client, admin_user):
        """Admin can plain-delete an unused assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 204
        assert not AssignmentTemplate.objects.filter(id=a.id).exists()

    def test_ATMPL_UC_05_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher can plain-delete an unused assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 204
        assert not AssignmentTemplate.objects.filter(id=a.id).exists()

    def test_ATMPL_UC_05_E2_TEACHER(self, api_client, admin_user, teacher_user):
        """Teacher cannot delete assignment_template (403)."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 403

    def test_ATMPL_UC_05_E3_used(self, api_client, admin_user, teacher_user):
        """Used assignment_template still returns conflict on plain DELETE."""
        a = _make_assignment_template(admin_user)
        _reference_assignment_template(a, teacher_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 409
        assert AssignmentTemplate.objects.filter(id=a.id).exists()

    def test_ATMPL_CN_05_used_delete_requires_archive(self, api_client, admin_user, teacher_user):
        """Previously used assignment_template requires archive/purge instead of plain delete."""
        a_referenced = _make_assignment_template(admin_user, title="Referenced")
        a_referenced.used_at = timezone.now()
        a_referenced.save(update_fields=["used_at"])
        _reference_assignment_template(a_referenced, teacher_user).delete()
        a_free = _make_assignment_template(admin_user, title="Free")
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a_referenced.id}")
        assert resp.status_code == 409
        assert AssignmentTemplate.objects.filter(id=a_referenced.id).exists()
        assert AssignmentTemplate.objects.filter(id=a_free.id).exists()


# ===========================================================================
# ATMPL-CN-02 — No Student Access (additional)
# ===========================================================================
@pytest.mark.django_db
class TestATMPL_CN_02:
    """No student access to any ATMPL endpoint (ATMPL-CN-02)."""

    def test_student_cannot_update(self, api_client, admin_user, student_user):
        """Student cannot update assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.patch(f"/api/v1/assignment-templates/{a.id}", VALID_MCQ_PAYLOAD, format="json")
        assert resp.status_code == 403

    def test_student_cannot_delete(self, api_client, admin_user, student_user):
        """Student cannot delete assignment_template."""
        a = _make_assignment_template(admin_user)
        api_client.force_authenticate(user=student_user)
        resp = api_client.delete(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, api_client, admin_user):
        """Unauthenticated request is denied."""
        a = _make_assignment_template(admin_user)
        resp = api_client.get(f"/api/v1/assignment-templates/{a.id}")
        assert resp.status_code in (401, 403)
