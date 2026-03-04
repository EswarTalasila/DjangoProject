"""Integration tests for FR-11 Observability (OBS)."""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from accounts.models import Role, SudoGrant, SudoPermission, UserRole
from assessments.models import GradingMode, ScoringPolicy
from core.models import AuditAction, AuditLog, AuditOutcome
from submissions.models import AnswerType, SubmissionStatus
from tests.factories import (
    AnswerFactory,
    AssessmentFactory,
    AssignmentFactory,
    CourseFactory,
    EnrollmentFactory,
    QuestionFactory,
    StudentProfileFactory,
    SubmissionFactory,
    UserFactory,
)


# ===========================================================================
# OBS-UC-01 — Configure Distributed Tracing
# ===========================================================================


class TestConfigureTracing:
    """Tests for configure_tracing() (OBS-UC-01)."""

    @staticmethod
    def _reset_configured():
        """Reset the _CONFIGURED guard before each tracing config test."""
        import importlib

        import config.otel as otel_mod  # noqa: F811

        importlib.reload(otel_mod)
        otel_mod._CONFIGURED = False

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_01(self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst):
        """Tracing configured with OTEL_ENABLED=true."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = ""
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_trace.set_tracer_provider.assert_called_once()
            mock_django_inst.return_value.instrument.assert_called_once()
            mock_psycopg_inst.return_value.instrument.assert_called_once()
            mock_logging_inst.return_value.instrument.assert_called_once()

        self._reset_configured()

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_01_disabled(
        self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst
    ):
        """Noop when OTEL_ENABLED=false."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_trace.set_tracer_provider.assert_not_called()
            mock_django_inst.return_value.instrument.assert_not_called()

        self._reset_configured()

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_01_idempotent(
        self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst
    ):
        """_CONFIGURED guard prevents double initialization (OBS-CN-01)."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = ""
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()
            configure_tracing()  # second call should be noop

            assert mock_trace.set_tracer_provider.call_count == 1

        self._reset_configured()

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.set_global_textmap")
    @patch("config.otel.trace")
    def test_OBS_CN_02(
        self,
        mock_trace,
        mock_set_textmap,
        mock_logging_inst,
        mock_django_inst,
        mock_psycopg_inst,
    ):
        """W3C propagator registered (OBS-CN-02)."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = ""
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_set_textmap.assert_called_once()
            arg = mock_set_textmap.call_args[0][0]
            from opentelemetry.propagators.textmap import W3CTraceContextTextMapPropagator

            assert isinstance(arg, W3CTraceContextTextMapPropagator)

        self._reset_configured()

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_CN_04(self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst):
        """Environment toggle respects profile defaults (OBS-CN-04)."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_trace.set_tracer_provider.assert_not_called()

        self._reset_configured()

    @patch("config.otel.FileSpanExporter")
    @patch("config.otel.OTLPSpanExporter")
    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_CN_05(
        self,
        mock_trace,
        mock_logging_inst,
        mock_django_inst,
        mock_psycopg_inst,
        mock_otlp,
        mock_file,
    ):
        """Dual export: both OTLP and file active simultaneously (OBS-CN-05)."""
        self._reset_configured()
        mock_provider = MagicMock()
        mock_trace.set_tracer_provider = MagicMock()

        with (
            patch("config.otel.env") as mock_env,
            patch("config.otel.TracerProvider", return_value=mock_provider),
        ):
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = "http://collector:4318"
            mock_env.otel_trace_file = "/tmp/traces.jsonl"
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            assert mock_provider.add_span_processor.call_count == 2

        self._reset_configured()

    @patch("config.otel.FileSpanExporter")
    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_CN_06(
        self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst, mock_file
    ):
        """File export disabled in production (OBS-CN-06)."""
        self._reset_configured()
        mock_provider = MagicMock()

        with (
            patch("config.otel.env") as mock_env,
            patch("config.otel.TracerProvider", return_value=mock_provider),
        ):
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = "/tmp/traces.jsonl"
            mock_env.is_production = True

            from config.otel import configure_tracing

            configure_tracing()

            mock_file.assert_not_called()

        self._reset_configured()

    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_03(self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst):
        """LoggingInstrumentor configured (OBS-CN-07)."""
        self._reset_configured()
        with patch("config.otel.env") as mock_env:
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = ""
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_logging_inst.return_value.instrument.assert_called_once()

        self._reset_configured()

    @patch("config.otel.OTLPSpanExporter")
    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_02(
        self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst, mock_otlp
    ):
        """OTLP exporter added when endpoint configured (OBS-UC-02)."""
        self._reset_configured()
        mock_provider = MagicMock()

        with (
            patch("config.otel.env") as mock_env,
            patch("config.otel.TracerProvider", return_value=mock_provider),
        ):
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = "http://collector:4318"
            mock_env.otel_trace_file = ""
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_otlp.assert_called_once()
            mock_provider.add_span_processor.assert_called_once()

        self._reset_configured()

    @patch("config.otel.FileSpanExporter")
    @patch("config.otel.PsycopgInstrumentor")
    @patch("config.otel.DjangoInstrumentor")
    @patch("config.otel.LoggingInstrumentor")
    @patch("config.otel.trace")
    def test_OBS_UC_04(
        self, mock_trace, mock_logging_inst, mock_django_inst, mock_psycopg_inst, mock_file
    ):
        """FileSpanExporter configured when trace file set (OBS-UC-04)."""
        self._reset_configured()
        mock_provider = MagicMock()

        with (
            patch("config.otel.env") as mock_env,
            patch("config.otel.TracerProvider", return_value=mock_provider),
        ):
            mock_env.effective_otel_enabled = True
            mock_env.otel_exporter_otlp_endpoint = ""
            mock_env.otel_trace_file = "/tmp/traces.jsonl"
            mock_env.is_production = False

            from config.otel import configure_tracing

            configure_tracing()

            mock_file.assert_called_once_with("/tmp/traces.jsonl")
            mock_provider.add_span_processor.assert_called_once()

        self._reset_configured()


# ===========================================================================
# OBS-UC-05 — Record Audit Trail for Sensitive Actions
# ===========================================================================

SUDO_GRANTS_URL = "/api/v1/sudo-grants"
SUDO_REVOKE_URL = "/api/v1/sudo-grants/{}"
USERS_URL = "/api/v1/users"
MANAGE_USER_URL = "/api/v1/users/{}"
RESET_CODE_URL = "/api/v1/auth/password-reset-codes"
SCORE_OVERRIDE_URL = "/api/v1/submissions/{}/override-score"


def _setup_teacher_with_submission(teacher_user, admin_user):
    """Create a course + student + submission for score override testing."""
    course = CourseFactory(teacher_profile=teacher_user.teacher_profile)
    sp = StudentProfileFactory(created_by=admin_user)
    EnrollmentFactory(course=course, student_profile=sp)
    assessment = AssessmentFactory(
        grading_mode=GradingMode.MANUAL,
        scoring_policy=ScoringPolicy.STANDARD,
        created_by_admin=admin_user,
    )
    question = QuestionFactory(
        assessment=assessment,
        kind="SHORT_ANSWER",
        question_type="SHORT_ANSWER",
        prompt="Question?",
        max_points=10.0,
    )
    assignment = AssignmentFactory(
        assessment=assessment,
        course=course,
        created_by=teacher_user,
    )
    submission = SubmissionFactory(
        assignment=assignment,
        student=sp.user,
        status=SubmissionStatus.SUBMITTED,
        submitted_at=timezone.now(),
    )
    from submissions.models import ShortAnswerAnswer

    answer = AnswerFactory(
        submission=submission,
        question=question,
        answer_type=AnswerType.SHORT_ANSWER,
        score=None,
    )
    ShortAnswerAnswer.objects.create(answer=answer, text="My answer")
    return submission, answer


@pytest.mark.django_db
class TestAuditSudoGrant:
    """OBS-UC-05 — SUDO_GRANT audit trail."""

    def test_OBS_UC_05_ADMIN_sudo_grant(self, api_client, admin_user, researcher_user):
        """Admin granting sudo produces SUDO_GRANT audit entry with SUCCESS."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            SUDO_GRANTS_URL,
            {
                "user_id": researcher_user.id,
                "permissions": ["CREATE_TEACHER"],
                "can_grant_sudo": False,
            },
            format="json",
        )
        assert resp.status_code == 201
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_GRANT).first()
        assert entry is not None
        assert entry.actor_id == admin_user.id
        assert entry.target_user_id == researcher_user.id
        assert entry.outcome == AuditOutcome.SUCCESS
        assert "CREATE_TEACHER" in entry.new_value["permissions"]

    def test_OBS_UC_05_sudo_grant_denied(self, api_client, researcher_user):
        """Sudo grant denied produces DENIED audit entry."""
        # Researcher without can_grant_sudo tries to grant
        api_client.force_authenticate(user=researcher_user)
        target = UserFactory()
        UserRole.objects.create(user=target, role=Role.RESEARCHER)
        resp = api_client.post(
            SUDO_GRANTS_URL,
            {"user_id": target.id, "permissions": ["CREATE_TEACHER"]},
            format="json",
        )
        assert resp.status_code in (400, 403)
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_GRANT).first()
        assert entry is not None
        assert entry.outcome in (AuditOutcome.DENIED, AuditOutcome.FAILURE)


@pytest.mark.django_db
class TestAuditSudoRevoke:
    """OBS-UC-05 — SUDO_REVOKE audit trail."""

    def test_OBS_UC_05_ADMIN_sudo_revoke(self, api_client, admin_user, researcher_user):
        """Admin revoking sudo produces SUDO_REVOKE audit entry with SUCCESS."""
        grant = SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.CREATE_TEACHER],
            can_grant_sudo=False,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(SUDO_REVOKE_URL.format(grant.id))
        assert resp.status_code == 204
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_REVOKE).first()
        assert entry is not None
        assert entry.actor_id == admin_user.id
        assert entry.target_user_id == researcher_user.id
        assert entry.outcome == AuditOutcome.SUCCESS

    def test_OBS_UC_05_sudo_revoke_denied(self, api_client, researcher_user):
        """Researcher revoking another's grant produces DENIED audit entry."""
        other_researcher = UserFactory()
        UserRole.objects.create(user=other_researcher, role=Role.RESEARCHER)
        from accounts.models import ResearcherProfile

        ResearcherProfile.objects.create(user=other_researcher)
        grant = SudoGrant.objects.create(
            user=other_researcher,
            granted_by=UserFactory(is_staff=True),
            permissions=[SudoPermission.CREATE_TEACHER],
            can_grant_sudo=False,
        )
        api_client.force_authenticate(user=researcher_user)
        resp = api_client.delete(SUDO_REVOKE_URL.format(grant.id))
        assert resp.status_code == 403
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_REVOKE).first()
        assert entry is not None
        assert entry.outcome == AuditOutcome.DENIED


@pytest.mark.django_db
class TestAuditRoleChange:
    """OBS-UC-05 — ROLE_CHANGE audit trail."""

    def test_OBS_UC_05_ADMIN_role_change(self, api_client, admin_user, teacher_user):
        """Admin changing user role produces ROLE_CHANGE audit entry."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            MANAGE_USER_URL.format(teacher_user.id),
            {"role": "RESEARCHER", "email": teacher_user.email},
            format="json",
        )
        assert resp.status_code == 200
        entry = AuditLog.objects.filter(action=AuditAction.ROLE_CHANGE).first()
        assert entry is not None
        assert entry.actor_id == admin_user.id
        assert entry.target_user_id == teacher_user.id
        assert entry.outcome == AuditOutcome.SUCCESS
        assert entry.old_value["role"] == "TEACHER"
        assert entry.new_value["role"] == "RESEARCHER"

    def test_OBS_UC_05_role_no_change_no_audit(self, api_client, admin_user, teacher_user):
        """Editing user without changing role does not create ROLE_CHANGE audit."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.patch(
            MANAGE_USER_URL.format(teacher_user.id),
            {"name": "Updated Name"},
            format="json",
        )
        assert resp.status_code == 200
        assert AuditLog.objects.filter(action=AuditAction.ROLE_CHANGE).count() == 0


@pytest.mark.django_db
class TestAuditUserDelete:
    """OBS-UC-05 — USER_DELETE audit trail."""

    def test_OBS_UC_05_ADMIN_user_delete(self, api_client, admin_user, teacher_user):
        """Admin deleting a user produces USER_DELETE audit entry."""
        target_id = teacher_user.id
        target_username = teacher_user.username
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(MANAGE_USER_URL.format(target_id))
        assert resp.status_code == 204
        entry = AuditLog.objects.filter(action=AuditAction.USER_DELETE).first()
        assert entry is not None
        assert entry.actor_id == admin_user.id
        # target_user is SET_NULL after deletion
        assert entry.target_user_id is None
        assert entry.outcome == AuditOutcome.SUCCESS
        assert entry.old_value["username"] == target_username

    def test_OBS_UC_05_user_delete_forbidden(self, api_client, teacher_user, admin_user):
        """Teacher cannot delete admin — no USER_DELETE audit entry."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.delete(MANAGE_USER_URL.format(admin_user.id))
        assert resp.status_code == 403
        assert AuditLog.objects.filter(action=AuditAction.USER_DELETE).count() == 0


@pytest.mark.django_db
class TestAuditPasswordReset:
    """OBS-UC-05 — PASSWORD_RESET audit trail."""

    def test_OBS_UC_05_ADMIN_password_reset(self, api_client, admin_user, teacher_user):
        """Admin issuing password reset produces PASSWORD_RESET audit entry."""
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(
            RESET_CODE_URL,
            {"targetUserId": teacher_user.id},
            format="json",
        )
        assert resp.status_code == 201
        entry = AuditLog.objects.filter(action=AuditAction.PASSWORD_RESET).first()
        assert entry is not None
        assert entry.actor_id == admin_user.id
        assert entry.target_user_id == teacher_user.id
        assert entry.outcome == AuditOutcome.SUCCESS

    def test_OBS_UC_05_password_reset_no_raw_password(self, api_client, admin_user, teacher_user):
        """Audit entry never stores raw passwords (OBS-CN-08)."""
        api_client.force_authenticate(user=admin_user)
        api_client.post(
            RESET_CODE_URL,
            {"targetUserId": teacher_user.id},
            format="json",
        )
        entry = AuditLog.objects.filter(action=AuditAction.PASSWORD_RESET).first()
        assert entry is not None
        assert entry.old_value == {"password": "changed"}
        assert entry.new_value == {"password": "changed"}

    def test_OBS_UC_05_password_reset_denied(self, api_client, teacher_user, admin_user):
        """Teacher cannot reset admin password — DENIED audit entry."""
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.post(
            RESET_CODE_URL,
            {"targetUserId": admin_user.id},
            format="json",
        )
        assert resp.status_code == 403
        entry = AuditLog.objects.filter(action=AuditAction.PASSWORD_RESET).first()
        assert entry is not None
        assert entry.outcome == AuditOutcome.DENIED


@pytest.mark.django_db
class TestAuditScoreOverride:
    """OBS-UC-05 — SCORE_OVERRIDE audit trail."""

    def test_OBS_UC_05_TEACHER_score_override(self, api_client, admin_user, teacher_user):
        """Teacher overriding score produces SCORE_OVERRIDE audit entry."""
        submission, answer = _setup_teacher_with_submission(teacher_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            SCORE_OVERRIDE_URL.format(submission.id),
            [8],
            format="json",
        )
        assert resp.status_code == 200
        entry = AuditLog.objects.filter(action=AuditAction.SCORE_OVERRIDE).first()
        assert entry is not None
        assert entry.actor_id == teacher_user.id
        assert entry.target_resource_type == "Submission"
        assert entry.target_resource_id == submission.id
        assert entry.outcome == AuditOutcome.SUCCESS

    def test_OBS_UC_05_score_override_failure(self, api_client, admin_user, teacher_user):
        """Score override exceeding max_points produces FAILURE audit entry."""
        submission, answer = _setup_teacher_with_submission(teacher_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        resp = api_client.patch(
            SCORE_OVERRIDE_URL.format(submission.id),
            [999],
            format="json",
        )
        assert resp.status_code in (400, 404)
        entry = AuditLog.objects.filter(action=AuditAction.SCORE_OVERRIDE).first()
        assert entry is not None
        assert entry.outcome == AuditOutcome.FAILURE


# ===========================================================================
# OBS-CN-08 — All Sensitive Actions Covered
# ===========================================================================


@pytest.mark.django_db
class TestAuditCoverage:
    """Verify all 6 sensitive action types are covered."""

    def test_OBS_CN_08_all_sensitive_actions_covered(self):
        """AuditAction enum contains all 6 required sensitive action types."""
        required = {
            "SUDO_GRANT",
            "SUDO_REVOKE",
            "ROLE_CHANGE",
            "USER_DELETE",
            "PASSWORD_RESET",
            "SCORE_OVERRIDE",
        }
        actual = {choice[0] for choice in AuditAction.choices}
        assert required == actual


# ===========================================================================
# OBS-UC-05 Resilience — Audit Logging Must Not Block Actions
# ===========================================================================


@pytest.mark.django_db
class TestAuditResilience:
    """Audit log failures must not block underlying actions."""

    def test_OBS_UC_05_audit_persists_on_action_failure(
        self, api_client, admin_user, researcher_user
    ):
        """Failed action still creates audit entry with FAILURE/DENIED outcome."""
        api_client.force_authenticate(user=admin_user)
        # Try to grant sudo to a non-researcher — should fail with ValueError
        non_researcher = UserFactory()
        UserRole.objects.create(user=non_researcher, role=Role.STUDENT)
        resp = api_client.post(
            SUDO_GRANTS_URL,
            {"user_id": non_researcher.id, "permissions": ["CREATE_TEACHER"]},
            format="json",
        )
        assert resp.status_code == 400
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_GRANT).first()
        assert entry is not None
        assert entry.outcome == AuditOutcome.FAILURE

    def test_OBS_UC_05_action_succeeds_when_audit_write_fails(
        self, api_client, admin_user, teacher_user
    ):
        """Action completes even when audit log write fails (fire-and-forget)."""
        api_client.force_authenticate(user=admin_user)
        target_id = teacher_user.id

        with patch("core.audit.AuditLog.objects.create", side_effect=Exception("DB down")):
            resp = api_client.delete(MANAGE_USER_URL.format(target_id))

        # Action should still succeed — audit failure is fire-and-forget
        assert resp.status_code == 204

    def test_OBS_UC_05_action_succeeds_when_audit_update_fails(
        self, api_client, admin_user, researcher_user
    ):
        """Action result unaffected when audit outcome update fails."""
        api_client.force_authenticate(user=admin_user)

        with patch("core.audit.AuditLog.objects.filter") as mock_filter:
            mock_filter.return_value.update.side_effect = Exception("DB down")
            resp = api_client.post(
                SUDO_GRANTS_URL,
                {
                    "user_id": researcher_user.id,
                    "permissions": ["CREATE_TEACHER"],
                },
                format="json",
            )

        assert resp.status_code == 201
        # Audit entry should exist with PENDING outcome (update failed)
        entry = AuditLog.objects.filter(action=AuditAction.SUDO_GRANT).first()
        assert entry is not None
        assert entry.outcome == AuditOutcome.PENDING


# ===========================================================================
# AuditLog Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestAuditLogModel:
    """AuditLog model CRUD and field validation."""

    def test_audit_log_creation(self, admin_user, teacher_user):
        """AuditLog entry can be created with all fields."""
        entry = AuditLog.objects.create(
            actor=admin_user,
            action=AuditAction.ROLE_CHANGE,
            target_user=teacher_user,
            old_value={"role": "TEACHER"},
            new_value={"role": "RESEARCHER"},
            outcome=AuditOutcome.SUCCESS,
            ip_address="127.0.0.1",
        )
        assert entry.id is not None
        assert entry.created_at is not None
        assert entry.actor_id == admin_user.id
        assert entry.target_user_id == teacher_user.id

    def test_audit_log_resource_fields(self, admin_user):
        """AuditLog supports target_resource_type and target_resource_id."""
        entry = AuditLog.objects.create(
            actor=admin_user,
            action=AuditAction.SCORE_OVERRIDE,
            target_resource_type="Submission",
            target_resource_id=42,
            outcome=AuditOutcome.SUCCESS,
        )
        assert entry.target_resource_type == "Submission"
        assert entry.target_resource_id == 42

    def test_audit_log_ordering(self, admin_user):
        """AuditLog entries ordered by -created_at."""
        AuditLog.objects.create(actor=admin_user, action=AuditAction.USER_DELETE)
        AuditLog.objects.create(actor=admin_user, action=AuditAction.ROLE_CHANGE)
        entries = list(AuditLog.objects.all())
        assert entries[0].created_at >= entries[1].created_at

    def test_audit_log_default_outcome(self, admin_user):
        """AuditLog default outcome is PENDING."""
        entry = AuditLog.objects.create(actor=admin_user, action=AuditAction.SUDO_GRANT)
        assert entry.outcome == AuditOutcome.PENDING

    def test_audit_log_nullable_fields(self, admin_user):
        """AuditLog nullable fields accept None."""
        entry = AuditLog.objects.create(
            actor=admin_user,
            action=AuditAction.SUDO_GRANT,
            target_user=None,
            target_resource_type=None,
            target_resource_id=None,
            old_value=None,
            new_value=None,
            ip_address=None,
        )
        assert entry.target_user is None
        assert entry.ip_address is None
