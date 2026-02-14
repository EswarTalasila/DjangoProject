"""Integration tests for accounts routes."""

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import (
    OAuthAccount,
    OAuthProvider,
    PasswordResetCode,
    PasswordResetRequest,
    PasswordResetRequestStatus,
    RegistrationCode,
    RegistrationCodeType,
    ResearcherProfile,
    Role,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from accounts.services import registration_code_hash, registration_code_prefix
from courses.models import Course, Enrollment


@pytest.mark.django_db
class TestAccountRoutes:
    def _student_code(self, teacher_user, code="INVITE1", course_name="Course A", max_uses=5):
        course = Course.objects.create(
            name=course_name, teacher_profile=teacher_user.teacher_profile
        )
        return RegistrationCode.objects.create(
            code_hash=registration_code_hash(code),
            code_prefix=registration_code_prefix(code),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher_user,
            course=course,
            max_uses=max_uses,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

    def _non_student_code(self, creator, *, code: str, code_type: str):
        return RegistrationCode.objects.create(
            code_hash=registration_code_hash(code),
            code_prefix=registration_code_prefix(code),
            code_type=code_type,
            created_by=creator,
            course=None,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

    def _create_user_for_auth_uc_01(
        self, *, role: str, username: str, email: str | None = None, password: str = "StartPass123!"
    ) -> User:
        user = User.objects.create_user(
            username=username,
            email=email,
            name=f"{role} User",
            password=password,
        )
        if role == "ADMIN":
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            return user
        UserRole.objects.create(user=user, role=role)
        if role == Role.TEACHER:
            TeacherProfile.objects.create(user=user)
        return user

    def _assert_auth_uc_01_role_login(
        self, api_client, *, role: str, identifier: str, password: str = "StartPass123!"
    ) -> None:
        response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": identifier, "password": password},
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert "accessToken" in payload
        assert "refreshToken" in payload
        assert payload["role"] == role

    def test_REG_UC_01_STUDENT(self, api_client):
        """Local registration creates a student from invite code with generated username."""
        teacher = User.objects.create_user(
            username="teacher@example.com",
            name="Teacher",
            password="testpass123",
        )
        UserRole.objects.create(user=teacher, role=Role.TEACHER)
        TeacherProfile.objects.get_or_create(user=teacher)
        self._student_code(teacher, code="INVITE-STUDENT-1")
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "INVITE-STUDENT-1",
                "password": "testpass123",
                "name": "Student Name",
                "role": "ROLE_TEACHER",  # Should be ignored, always creates student
            },
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        user = User.objects.get(username=payload["username"])
        role = user.roles.values_list("role", flat=True).first()
        assert role == Role.STUDENT

    def test_REG_UC_01_E5(self, api_client, teacher_user, monkeypatch):
        """Student code OAuth registration attempts are rejected."""
        self._student_code(teacher_user, code="INVITE-STUDENT-OAUTH")
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {
                "sub": "student-oauth-sub",
                "email": "student-oauth@example.com",
                "name": "Student OAuth",
            },
        )
        response = api_client.post(
            "/api/v1/registration/accounts",
            {"method": "OAUTH", "code": "INVITE-STUDENT-OAUTH", "accessToken": "oauth-token"},
            format="json",
        )
        assert response.status_code == 400
        assert "do not support OAuth" in response.json()["detail"]

    def test_REG_UC_01_RESEARCHER(self, api_client, admin_user, monkeypatch):
        """Researcher invite code supports both OAuth and local registration."""
        oauth_code = "INVITE-RESEARCHER-OAUTH"
        local_code = "INVITE-RESEARCHER-LOCAL"
        self._non_student_code(
            admin_user, code=oauth_code, code_type=RegistrationCodeType.RESEARCHER
        )
        self._non_student_code(
            admin_user, code=local_code, code_type=RegistrationCodeType.RESEARCHER
        )
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {
                "sub": "researcher-oauth-sub",
                "email": "researcher-oauth@example.com",
                "name": "Researcher OAuth",
                "email_verified": True,
            },
        )
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "OAUTH",
                "code": oauth_code,
                "accessToken": "oauth-token",
                "username": "researcher-oauth-user",
            },
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["role"] == Role.RESEARCHER
        assert payload["username"] == "researcher-oauth-user"
        assert "refreshToken" in payload

        user = User.objects.get(username="researcher-oauth-user")
        assert user.email == "researcher-oauth@example.com"
        assert user.roles.filter(role=Role.RESEARCHER).exists()
        assert OAuthAccount.objects.filter(
            user=user,
            provider=OAuthProvider.GOOGLE,
            subject="researcher-oauth-sub",
        ).exists()

        local_response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": local_code,
                "name": "Local Researcher",
                "username": "local-researcher",
                "email": "local-researcher@example.com",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert local_response.status_code == 200
        local_payload = local_response.json()
        assert local_payload["role"] == Role.RESEARCHER
        assert local_payload["username"] == "local-researcher"
        assert "refreshToken" in local_payload

    def test_REG_UC_01_TEACHER(self, api_client, researcher_user):
        """Teacher invite code supports local non-student registration."""
        self._non_student_code(
            researcher_user,
            code="INVITE-TEACHER-LOCAL",
            code_type=RegistrationCodeType.TEACHER,
        )
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "INVITE-TEACHER-LOCAL",
                "name": "Local Teacher",
                "username": "local-teacher",
                "email": "local-teacher@example.com",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["role"] == Role.TEACHER
        assert payload["username"] == "local-teacher"
        assert "refreshToken" in payload

    def test_REG_UC_01_E3(self, api_client, researcher_user):
        """Non-student local registration requires username and email."""
        self._non_student_code(
            researcher_user,
            code="INVITE-TEACHER-MISSING",
            code_type=RegistrationCodeType.TEACHER,
        )
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "INVITE-TEACHER-MISSING",
                "name": "Missing Fields",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "username is required" in response.json()["detail"]

    def test_AUTH_UC_01(self, api_client):
        """Domain aggregator: all role-specific AUTH-UC-01 login paths must pass."""
        self._create_user_for_auth_uc_01(
            role="ADMIN",
            username="admin-login",
            email="admin-login@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role="ADMIN",
            identifier="admin-login@example.com",
        )

        self._create_user_for_auth_uc_01(
            role=Role.RESEARCHER,
            username="researcher-login",
            email="researcher-login@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role=Role.RESEARCHER,
            identifier="researcher-login",
        )

        self._create_user_for_auth_uc_01(
            role=Role.TEACHER,
            username="teacher-login",
            email="teacher-login@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role=Role.TEACHER,
            identifier="teacher-login@example.com",
        )

        self._create_user_for_auth_uc_01(
            role=Role.STUDENT,
            username="student-login",
            email="student-login@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role=Role.STUDENT,
            identifier="student-login",
        )

    def test_AUTH_UC_01_ADMIN(self, api_client):
        """ADMIN login via identifier."""
        self._create_user_for_auth_uc_01(
            role="ADMIN",
            username="admin-role",
            email="admin-role@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role="ADMIN",
            identifier="admin-role@example.com",
        )

    def test_AUTH_UC_01_RESEARCHER(self, api_client):
        """RESEARCHER login via identifier."""
        self._create_user_for_auth_uc_01(
            role=Role.RESEARCHER,
            username="researcher-role",
            email="researcher-role@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role=Role.RESEARCHER,
            identifier="researcher-role",
        )

    def test_AUTH_UC_01_STUDENT(self, api_client):
        """STUDENT login via username identifier."""
        self._create_user_for_auth_uc_01(
            role=Role.STUDENT,
            username="student-role",
            email="student-role@example.com",
        )
        self._assert_auth_uc_01_role_login(
            api_client,
            role=Role.STUDENT,
            identifier="student-role",
        )

    def test_REG_UC_01(self, api_client, teacher_user):
        """Validate-code returns course context for a valid student invite."""
        self._student_code(teacher_user, code="INVITE-CONTEXT", course_name="Biology")
        response = api_client.post(
            "/api/v1/registration/code-validations",
            {"code": "INVITE-CONTEXT"},
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is True
        assert payload["code_type"] == RegistrationCodeType.STUDENT
        assert payload["context"]["course_name"] == "Biology"

    def test_REG_UC_01a_STUDENT(self, api_client, teacher_user):
        """Authenticated student can redeem another code to join an additional course."""
        first_code = self._student_code(teacher_user, code="INVITE-FIRST", course_name="Math")
        second_code = self._student_code(teacher_user, code="INVITE-SECOND", course_name="Science")
        assert first_code.course_id != second_code.course_id

        create_res = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "INVITE-FIRST",
                "name": "Multi Student",
                "password": "testpass123",
            },
            format="json",
        )
        assert create_res.status_code == 200
        username = create_res.json()["username"]

        user = User.objects.get(username=username)
        api_client.force_authenticate(user=user)
        redeem_res = api_client.post(
            "/api/v1/enrollments",
            {"code": "INVITE-SECOND"},
            format="json",
        )
        assert redeem_res.status_code == 200
        assert redeem_res.json()["alreadyEnrolled"] is False

        enrollment_count = Enrollment.objects.filter(student_profile=user.student_profile).count()
        assert enrollment_count == 2
        first_code.refresh_from_db()
        second_code.refresh_from_db()
        assert first_code.times_used == 1
        assert second_code.times_used == 1

    def test_REG_CN_20(self, api_client, teacher_user):
        """Already-enrolled redemption succeeds and does not consume code usage."""
        first_code = self._student_code(teacher_user, code="IDEMP-FIRST", course_name="Math")
        second_code = RegistrationCode.objects.create(
            code_hash=registration_code_hash("IDEMP-SECOND"),
            code_prefix=registration_code_prefix("IDEMP-SECOND"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher_user,
            course=first_code.course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        create_res = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "IDEMP-FIRST",
                "name": "Repeat Student",
                "password": "testpass123",
            },
            format="json",
        )
        assert create_res.status_code == 200
        username = create_res.json()["username"]

        user = User.objects.get(username=username)
        api_client.force_authenticate(user=user)
        redeem_res = api_client.post(
            "/api/v1/enrollments",
            {"code": "IDEMP-SECOND"},
            format="json",
        )
        assert redeem_res.status_code == 200
        payload = redeem_res.json()
        assert payload["alreadyEnrolled"] is True
        assert payload["message"] == "Already enrolled"

        enrollment_count = Enrollment.objects.filter(student_profile=user.student_profile).count()
        assert enrollment_count == 1

        second_code.refresh_from_db()
        assert second_code.times_used == 0
        assert second_code.is_active is True

    def test_REG_UC_01a_E2(self, api_client, teacher_user):
        """Join-course endpoint is authenticated and student-role scoped."""
        code = self._student_code(teacher_user, code="JOIN-AUTH")

        unauthenticated = api_client.post(
            "/api/v1/enrollments",
            {"code": "JOIN-AUTH"},
            format="json",
        )
        assert unauthenticated.status_code == 401

        api_client.force_authenticate(user=teacher_user)
        forbidden = api_client.post(
            "/api/v1/enrollments",
            {"code": "JOIN-AUTH"},
            format="json",
        )
        assert forbidden.status_code == 403

        code.refresh_from_db()
        assert code.times_used == 0

    def test_REG_UC_02_TEACHER(self, api_client, teacher_user):
        """Teacher can generate student registration codes for their own course."""
        course = Course.objects.create(
            name="Code Gen Course", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 2,
                "usesPerCode": 3,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["count"] == 2
        assert len(payload["codes"]) == 2
        assert all(entry["codeType"] == RegistrationCodeType.STUDENT for entry in payload["codes"])
        assert all(entry["status"] == "ACTIVE" for entry in payload["codes"])
        assert all(entry["code"] is not None for entry in payload["codes"])
        assert all(entry["codePrefix"] is not None for entry in payload["codes"])

        # Hash-at-rest: returned plaintext codes are not persisted directly.
        generated_hashes = {registration_code_hash(entry["code"]) for entry in payload["codes"]}
        db_hashes = set(
            RegistrationCode.objects.filter(
                created_by=teacher_user,
                course=course,
                code_type=RegistrationCodeType.STUDENT,
            ).values_list("code_hash", flat=True)
        )
        assert generated_hashes.issubset(db_hashes)

    def test_REG_UC_02_RESEARCHER(self, api_client, researcher_user):
        """Researcher can generate a teacher code with metadata when count is one."""
        api_client.force_authenticate(user=researcher_user)
        metadata = {"district": "Wake", "school": "NCSU Lab School"}
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.TEACHER,
                "count": 1,
                "usesPerCode": 2,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "metadata": metadata,
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["count"] == 1
        assert payload["codes"][0]["codeType"] == RegistrationCodeType.TEACHER
        assert payload["codes"][0]["metadata"] == metadata

        persisted = RegistrationCode.objects.get(id=payload["codes"][0]["id"])
        assert persisted.metadata == metadata

    def test_REG_UC_02_E4(self, api_client, researcher_user):
        """Metadata with count greater than one is rejected."""
        api_client.force_authenticate(user=researcher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.TEACHER,
                "count": 2,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "metadata": {"district": "Wake"},
            },
            format="json",
        )
        assert response.status_code == 400
        assert "count must be 1" in str(response.json())

    def test_REG_CN_10(self, api_client, researcher_user, admin_user, teacher_user):
        """Researcher sudo permission expands code generation and lifecycle scope to student codes."""
        course = Course.objects.create(
            name="Researcher Student Code Scope",
            teacher_profile=teacher_user.teacher_profile,
        )
        foreign_code = self._student_code(teacher_user, code="TEACHER-ONLY-SCOPE")

        api_client.force_authenticate(user=researcher_user)
        denied = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert denied.status_code == 403

        SudoGrant.objects.create(
            user=researcher_user,
            granted_by=admin_user,
            permissions=[SudoPermission.CREATE_STUDENT],
        )

        allowed = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert allowed.status_code == 201
        created_code_id = allowed.json()["codes"][0]["id"]

        list_response = api_client.get("/api/v1/codes")
        assert list_response.status_code == 200
        listed_ids = {entry["id"] for entry in list_response.json()}
        assert created_code_id in listed_ids
        assert foreign_code.id not in listed_ids

        detail_response = api_client.get(f"/api/v1/codes/{created_code_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["codeType"] == RegistrationCodeType.STUDENT

        revoke_response = api_client.patch(
            f"/api/v1/codes/{created_code_id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["status"] == "REVOKED"

        forbidden_foreign = api_client.patch(
            f"/api/v1/codes/{foreign_code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert forbidden_foreign.status_code == 404

    def test_REG_UC_03_TEACHER(self, api_client, teacher_user):
        """Teacher can list, revoke, and archive own student codes."""
        code = self._student_code(teacher_user, code="LIFE-ONE", max_uses=1)
        api_client.force_authenticate(user=teacher_user)

        list_response = api_client.get("/api/v1/codes")
        assert list_response.status_code == 200
        listed_payload = list_response.json()
        listed_ids = {entry["id"] for entry in listed_payload}
        assert code.id in listed_ids
        listed_code = next(entry for entry in listed_payload if entry["id"] == code.id)
        assert listed_code["code"] is None
        assert listed_code["codePrefix"] == registration_code_prefix("LIFE-ONE")

        revoke_response = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["status"] == "REVOKED"

        archive_response = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "ARCHIVED"},
            format="json",
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "ARCHIVED"

    def test_REG_UC_03_E1(self, api_client, teacher_user):
        """Teacher cannot transition registration codes outside their scope."""
        other_teacher = User.objects.create_user(
            username="other-teacher",
            email="other-teacher@example.com",
            name="Other Teacher",
            password="StartPass123!",
        )
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        foreign_code = self._student_code(other_teacher, code="FOREIGN-CODE")

        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(
            f"/api/v1/codes/{foreign_code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert response.status_code == 404

    def test_AUTH_UC_03(self, api_client):
        """Refresh returns a new access token and logout invalidates the refresh token."""
        user = User.objects.create_user(
            username="refresh-user",
            email="refresh@example.com",
            name="Refresh User",
            password="StartPass123!",
        )
        UserRole.objects.create(user=user, role=Role.TEACHER)
        TeacherProfile.objects.create(user=user)

        login_response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "refresh@example.com", "password": "StartPass123!"},
            format="json",
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refreshToken"]

        refresh_response = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert refresh_response.status_code == 200
        assert "accessToken" in refresh_response.json()

        api_client.force_authenticate(user=user)
        logout_response = api_client.post(
            "/api/v1/auth/session-revocations",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert logout_response.status_code == 200

        refresh_after_logout = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert refresh_after_logout.status_code == 401

    def test_AUTH_UC_04(self, api_client):
        """Password change invalidates existing refresh tokens and requires re-login."""
        user = User.objects.create_user(
            username="changepass-user",
            email="changepass@example.com",
            name="Change Pass",
            password="OldPass123!",
        )
        UserRole.objects.create(user=user, role=Role.TEACHER)
        TeacherProfile.objects.create(user=user)

        login_response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "changepass-user", "password": "OldPass123!"},
            format="json",
        )
        assert login_response.status_code == 200
        payload = login_response.json()
        refresh_token = payload["refreshToken"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['accessToken']}")

        change_response = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "OldPass123!",
                "newPassword": "NewPass123!",
                "confirmPassword": "NewPass123!",
            },
            format="json",
        )
        assert change_response.status_code == 200

        refresh_after_change = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert refresh_after_change.status_code == 401

        relogin = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "changepass-user", "password": "NewPass123!"},
            format="json",
        )
        assert relogin.status_code == 200

    def test_AUTH_UC_05_STUDENT(self, api_client, teacher_user):
        """Teacher directly issues student reset code; student verifies and completes reset."""
        self._student_code(teacher_user, code="RESET-CODE-1", course_name="Reset Course")
        register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "RESET-CODE-1",
                "name": "Reset Student",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert register.status_code == 200
        student_identifier = register.json()["username"]
        student_user = User.objects.get(username=student_identifier)
        course_id = student_user.student_profile.enrollments.first().course_id

        api_client.force_authenticate(user=teacher_user)
        issue_response = api_client.post(
            f"/api/v1/courses/{course_id}/students/{student_user.id}/reset-code",
            {},
            format="json",
        )
        assert issue_response.status_code == 200
        issue_payload = issue_response.json()
        assert issue_payload["studentUserId"] == student_user.id
        assert issue_payload["courseId"] == course_id
        reset_code = issue_payload["resetCode"]
        assert reset_code.startswith("RESET-")
        latest_request = student_user.password_reset_requests.order_by("-id").first()
        assert latest_request is not None
        assert latest_request.status == PasswordResetRequestStatus.APPROVED
        assert latest_request.reviewed_by_id == teacher_user.id

        verify_response = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": student_identifier, "resetCode": reset_code},
            format="json",
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

        api_client.force_authenticate(user=None)
        complete_response = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": student_identifier,
                "resetCode": reset_code,
                "newPassword": "AfterReset123!",
                "confirmPassword": "AfterReset123!",
            },
            format="json",
        )
        assert complete_response.status_code == 200

        login_after = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": student_identifier, "password": "AfterReset123!"},
            format="json",
        )
        assert login_after.status_code == 200

    def test_AUTH_CN_05_STUDENT(self, api_client, teacher_user):
        """Student identifiers cannot use request/status endpoints in the approval queue flow."""
        self._student_code(teacher_user, code="RESET-CODE-2", course_name="Reset Course 2")
        register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "RESET-CODE-2",
                "name": "Blocked Student Reset Request",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert register.status_code == 200
        student_identifier = register.json()["username"]

        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": student_identifier},
            format="json",
        )
        assert request_response.status_code == 400
        assert request_response.json()["detail"] == "Unable to create reset request."

        status_response = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": student_identifier, "requestToken": "REQ-DOES-NOT-EXIST"},
            format="json",
        )
        assert status_response.status_code == 404
        assert status_response.json()["detail"] == "Invalid identifier or request token."

    def test_AUTH_UC_07_E1(self, api_client, teacher_user):
        """Teacher direct-reset endpoint is restricted to students in the teacher's own courses."""
        other_teacher = User.objects.create_user(
            username="other-reset-teacher",
            email="other-reset-teacher@example.com",
            name="Other Reset Teacher",
            password="StartPass123!",
        )
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)
        foreign_code = self._student_code(other_teacher, code="FOREIGN-RESET-CODE")

        register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "FOREIGN-RESET-CODE",
                "name": "Foreign Student",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert register.status_code == 200
        student_user = User.objects.get(username=register.json()["username"])

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            f"/api/v1/courses/{foreign_code.course_id}/students/{student_user.id}/reset-code",
            {},
            format="json",
        )
        assert response.status_code == 403

    def test_AUTH_UC_07_RESEARCHER(self, api_client, teacher_user, researcher_user):
        """Only researcher/admin can approve queued non-student reset requests."""
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": teacher_user.email or teacher_user.username},
            format="json",
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["requestId"]

        api_client.force_authenticate(user=teacher_user)
        teacher_attempt = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert teacher_attempt.status_code == 403

        api_client.force_authenticate(user=researcher_user)
        researcher_attempt = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert researcher_attempt.status_code == 200
        assert researcher_attempt.json()["status"] == PasswordResetRequestStatus.APPROVED
        assert researcher_attempt.json()["resetCode"].startswith("RESET-")

    def test_USER_UC_01_ADMIN(self, api_client, admin_user):
        """Admin can create a teacher account."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "username": "teacher@example.com",
            "email": "teacher-contact@example.com",
            "password": "testpass123",
            "name": "Teacher Name",
            "role": "ROLE_TEACHER",
        }
        response = api_client.post("/api/v1/users", payload, format="json")
        assert response.status_code == 200
        created = User.objects.get(username="teacher@example.com")
        assert created.email == "teacher-contact@example.com"
        assert created.teacher_profile is not None

    def test_USER_UC_01_E2(self, api_client, teacher_user):
        """Teacher cannot create a researcher account."""
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "username": "researcher@example.com",
            "email": "researcher@example.com",
            "password": "testpass123",
            "name": "Researcher",
            "role": "ROLE_RESEARCHER",
        }
        response = api_client.post("/api/v1/users", payload, format="json")
        assert response.status_code == 403

    def test_REG_CN_16(self, api_client, teacher_user):
        """Student username is generated, collision-suffixed, and immutable."""
        self._student_code(teacher_user, code="REG-CN16-STUDENT-A")
        first_register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN16-STUDENT-A",
                "password": "StartPass123!",
                "name": "Jane Smith",
            },
            format="json",
        )
        assert first_register.status_code == 200
        first_username = first_register.json()["username"]
        assert first_username == "jsmith"

        self._student_code(teacher_user, code="REG-CN16-STUDENT-B")
        second_register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN16-STUDENT-B",
                "password": "StartPass123!",
                "name": "Jane Smith",
            },
            format="json",
        )
        assert second_register.status_code == 200
        second_username = second_register.json()["username"]
        assert second_username == "jsmith2"

        student = User.objects.get(username=first_username)
        original_username = first_username

        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(
            f"/api/v1/users/{student.id}",
            {"username": "renamed-student"},
            format="json",
        )
        assert response.status_code == 400
        assert response.json() == "Student usernames are immutable after account creation."

        student.refresh_from_db()
        assert student.username == original_username

    def test_USER_UC_03_E2(self, api_client, teacher_user, admin_user):
        """Teacher edit is denied for a non-owned target user."""
        api_client.force_authenticate(user=teacher_user)
        payload = {
            "name": "Admin Updated",
            "username": admin_user.username,
        }
        response = api_client.patch(f"/api/v1/users/{admin_user.id}", payload, format="json")
        assert response.status_code == 403

    def test_USER_UC_05_ADMIN(self, api_client, admin_user, teacher_user):
        """Staff listing returns teacher and researcher users."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/v1/users/staff")
        assert response.status_code == 200
        # Endpoint returns TEACHER and RESEARCHER roles only (not staff-only admins)
        usernames = {entry["username"] for entry in response.json()}
        assert teacher_user.username in usernames

    def test_USER_UC_02_ADMIN(self, api_client, admin_user):
        """Bulk create returns the number of users created."""
        api_client.force_authenticate(user=admin_user)
        payload = [
            {
                "username": "bulk1",
                "email": "bulk1@example.com",
                "name": "Bulk One",
                "role": "ROLE_TEACHER",
            },
            {
                "username": "bulk2",
                "email": "bulk2@example.com",
                "name": "Bulk Two",
                "role": "ROLE_TEACHER",
            },
        ]
        response = api_client.post("/api/v1/user-batches", payload, format="json")
        assert response.status_code == 200
        assert response.json() == 2

    def test_USER_UC_04_E1(self, api_client, admin_user, teacher_user):
        """Non-admin user deletion attempts are forbidden."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/users/{admin_user.id}")
        assert response.status_code == 403

    def test_USER_UC_01(self, api_client, admin_user):
        """Created user is assigned exactly one role."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "username": "singleuser",
            "email": "single@example.com",
            "password": "testpass123",
            "name": "Single Role",
            "role": "ROLE_TEACHER",
        }
        response = api_client.post("/api/v1/users", payload, format="json")
        assert response.status_code == 200
        roles = UserRole.objects.filter(user__username="singleuser")
        assert roles.count() == 1
        assert roles.first().role == Role.TEACHER

    def test_AUTH_UC_01_TEACHER(self, api_client):
        """Non-students can log in with either username or email."""
        user = User.objects.create_user(
            username="teachernotemail",
            email="teachernotemail@example.com",
            name="Teacher No Email",
            password="StartPass123!",
        )
        UserRole.objects.create(user=user, role=Role.TEACHER)
        TeacherProfile.objects.create(user=user)

        username_login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "teachernotemail", "password": "StartPass123!"},
            format="json",
        )
        assert username_login.status_code == 200

        email_login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "teachernotemail@example.com", "password": "StartPass123!"},
            format="json",
        )
        assert email_login.status_code == 200

    def test_AUTH_CN_12(self, api_client):
        """Students cannot log in with email, even when an email value exists."""
        user = User.objects.create_user(
            username="student-only",
            email="student-only@example.com",
            name="Student Identifier Policy",
            password="StartPass123!",
        )
        UserRole.objects.create(user=user, role=Role.STUDENT)

        email_login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "student-only@example.com", "password": "StartPass123!"},
            format="json",
        )
        assert email_login.status_code == 401

        username_login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "student-only", "password": "StartPass123!"},
            format="json",
        )
        assert username_login.status_code == 200

    def test_USER_UC_01_E3(self, api_client, admin_user):
        """Non-student user creation requires an email."""
        api_client.force_authenticate(user=admin_user)
        payload = {
            "username": "teacher-no-email",
            "password": "testpass123",
            "name": "Teacher Missing Email",
            "role": "ROLE_TEACHER",
        }
        response = api_client.post("/api/v1/users", payload, format="json")
        assert response.status_code == 400
        assert response.json() == "email is required for non-student users"

    # ── Bucket 1: AUTH-UC-05/06/07 Non-Student Queue Flow ──

    def _create_non_student_for_reset(self, *, role, username, email, password="StartPass123!"):
        """Helper: create a non-student user ready for reset tests."""
        user = User.objects.create_user(
            username=username, email=email, name=f"{role} Reset User", password=password
        )
        UserRole.objects.create(user=user, role=role)
        if role == Role.TEACHER:
            TeacherProfile.objects.create(user=user)
        elif role == Role.RESEARCHER:
            ResearcherProfile.objects.create(user=user)
        return user

    def test_AUTH_UC_05(self, api_client, researcher_user):
        """Domain aggregator: non-student reset flow (request → approve → verify → complete → login)."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="reset-agg-teacher", email="reset-agg-teacher@example.com"
        )
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "reset-agg-teacher@example.com"},
            format="json",
        )
        assert request_response.status_code == 201
        payload = request_response.json()
        request_id = payload["requestId"]
        request_token = payload["requestToken"]
        assert request_token.startswith("REQ-")
        assert payload["status"] == PasswordResetRequestStatus.PENDING

        api_client.force_authenticate(user=researcher_user)
        approve_response = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve_response.status_code == 200
        reset_code = approve_response.json()["resetCode"]
        assert reset_code.startswith("RESET-")

        api_client.force_authenticate(user=None)
        verify_response = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": "reset-agg-teacher@example.com", "resetCode": reset_code},
            format="json",
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

        complete_response = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "reset-agg-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "NewTeacherPass1!",
                "confirmPassword": "NewTeacherPass1!",
            },
            format="json",
        )
        assert complete_response.status_code == 200

        login_response = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "reset-agg-teacher@example.com", "password": "NewTeacherPass1!"},
            format="json",
        )
        assert login_response.status_code == 200

    def test_AUTH_UC_05_RESEARCHER(self, api_client, admin_user):
        """Researcher submits reset request; admin approves; researcher completes reset."""
        self._create_non_student_for_reset(
            role=Role.RESEARCHER,
            username="reset-researcher",
            email="reset-researcher@example.com",
        )
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "reset-researcher@example.com"},
            format="json",
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["requestId"]

        api_client.force_authenticate(user=admin_user)
        approve_response = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve_response.status_code == 200
        reset_code = approve_response.json()["resetCode"]

        api_client.force_authenticate(user=None)
        complete = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "reset-researcher@example.com",
                "resetCode": reset_code,
                "newPassword": "NewResPass1!",
                "confirmPassword": "NewResPass1!",
            },
            format="json",
        )
        assert complete.status_code == 200

        login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "reset-researcher@example.com", "password": "NewResPass1!"},
            format="json",
        )
        assert login.status_code == 200

    def test_AUTH_UC_05_TEACHER(self, api_client, researcher_user):
        """Teacher submits reset request; researcher approves; teacher completes reset."""
        self._create_non_student_for_reset(
            role=Role.TEACHER,
            username="reset-teacher-05",
            email="reset-teacher-05@example.com",
        )
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "reset-teacher-05@example.com"},
            format="json",
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["requestId"]

        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve.status_code == 200
        reset_code = approve.json()["resetCode"]

        api_client.force_authenticate(user=None)
        complete = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "reset-teacher-05@example.com",
                "resetCode": reset_code,
                "newPassword": "NewTeach1!Pass",
                "confirmPassword": "NewTeach1!Pass",
            },
            format="json",
        )
        assert complete.status_code == 200

        login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": "reset-teacher-05@example.com", "password": "NewTeach1!Pass"},
            format="json",
        )
        assert login.status_code == 200

    def test_AUTH_UC_05_E1(self, api_client, researcher_user):
        """AUTH-UC-05-E1: approver denies a reset request; status updates to DENIED."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="deny-teacher", email="deny-teacher@example.com"
        )
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "deny-teacher@example.com"},
            format="json",
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["requestId"]

        api_client.force_authenticate(user=researcher_user)
        deny_response = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.DENIED, "reason": "Identity not verified"},
            format="json",
        )
        assert deny_response.status_code == 200
        assert deny_response.json()["status"] == PasswordResetRequestStatus.DENIED
        assert "resetCode" not in deny_response.json()

    def test_AUTH_UC_05_E2(self, api_client):
        """AUTH-UC-05-E2: pending request window expires; status updates to EXPIRED."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="expire-teacher", email="expire-teacher@example.com"
        )
        request_response = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "expire-teacher@example.com"},
            format="json",
        )
        assert request_response.status_code == 201
        payload = request_response.json()
        request_id = payload["requestId"]
        request_token = payload["requestToken"]

        req = PasswordResetRequest.objects.get(id=request_id)
        req.expires_at = timezone.now() - timedelta(minutes=1)
        req.save(update_fields=["expires_at"])

        status_response = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": "expire-teacher@example.com", "requestToken": request_token},
            format="json",
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == PasswordResetRequestStatus.EXPIRED

    def test_AUTH_UC_05_E3(self, api_client, researcher_user):
        """AUTH-UC-05-E3: reset code invalid, expired, and already-used are all rejected."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="e3-teacher", email="e3-teacher@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "e3-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        request_id = req.json()["requestId"]

        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve.status_code == 200
        reset_code = approve.json()["resetCode"]
        api_client.force_authenticate(user=None)

        # Wrong code
        wrong = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": "e3-teacher@example.com", "resetCode": "RESET-WRONG"},
            format="json",
        )
        assert wrong.status_code == 400
        assert wrong.json()["valid"] is False

        # Expired code
        code_obj = PasswordResetCode.objects.get(request_id=request_id)
        code_obj.expires_at = timezone.now() - timedelta(minutes=1)
        code_obj.save(update_fields=["expires_at"])

        expired = api_client.post(
            "/api/v1/auth/reset-code-validations",
            {"identifier": "e3-teacher@example.com", "resetCode": reset_code},
            format="json",
        )
        assert expired.status_code == 400

        # Restore for used-code test
        code_obj.expires_at = timezone.now() + timedelta(minutes=30)
        code_obj.save(update_fields=["expires_at"])
        pr = PasswordResetRequest.objects.get(id=request_id)
        pr.status = PasswordResetRequestStatus.APPROVED
        pr.save(update_fields=["status"])

        # Use the code
        complete = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "e3-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "AfterE3Test1!",
                "confirmPassword": "AfterE3Test1!",
            },
            format="json",
        )
        assert complete.status_code == 200

        # Already-used code
        used = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "e3-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "Another1!Pass",
                "confirmPassword": "Another1!Pass",
            },
            format="json",
        )
        assert used.status_code == 400

    def test_AUTH_UC_05_E4(self, api_client):
        """AUTH-UC-05-E4: existing pending request blocks duplicate request creation."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="e4-teacher", email="e4-teacher@example.com"
        )
        first = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "e4-teacher@example.com"},
            format="json",
        )
        assert first.status_code == 201

        duplicate = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "e4-teacher@example.com"},
            format="json",
        )
        assert duplicate.status_code == 400
        assert "pending" in duplicate.json()["detail"].lower()

    def test_AUTH_UC_05_E5(self, api_client, researcher_user):
        """AUTH-UC-05-E5: reset password validation (weak, mismatch, same as old)."""
        self._create_non_student_for_reset(
            role=Role.TEACHER,
            username="e5-teacher",
            email="e5-teacher@example.com",
            password="OldPass123!",
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "e5-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        request_id = req.json()["requestId"]

        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve.status_code == 200
        reset_code = approve.json()["resetCode"]
        api_client.force_authenticate(user=None)

        # Weak password
        weak = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "e5-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "short",
                "confirmPassword": "short",
            },
            format="json",
        )
        assert weak.status_code == 400

        # Mismatch
        mismatch = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "e5-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "ValidNew1!Pass",
                "confirmPassword": "Different1!Pass",
            },
            format="json",
        )
        assert mismatch.status_code == 400

        # Same as old
        same = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "e5-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "OldPass123!",
                "confirmPassword": "OldPass123!",
            },
            format="json",
        )
        assert same.status_code == 400

    def test_AUTH_CN_06(self, api_client, teacher_user, researcher_user):
        """AUTH-CN-06: student resets have fixed 30-min expiry; non-student approvals configurable."""
        # Student: teacher-initiated, fixed 30 min
        self._student_code(teacher_user, code="CN06-STUDENT", course_name="CN06 Course")
        reg = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "CN06-STUDENT",
                "name": "CN06 Student",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert reg.status_code == 200
        student = User.objects.get(username=reg.json()["username"])
        course_id = student.student_profile.enrollments.first().course_id

        api_client.force_authenticate(user=teacher_user)
        issue = api_client.post(
            f"/api/v1/courses/{course_id}/students/{student.id}/reset-code",
            {},
            format="json",
        )
        assert issue.status_code == 200
        student_request = PasswordResetRequest.objects.filter(user=student).latest("id")
        student_code = PasswordResetCode.objects.get(request=student_request)
        delta = (student_code.expires_at - student_request.reviewed_at).total_seconds()
        assert 1795 <= delta <= 1805  # 30 min = 1800 sec ±5s tolerance

        # Non-student: configurable expiry via date+time picker
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="cn06-teacher", email="cn06-teacher@example.com"
        )
        api_client.force_authenticate(user=None)
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "cn06-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        request_id = req.json()["requestId"]

        custom_expiry = (timezone.now() + timedelta(hours=2)).isoformat()
        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED, "expires_at": custom_expiry},
            format="json",
        )
        assert approve.status_code == 200
        non_student_code = PasswordResetCode.objects.get(request_id=request_id)
        delta_ns = (non_student_code.expires_at - timezone.now()).total_seconds()
        assert delta_ns > 3600  # custom expiry is >1 hour out, not default 30 min

    def test_AUTH_CN_07(self, api_client, researcher_user):
        """AUTH-CN-07: reset codes are single-use; second use is rejected."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="cn07-teacher", email="cn07-teacher@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "cn07-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201

        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{req.json()['requestId']}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        reset_code = approve.json()["resetCode"]
        api_client.force_authenticate(user=None)

        first = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "cn07-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "FirstNew1!Pass",
                "confirmPassword": "FirstNew1!Pass",
            },
            format="json",
        )
        assert first.status_code == 200

        second = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "cn07-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "SecondNew1!Pass",
                "confirmPassword": "SecondNew1!Pass",
            },
            format="json",
        )
        assert second.status_code == 400

    def test_AUTH_CN_08(self, api_client, researcher_user):
        """AUTH-CN-08: failed validation does not consume the reset code (atomic)."""
        self._create_non_student_for_reset(
            role=Role.TEACHER,
            username="cn08-teacher",
            email="cn08-teacher@example.com",
            password="OldAtomic1!",
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "cn08-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201

        api_client.force_authenticate(user=researcher_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{req.json()['requestId']}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        reset_code = approve.json()["resetCode"]
        api_client.force_authenticate(user=None)

        # Fail: same-as-old password should NOT consume the code
        fail_response = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "cn08-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "OldAtomic1!",
                "confirmPassword": "OldAtomic1!",
            },
            format="json",
        )
        assert fail_response.status_code == 400

        code_obj = PasswordResetCode.objects.get(request_id=req.json()["requestId"])
        assert code_obj.used_at is None

        # Succeed: code still works after failed attempt
        success = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": "cn08-teacher@example.com",
                "resetCode": reset_code,
                "newPassword": "NewAtomic1!Pass",
                "confirmPassword": "NewAtomic1!Pass",
            },
            format="json",
        )
        assert success.status_code == 200

        code_obj.refresh_from_db()
        assert code_obj.used_at is not None

    def test_AUTH_CN_10(self, api_client):
        """AUTH-CN-10: reset request generates REQ-... token, not a reset code."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="cn10-teacher", email="cn10-teacher@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "cn10-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        payload = req.json()
        assert payload["requestToken"].startswith("REQ-")
        assert "resetCode" not in payload

    def test_AUTH_UC_06(self, api_client, researcher_user):
        """Domain aggregator: status lookup returns correct status through lifecycle."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="uc06-teacher", email="uc06-teacher@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc06-teacher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        request_token = req.json()["requestToken"]
        request_id = req.json()["requestId"]

        # Pending
        pending = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": "uc06-teacher@example.com", "requestToken": request_token},
            format="json",
        )
        assert pending.status_code == 200
        assert pending.json()["status"] == PasswordResetRequestStatus.PENDING

        # Approve
        api_client.force_authenticate(user=researcher_user)
        api_client.patch(
            f"/api/v1/auth/reset-requests/{request_id}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        api_client.force_authenticate(user=None)

        # Approved — should include next step hint
        approved = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": "uc06-teacher@example.com", "requestToken": request_token},
            format="json",
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == PasswordResetRequestStatus.APPROVED
        assert approved.json()["next"] == "ENTER_RESET_CODE"

    def test_AUTH_UC_06_RESEARCHER(self, api_client):
        """Researcher can look up own reset request status."""
        self._create_non_student_for_reset(
            role=Role.RESEARCHER,
            username="uc06-researcher",
            email="uc06-researcher@example.com",
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc06-researcher@example.com"},
            format="json",
        )
        assert req.status_code == 201
        token = req.json()["requestToken"]

        status_response = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": "uc06-researcher@example.com", "requestToken": token},
            format="json",
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == PasswordResetRequestStatus.PENDING

    def test_AUTH_UC_06_TEACHER(self, api_client):
        """Teacher can look up own reset request status."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="uc06-teacher2", email="uc06-teacher2@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc06-teacher2@example.com"},
            format="json",
        )
        assert req.status_code == 201
        token = req.json()["requestToken"]

        status_response = api_client.post(
            "/api/v1/auth/reset-request-lookups",
            {"identifier": "uc06-teacher2@example.com", "requestToken": token},
            format="json",
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == PasswordResetRequestStatus.PENDING

    def test_AUTH_UC_07(self, api_client, admin_user, researcher_user, teacher_user):
        """Domain aggregator: all AUTH-UC-07 approval paths (admin, researcher, teacher-initiated)."""
        # 1. Researcher approves teacher request
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="uc07-t1", email="uc07-t1@example.com"
        )
        req1 = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc07-t1@example.com"},
            format="json",
        )
        assert req1.status_code == 201
        api_client.force_authenticate(user=researcher_user)
        a1 = api_client.patch(
            f"/api/v1/auth/reset-requests/{req1.json()['requestId']}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert a1.status_code == 200
        assert a1.json()["resetCode"].startswith("RESET-")

        # 2. Admin approves researcher request
        self._create_non_student_for_reset(
            role=Role.RESEARCHER, username="uc07-r2", email="uc07-r2@example.com"
        )
        api_client.force_authenticate(user=None)
        req2 = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc07-r2@example.com"},
            format="json",
        )
        assert req2.status_code == 201
        api_client.force_authenticate(user=admin_user)
        a2 = api_client.patch(
            f"/api/v1/auth/reset-requests/{req2.json()['requestId']}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert a2.status_code == 200

        # 3. Teacher-initiated student reset
        self._student_code(teacher_user, code="UC07-STUDENT", course_name="UC07 Course")
        api_client.force_authenticate(user=None)
        reg = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "UC07-STUDENT",
                "name": "UC07 Student",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert reg.status_code == 200
        student = User.objects.get(username=reg.json()["username"])
        course_id = student.student_profile.enrollments.first().course_id

        api_client.force_authenticate(user=teacher_user)
        issue = api_client.post(
            f"/api/v1/courses/{course_id}/students/{student.id}/reset-code",
            {},
            format="json",
        )
        assert issue.status_code == 200
        assert issue.json()["resetCode"].startswith("RESET-")

    def test_AUTH_UC_07_ADMIN(self, api_client, admin_user):
        """Admin can approve any role's reset request."""
        self._create_non_student_for_reset(
            role=Role.TEACHER, username="uc07-admin-t", email="uc07-admin-t@example.com"
        )
        req = api_client.post(
            "/api/v1/auth/reset-requests",
            {"identifier": "uc07-admin-t@example.com"},
            format="json",
        )
        assert req.status_code == 201

        api_client.force_authenticate(user=admin_user)
        approve = api_client.patch(
            f"/api/v1/auth/reset-requests/{req.json()['requestId']}",
            {"status": PasswordResetRequestStatus.APPROVED},
            format="json",
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == PasswordResetRequestStatus.APPROVED
        assert approve.json()["resetCode"].startswith("RESET-")

    def test_AUTH_UC_07_TEACHER(self, api_client, teacher_user):
        """Teacher generates reset code for student enrolled in their course."""
        self._student_code(teacher_user, code="UC07-T-STU", course_name="Teacher Reset Course")
        reg = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "UC07-T-STU",
                "name": "Teacher Reset Student",
                "password": "StartPass123!",
            },
            format="json",
        )
        assert reg.status_code == 200
        student = User.objects.get(username=reg.json()["username"])
        course_id = student.student_profile.enrollments.first().course_id

        api_client.force_authenticate(user=teacher_user)
        issue = api_client.post(
            f"/api/v1/courses/{course_id}/students/{student.id}/reset-code",
            {},
            format="json",
        )
        assert issue.status_code == 200
        payload = issue.json()
        assert payload["studentUserId"] == student.id
        assert payload["courseId"] == course_id
        assert payload["resetCode"].startswith("RESET-")
        assert "expiresAt" in payload
