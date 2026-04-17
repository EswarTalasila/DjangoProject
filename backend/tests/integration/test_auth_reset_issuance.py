"""Integration coverage for issuer-driven password reset code issuance."""

from __future__ import annotations

import pytest

from accounts.models import (
    ResearcherProfile,
    Role,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    UserRole,
)
from courses.models import Course, Enrollment, EnrollmentStatus
from tests.factories import UserFactory

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestAuthResetIssuance:
    """AUTH-UC-07 issuer-driven reset issuance behavior."""

    @staticmethod
    def _enroll_student(*, teacher_user, student_user):
        course = Course.objects.create(
            name="Reset Chain Course", teacher_profile=teacher_user.teacher_profile
        )
        Enrollment.objects.create(
            course=course,
            student_profile=student_user.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )
        return course

    @staticmethod
    def _grant_permissions(*, admin_user, researcher_user, permissions: list[str]):
        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            can_grant_sudo=False,
            permissions=permissions,
        )

    def test_teacher_can_issue_for_enrolled_student(self, api_client, teacher_user, student_user):
        """Teacher can issue student reset code when enrollment ownership is valid."""
        self._enroll_student(teacher_user=teacher_user, student_user=student_user)
        api_client.force_authenticate(user=teacher_user)

        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["targetUserId"] == student_user.id
        assert response.json()["targetRole"] == Role.STUDENT
        assert response.json()["resetCode"].startswith("RESET-")

    def test_teacher_denied_for_non_enrolled_student(self, api_client, teacher_user, student_user):
        """Teacher issuance is denied when target student is outside teacher scope."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )

        assert response.status_code == 403
        assert "enrolled" in response.json()["detail"].lower()

    def test_researcher_chain_and_sudo_extensions(
        self, api_client, admin_user, researcher_user, teacher_user, student_user
    ):
        """Researcher default target is teacher; student/researcher targets require sudo flags."""
        api_client.force_authenticate(user=researcher_user)

        default_teacher = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": teacher_user.id},
            format="json",
        )
        assert default_teacher.status_code == 201
        assert default_teacher.json()["targetRole"] == Role.TEACHER

        denied_student = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert denied_student.status_code == 403

        denied_researcher = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": researcher_user.id},
            format="json",
        )
        assert denied_researcher.status_code == 403

        self._grant_permissions(
            admin_user=admin_user,
            researcher_user=researcher_user,
            permissions=[
                SudoPermission.ISSUE_STUDENT_RESET_CODE.value,
                SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value,
            ],
        )

        allowed_student = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert allowed_student.status_code == 201
        assert allowed_student.json()["targetRole"] == Role.STUDENT

        researcher_target = UserFactory()
        UserRole.objects.create(user=researcher_target, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=researcher_target)

        allowed_researcher = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": researcher_target.id},
            format="json",
        )
        assert allowed_researcher.status_code == 201
        assert allowed_researcher.json()["targetRole"] == Role.RESEARCHER

    def test_new_issuance_invalidates_prior_code(self, api_client, teacher_user, student_user):
        """New issuance expires prior active code for the same target user."""
        self._enroll_student(teacher_user=teacher_user, student_user=student_user)
        api_client.force_authenticate(user=teacher_user)

        first = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        second = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert first.status_code == 201
        assert second.status_code == 201

        first_verify = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": student_user.username, "resetCode": first.json()["resetCode"]},
            format="json",
        )
        second_verify = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": student_user.username, "resetCode": second.json()["resetCode"]},
            format="json",
        )

        assert first_verify.status_code == 400
        assert second_verify.status_code == 200

    # Traceability aliases required by FR-01 AUTH-UC-07
    def test_AUTH_UC_07_TEACHER_DEFAULT(self, api_client, teacher_user, student_user):
        """Teacher default issuance target: enrolled student only."""
        self._enroll_student(teacher_user=teacher_user, student_user=student_user)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["targetRole"] == Role.STUDENT

    def test_AUTH_UC_07_RESEARCHER_DEFAULT(
        self, api_client, researcher_user, teacher_user, student_user
    ):
        """Researcher default issuance target: teacher."""
        api_client.force_authenticate(user=researcher_user)
        teacher_response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": teacher_user.id},
            format="json",
        )
        assert teacher_response.status_code == 201
        assert teacher_response.json()["targetRole"] == Role.TEACHER

        student_response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert student_response.status_code == 403

    def test_AUTH_UC_07_RESEARCHER_SUDO_STUDENT(
        self, api_client, admin_user, researcher_user, student_user
    ):
        """Researcher with ISSUE_STUDENT_RESET_CODE can issue student reset codes."""
        self._grant_permissions(
            admin_user=admin_user,
            researcher_user=researcher_user,
            permissions=[SudoPermission.ISSUE_STUDENT_RESET_CODE.value],
        )
        api_client.force_authenticate(user=researcher_user)
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": student_user.id},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["targetRole"] == Role.STUDENT

    def test_AUTH_UC_07_RESEARCHER_SUDO_RESEARCHER(self, api_client, admin_user, researcher_user):
        """Researcher with ISSUE_RESEARCHER_RESET_CODE can issue researcher reset codes."""
        target = UserFactory()
        UserRole.objects.create(user=target, role=Role.RESEARCHER)
        ResearcherProfile.objects.create(user=target)
        self._grant_permissions(
            admin_user=admin_user,
            researcher_user=researcher_user,
            permissions=[SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value],
        )
        api_client.force_authenticate(user=researcher_user)
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": target.id},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["targetRole"] == Role.RESEARCHER

    def test_AUTH_UC_07_E2(self, api_client, teacher_user):
        """AUTH-UC-07-E2: target not in issuer scope is rejected."""
        target_teacher = UserFactory()
        UserRole.objects.create(user=target_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=target_teacher)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": target_teacher.id},
            format="json",
        )
        assert response.status_code == 403
