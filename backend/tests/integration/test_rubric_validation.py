"""FR-06 Rubric validation matrix tests.

Tests rubric linkage rules, archived rubric attachment, grading-mode constraints,
and ValueError→400 regression.
"""

import pytest

from assignment_templates.models import AssignmentTemplate, GradingMode
from rubrics.models import Rubric, RubricCriterion, RubricLevel, RubricStatus


def _make_rubric(user, **overrides):
    defaults = dict(title="Test Rubric", created_by=user)
    defaults.update(overrides)
    return Rubric.objects.create(**defaults)


def _make_assessment(user, **overrides):
    defaults = dict(title="Test AssignmentTemplate", grading_mode=GradingMode.AUTO, created_by_admin=user)
    defaults.update(overrides)
    return AssignmentTemplate.objects.create(**defaults)


# ===========================================================================
# Legacy field rejection
# ===========================================================================
@pytest.mark.django_db
class TestLegacyFieldRejection:
    """Current and legacy rubric payload behavior."""

    def test_create_with_assessment_rubric_succeeds(self, api_client, admin_user):
        """Top-level rubricId now binds a default rubric to the assignment_template."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "MANUAL",
                "rubricId": r.id,
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["rubricId"] == r.id

    def test_create_with_rubricAssignmentTemplateIds_returns_400(self, api_client, admin_user):
        """Sending legacy rubricAssignmentTemplateIds on create returns 400."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "AUTO",
                "questions": [],
                "rubricAssignmentTemplateIds": [1, 2],
            },
            format="json",
        )
        assert resp.status_code == 400


# ===========================================================================
# Unsupported grading mode behavior
# ===========================================================================
@pytest.mark.django_db
class TestInvalidGradingMode:
    """Removed grading modes are rejected."""

    def test_rubric_mode_returns_400(self, api_client, admin_user):
        """Creating with gradingMode=RUBRIC is rejected."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Rubric Test",
                "gradingMode": "RUBRIC",
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400


# ===========================================================================
# Archived rubric attachment
# ===========================================================================
@pytest.mark.django_db
class TestArchivedRubricAttachment:
    """Archived rubrics cannot be newly attached (400)."""

    def test_archived_rubric_on_question_returns_400(self, api_client, admin_user):
        """Attaching archived rubric to a question returns 400."""
        r = _make_rubric(admin_user, status=RubricStatus.ARCHIVED)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "MANUAL",
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Q",
                        "maxPoints": 10,
                        "rubricId": r.id,
                        "gradingStrategy": "MANUAL",
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "archived" in resp.json()["detail"].lower()

    def test_archived_rubric_on_group_returns_400(self, api_client, admin_user):
        """Attaching archived rubric to a question group returns 400."""
        r = _make_rubric(admin_user, status=RubricStatus.ARCHIVED)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "MANUAL",
                "questionGroups": [
                    {"clientKey": "g1", "name": "Group 1", "rubricId": r.id}
                ],
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Q",
                        "maxPoints": 10,
                        "groupClientKey": "g1",
                        "gradingStrategy": "MANUAL",
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "archived" in resp.json()["detail"].lower()

    def test_archived_rubric_on_assessment_returns_400(self, api_client, admin_user):
        """Attaching archived rubric to the assignment_template returns 400."""
        r = _make_rubric(admin_user, status=RubricStatus.ARCHIVED)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "MANUAL",
                "rubricId": r.id,
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Q",
                        "maxPoints": 10,
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "archived" in resp.json()["detail"].lower()


# ===========================================================================
# Rubric immutability when referenced
# ===========================================================================
@pytest.mark.django_db
class TestRubricImmutability:
    """Referenced rubrics cannot be updated or deleted (409)."""

    def test_update_referenced_rubric_returns_409(self, api_client, admin_user):
        """PATCH on referenced rubric returns 409."""
        from assignment_templates.models import Question, QuestionKind

        r = _make_rubric(admin_user)
        a = _make_assessment(admin_user, grading_mode=GradingMode.MANUAL)
        Question.objects.create(
            assignment_template=a,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q",
            max_points=10,
            rubric=r,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/rubrics/{r.id}", {"title": "New"}, format="json"
        )
        assert resp.status_code == 409

    def test_delete_referenced_rubric_returns_409(self, api_client, admin_user):
        """DELETE on referenced rubric returns 409."""
        from assignment_templates.models import Question, QuestionKind

        r = _make_rubric(admin_user)
        a = _make_assessment(admin_user, grading_mode=GradingMode.MANUAL)
        Question.objects.create(
            assignment_template=a,
            question_type=QuestionKind.SHORT_ANSWER,
            kind=QuestionKind.SHORT_ANSWER,
            prompt="Q",
            max_points=10,
            rubric=r,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(f"/api/v1/rubrics/{r.id}")
        assert resp.status_code == 409


# ===========================================================================
# ValueError → 400 regression (never 409)
# ===========================================================================
@pytest.mark.django_db
class TestValueErrorRegression:
    """ValueError always maps to 400, never 409."""

    def test_update_with_bad_payload_returns_400_not_409(self, api_client, admin_user):
        """ValueError from service layer maps to 400, not 409."""
        a = _make_assessment(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            f"/api/v1/assignment-templates/{a.id}",
            {
                "title": "Updated",
                "gradingMode": "AUTO",
                "questions": [
                    {
                        "type": "NUMBER_SCALE",
                        "prompt": "Rate",
                        "maxPoints": 5,
                        "data": {},  # missing min/max → ValueError
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400


# ===========================================================================
# HYBRID grading strategy validation
# ===========================================================================
@pytest.mark.django_db
class TestHybridValidation:
    """HYBRID mode requires per-question grading strategy + rubric rules."""

    def test_hybrid_manual_without_rubric_returns_400(self, api_client, admin_user):
        """HYBRID with MANUAL question but no rubric returns 400."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Hybrid Test",
                "gradingMode": "HYBRID",
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "gradingStrategy": "MANUAL",
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "rubric" in resp.json()["detail"].lower()

    def test_hybrid_auto_with_rubric_returns_400(self, api_client, admin_user):
        """HYBRID with AUTO question but with rubric returns 400."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Hybrid Test",
                "gradingMode": "HYBRID",
                "questions": [
                    {
                        "type": "MULTIPLE_CHOICE",
                        "prompt": "Pick",
                        "maxPoints": 5,
                        "gradingStrategy": "AUTO",
                        "rubricId": r.id,
                        "data": {
                            "choices": [{"prompt": "A", "score": 1}],
                            "selectAll": False,
                        },
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "rubric" in resp.json()["detail"].lower()

    def test_hybrid_valid_mixed_succeeds(self, api_client, admin_user):
        """HYBRID with valid AUTO + MANUAL (with rubric) succeeds."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Hybrid Test",
                "gradingMode": "HYBRID",
                "questions": [
                    {
                        "type": "MULTIPLE_CHOICE",
                        "prompt": "Pick",
                        "maxPoints": 5,
                        "gradingStrategy": "AUTO",
                        "data": {
                            "choices": [{"prompt": "A", "score": 1}],
                            "selectAll": False,
                        },
                    },
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "gradingStrategy": "MANUAL",
                        "rubricId": r.id,
                        "data": {"trim": True, "caseSensitive": False},
                    },
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["questions"][0]["gradingStrategy"] == "AUTO"
        assert data["questions"][1]["gradingStrategy"] == "MANUAL"
        assert data["questions"][1]["rubricId"] == r.id


# ===========================================================================
# Question group with rubric
# ===========================================================================
@pytest.mark.django_db
class TestQuestionGroups:
    """Question groups with rubric assignment."""

    def test_create_with_question_groups(self, api_client, admin_user):
        """AssignmentTemplate can be created with question groups."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Grouped AssignmentTemplate",
                "gradingMode": "HYBRID",
                "questionGroups": [
                    {"clientKey": "g1", "name": "Writing", "rubricId": r.id},
                ],
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Write an essay",
                        "maxPoints": 20,
                        "groupClientKey": "g1",
                        "gradingStrategy": "MANUAL",
                        "data": {"trim": True, "caseSensitive": False},
                    },
                    {
                        "type": "MULTIPLE_CHOICE",
                        "prompt": "Pick one",
                        "maxPoints": 5,
                        "gradingStrategy": "AUTO",
                        "data": {
                            "choices": [{"prompt": "A", "score": 1}],
                            "selectAll": False,
                        },
                    },
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["questionGroups"]) == 1
        assert data["questionGroups"][0]["name"] == "Writing"
        assert data["questionGroups"][0]["rubricId"] == r.id
        # First question should be in group
        assert data["questions"][0]["groupId"] == data["questionGroups"][0]["id"]
        # Second question should not be in a group
        assert data["questions"][1]["groupId"] is None

    def test_manual_with_assessment_rubric_succeeds(self, api_client, admin_user):
        """AssignmentTemplate-level rubric satisfies MANUAL rubric requirements."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Manual AssignmentTemplate Rubric",
                "gradingMode": "MANUAL",
                "rubricId": r.id,
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rubricId"] == r.id
        assert data["questions"][0]["rubricId"] is None

    def test_hybrid_manual_question_inherits_assessment_rubric(
        self, api_client, admin_user
    ):
        """HYBRID MANUAL questions can inherit the assignment_template-level rubric."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Hybrid AssignmentTemplate Rubric",
                "gradingMode": "HYBRID",
                "rubricId": r.id,
                "questions": [
                    {
                        "type": "SHORT_ANSWER",
                        "prompt": "Explain",
                        "maxPoints": 10,
                        "gradingStrategy": "MANUAL",
                        "data": {"trim": True, "caseSensitive": False},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["rubricId"] == r.id


# ===========================================================================
# AUTO mode rubric linkage rejection
# ===========================================================================
@pytest.mark.django_db
class TestAutoModeRubricRejection:
    """AUTO mode does not allow rubric linkage."""

    def test_auto_with_rubric_on_question_returns_400(self, api_client, admin_user):
        """AUTO mode with rubric on question returns 400."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "Test",
                "gradingMode": "AUTO",
                "questions": [
                    {
                        "type": "MULTIPLE_CHOICE",
                        "prompt": "Pick",
                        "maxPoints": 5,
                        "rubricId": r.id,
                        "data": {
                            "choices": [{"prompt": "A", "score": 1}],
                            "selectAll": False,
                        },
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "auto" in resp.json()["detail"].lower()

    def test_auto_with_assessment_rubric_returns_400(self, api_client, admin_user):
        """AUTO mode with an assignment_template-level rubric returns 400."""
        r = _make_rubric(admin_user)
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            "/api/v1/assignment-templates/",
            {
                "title": "AssignmentTemplate Rubric in Auto",
                "gradingMode": "AUTO",
                "rubricId": r.id,
                "questions": [
                    {
                        "type": "MULTIPLE_CHOICE",
                        "prompt": "Pick",
                        "maxPoints": 5,
                        "data": {
                            "choices": [{"prompt": "A", "score": 1}],
                            "selectAll": False,
                        },
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "auto" in resp.json()["detail"].lower()
