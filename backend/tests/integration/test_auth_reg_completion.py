"""Spec completion tests for remaining FR-01/FR-02 backend IDs."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import (
    PasswordResetCode,
    PasswordResetRequest,
    PasswordResetRequestStatus,
    RegistrationCode,
    RegistrationCodeType,
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from accounts.services import (
    LOGIN_RATE_LIMIT_ATTEMPTS,
    cleanup_temporary_reset_codes,
    registration_code_hash,
    registration_code_prefix,
)
from courses.models import Course, Enrollment, EnrollmentStatus


@pytest.mark.django_db
class TestAuthRegCompletion:
    def _make_user(
        self,
        *,
        role: str,
        username: str,
        email: str | None = None,
        password: str = "StartPass123!",
    ) -> User:
        """Create a user for the requested role, including role profile wiring."""
        user = User.objects.create_user(
            username=username,
            email=email,
            name=f"{role} User",
            password=password,
        )
        if role == "ADMIN":
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            return user
        UserRole.objects.create(user=user, role=role)
        if role == Role.RESEARCHER:
            ResearcherProfile.objects.create(user=user)
        elif role == Role.TEACHER:
            TeacherProfile.objects.create(user=user)
        elif role == Role.STUDENT:
            creator = User.objects.create_user(
                username=f"{username}-creator@example.com",
                email=f"{username}-creator@example.com",
                name="Student Creator",
                password="StartPass123!",
                is_staff=True,
            )
            StudentProfile.objects.create(user=user, created_by=creator, consent=False)
        return user

    def _student_code(
        self, teacher_user: User, code: str, *, max_uses: int = 5
    ) -> RegistrationCode:
        """Create a teacher-owned student registration code bound to a course."""
        course = Course.objects.create(
            name=f"Course-{code}",
            teacher_profile=teacher_user.teacher_profile,
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

    def _non_student_code(self, creator: User, *, code: str, code_type: str) -> RegistrationCode:
        """Create a researcher/teacher invite code."""
        return RegistrationCode.objects.create(
            code_hash=registration_code_hash(code),
            code_prefix=registration_code_prefix(code),
            code_type=code_type,
            created_by=creator,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

    def _login(self, api_client, *, identifier: str, password: str):
        """Perform password login and return response."""
        return api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": identifier, "password": password},
            format="json",
        )

    @staticmethod
    def _assert_auth_cookies(response) -> None:
        """Assert HttpOnly auth cookies are set on a response."""
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"]["httponly"]
        assert response.cookies["refresh_token"]["httponly"]

    @staticmethod
    def _refresh_cookie_value(response) -> str:
        """Return refresh token value from response cookies."""
        return response.cookies["refresh_token"].value

    @staticmethod
    def _access_cookie_value(response) -> str:
        """Return access token value from response cookies."""
        return response.cookies["access_token"].value

    def _oauth_login(self, api_client, monkeypatch, *, subject: str, email: str):
        """Perform OAuth login with mocked Google userinfo response."""
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {"sub": subject, "email": email},
        )
        return api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "valid-token"},
            format="json",
        )

    # AUTH-UC-01 / AUTH-CN-04 remaining tests
    def test_AUTH_UC_01a_ADMIN(self, api_client):
        """Admin can authenticate into Django admin portal."""
        admin = self._make_user(
            role="ADMIN",
            username="uc01a-admin@example.com",
            email="uc01a-admin@example.com",
        )
        assert api_client.login(username=admin.username, password="StartPass123!")
        response = api_client.get("/admin/")
        assert response.status_code == 200

    def test_AUTH_UC_01_E2(self, api_client):
        """Login is rate limited after too many failed attempts for one identifier."""
        self._make_user(
            role=Role.TEACHER,
            username="uc01e2-teacher",
            email="uc01e2-teacher@example.com",
        )
        for _ in range(LOGIN_RATE_LIMIT_ATTEMPTS):
            response = self._login(
                api_client,
                identifier="uc01e2-teacher@example.com",
                password="WrongPass123!",
            )
            assert response.status_code == 401

        blocked = self._login(
            api_client,
            identifier="uc01e2-teacher@example.com",
            password="WrongPass123!",
        )
        assert blocked.status_code == 429
        assert "Too many failed attempts" in blocked.json()["detail"]

    def test_AUTH_UC_01_E3(self, api_client):
        """Disabled account login returns generic auth failure."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc01e3-teacher",
            email="uc01e3-teacher@example.com",
        )
        teacher.is_active = False
        teacher.save(update_fields=["is_active"])

        response = self._login(
            api_client,
            identifier="uc01e3-teacher@example.com",
            password="StartPass123!",
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid identifier or password."

    def test_AUTH_CN_04(self, api_client):
        """Login error messaging is consistent across missing and wrong-credential cases."""
        self._make_user(
            role=Role.TEACHER,
            username="cn04-teacher",
            email="cn04-teacher@example.com",
        )
        missing = self._login(
            api_client,
            identifier="cn04-missing@example.com",
            password="WrongPass123!",
        )
        wrong = self._login(
            api_client,
            identifier="cn04-teacher@example.com",
            password="WrongPass123!",
        )
        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert missing.json()["detail"] == wrong.json()["detail"]

    # AUTH-UC-02 remaining tests
    def test_AUTH_UC_02(self, api_client, monkeypatch):
        """Domain aggregator: OAuth login succeeds for non-admin roles; admin is blocked."""
        admin = self._make_user(
            role="ADMIN",
            username="uc02-admin@example.com",
            email="uc02-admin@example.com",
        )
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc02-researcher",
            email="uc02-researcher@example.com",
        )
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc02-teacher",
            email="uc02-teacher@example.com",
        )

        # Admin OAuth blocked
        admin_response = self._oauth_login(
            api_client, monkeypatch, subject="uc02-sub-admin", email=admin.email
        )
        assert admin_response.status_code == 403

        # Non-admin roles succeed
        for subject, email in [
            ("uc02-sub-researcher", researcher.email),
            ("uc02-sub-teacher", teacher.email),
        ]:
            response = self._oauth_login(api_client, monkeypatch, subject=subject, email=email)
            assert response.status_code == 200
            self._assert_auth_cookies(response)

    def test_AUTH_UC_02_ADMIN(self, api_client, monkeypatch):
        """Admin OAuth login is blocked with 403."""
        admin = self._make_user(
            role="ADMIN",
            username="uc02-admin-role@example.com",
            email="uc02-admin-role@example.com",
        )
        response = self._oauth_login(
            api_client,
            monkeypatch,
            subject="uc02-admin-role-sub",
            email=admin.email,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin accounts must use Django admin."

    def test_AUTH_UC_02_RESEARCHER(self, api_client, monkeypatch):
        """Researcher account can authenticate via OAuth."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc02-researcher-role",
            email="uc02-researcher-role@example.com",
        )
        response = self._oauth_login(
            api_client,
            monkeypatch,
            subject="uc02-researcher-role-sub",
            email=researcher.email,
        )
        assert response.status_code == 200
        assert response.json()["role"] == Role.RESEARCHER

    def test_AUTH_UC_02_TEACHER(self, api_client, monkeypatch):
        """Teacher account can authenticate via OAuth."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc02-teacher-role",
            email="uc02-teacher-role@example.com",
        )
        response = self._oauth_login(
            api_client,
            monkeypatch,
            subject="uc02-teacher-role-sub",
            email=teacher.email,
        )
        assert response.status_code == 200
        assert response.json()["role"] == Role.TEACHER

    def test_AUTH_UC_02_E2(self, api_client, monkeypatch):
        """OAuth login rejects identities without an eligible pre-created account."""
        response = self._oauth_login(
            api_client,
            monkeypatch,
            subject="uc02-e2-sub",
            email="uc02-e2-missing@example.com",
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid identifier or password."

    # AUTH-UC-03 / AUTH-CN-02 remaining tests
    def test_AUTH_UC_03_ADMIN(self, api_client):
        """Admin password login is blocked; cannot obtain tokens to refresh."""
        admin = self._make_user(
            role="ADMIN",
            username="uc03-admin@example.com",
            email="uc03-admin@example.com",
        )
        login = self._login(
            api_client,
            identifier=admin.email,
            password="StartPass123!",
        )
        assert login.status_code == 403
        assert login.json()["detail"] == "Admin accounts must use Django admin."

    def test_AUTH_UC_03_RESEARCHER(self, api_client):
        """Researcher can refresh an access token using a valid refresh token."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc03-researcher",
            email="uc03-researcher@example.com",
        )
        login = self._login(
            api_client,
            identifier=researcher.email,
            password="StartPass123!",
        )
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        refresh = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": self._refresh_cookie_value(login)},
            format="json",
        )
        assert refresh.status_code == 200

    def test_AUTH_UC_03_TEACHER(self, api_client):
        """Teacher can refresh an access token using a valid refresh token."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc03-teacher",
            email="uc03-teacher@example.com",
        )
        login = self._login(
            api_client,
            identifier=teacher.email,
            password="StartPass123!",
        )
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        refresh = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": self._refresh_cookie_value(login)},
            format="json",
        )
        assert refresh.status_code == 200

    def test_AUTH_UC_03_STUDENT(self, api_client):
        """Student can refresh an access token using a valid refresh token."""
        student = self._make_user(
            role=Role.STUDENT,
            username="uc03-student",
            email="uc03-student@example.com",
        )
        login = self._login(
            api_client,
            identifier=student.username,
            password="StartPass123!",
        )
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        refresh = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": self._refresh_cookie_value(login)},
            format="json",
        )
        assert refresh.status_code == 200

    def test_AUTH_CN_02(self, api_client):
        """Issued JWTs follow configured access and refresh token lifetimes."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="cn02-teacher",
            email="cn02-teacher@example.com",
        )
        login = self._login(
            api_client,
            identifier=teacher.email,
            password="StartPass123!",
        )
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        access = AccessToken(self._access_cookie_value(login))
        refresh = RefreshToken(self._refresh_cookie_value(login))
        access_lifetime = access["exp"] - access["iat"]
        refresh_lifetime = refresh["exp"] - refresh["iat"]
        expected_access = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        expected_refresh = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        assert abs(access_lifetime - expected_access) <= 1
        assert abs(refresh_lifetime - expected_refresh) <= 1

    # AUTH-UC-04 / AUTH-CN-01 / AUTH-CN-11 remaining tests
    def _assert_change_password_success(
        self, api_client, *, identifier: str, password: str
    ) -> None:
        """Shared role behavior for AUTH-UC-04 success path."""
        login = self._login(api_client, identifier=identifier, password=password)
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        refresh_token = self._refresh_cookie_value(login)
        user_id = login.json()["id"]
        user = User.objects.get(id=user_id)
        api_client.force_authenticate(user=user)
        change = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": password,
                "newPassword": "ChangedPass123!",
                "confirmPassword": "ChangedPass123!",
            },
            format="json",
        )
        assert change.status_code == 200
        refresh = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert refresh.status_code == 401

    def test_AUTH_UC_04_ADMIN(self, api_client):
        """Admin password login is blocked; cannot reach password change flow."""
        admin = self._make_user(
            role="ADMIN",
            username="uc04-admin@example.com",
            email="uc04-admin@example.com",
        )
        login = self._login(
            api_client,
            identifier=admin.email,
            password="StartPass123!",
        )
        assert login.status_code == 403

    def test_AUTH_UC_04_RESEARCHER(self, api_client):
        """Researcher can change password and old refresh tokens are invalidated."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc04-researcher",
            email="uc04-researcher@example.com",
        )
        self._assert_change_password_success(
            api_client,
            identifier=researcher.email,
            password="StartPass123!",
        )

    def test_AUTH_UC_04_TEACHER(self, api_client):
        """Teacher can change password and old refresh tokens are invalidated."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc04-teacher",
            email="uc04-teacher@example.com",
        )
        self._assert_change_password_success(
            api_client,
            identifier=teacher.email,
            password="StartPass123!",
        )

    def test_AUTH_UC_04_STUDENT(self, api_client):
        """Student can change password and old refresh tokens are invalidated."""
        student = self._make_user(
            role=Role.STUDENT,
            username="uc04-student",
            email="uc04-student@example.com",
        )
        self._assert_change_password_success(
            api_client,
            identifier=student.username,
            password="StartPass123!",
        )

    def test_AUTH_UC_04_E1(self, api_client):
        """Weak, mismatched, or incorrect-current values are rejected in password change."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc04-e1-teacher",
            email="uc04-e1-teacher@example.com",
        )
        api_client.force_authenticate(user=teacher)

        incorrect_current = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "WrongPass123!",
                "newPassword": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert incorrect_current.status_code == 400

        mismatch = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "StartPass123!",
                "newPassword": "ValidPass123!",
                "confirmPassword": "Different123!",
            },
            format="json",
        )
        assert mismatch.status_code == 400

        weak = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "StartPass123!",
                "newPassword": "weak",
                "confirmPassword": "weak",
            },
            format="json",
        )
        assert weak.status_code == 400

    def test_AUTH_UC_04_E2(self, api_client):
        """Password change rejects a new password identical to the current password."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc04-e2-teacher",
            email="uc04-e2-teacher@example.com",
        )
        api_client.force_authenticate(user=teacher)
        response = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "StartPass123!",
                "newPassword": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "different from current password" in response.json()["detail"]

    def test_AUTH_CN_01(self, api_client):
        """Password strength policy is enforced on self-service password change."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="cn01-teacher",
            email="cn01-teacher@example.com",
        )
        api_client.force_authenticate(user=teacher)
        weak = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "StartPass123!",
                "newPassword": "short",
                "confirmPassword": "short",
            },
            format="json",
        )
        assert weak.status_code == 400
        assert "at least 8 characters" in weak.json()["detail"]

    def test_AUTH_CN_11(self, api_client):
        """Password changes invalidate all active refresh tokens for the user."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="cn11-teacher",
            email="cn11-teacher@example.com",
        )
        first = self._login(
            api_client,
            identifier=teacher.email,
            password="StartPass123!",
        )
        second = self._login(
            api_client,
            identifier=teacher.email,
            password="StartPass123!",
        )
        assert first.status_code == 200
        assert second.status_code == 200
        self._assert_auth_cookies(first)
        self._assert_auth_cookies(second)
        refresh_1 = self._refresh_cookie_value(first)
        refresh_2 = self._refresh_cookie_value(second)

        api_client.force_authenticate(user=teacher)
        change = api_client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "StartPass123!",
                "newPassword": "Cn11NewPass1!",
                "confirmPassword": "Cn11NewPass1!",
            },
            format="json",
        )
        assert change.status_code == 200

        old_1 = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_1},
            format="json",
        )
        old_2 = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_2},
            format="json",
        )
        assert old_1.status_code == 401
        assert old_2.status_code == 401

    def test_AUTH_CN_09(self, api_client):
        """Expired and used reset codes are purged by cleanup job."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="cn09-researcher",
            email="cn09-researcher@example.com",
        )
        teacher_expired = self._make_user(
            role=Role.TEACHER,
            username="cn09-expired-teacher",
            email="cn09-expired-teacher@example.com",
        )
        teacher_used = self._make_user(
            role=Role.TEACHER,
            username="cn09-used-teacher",
            email="cn09-used-teacher@example.com",
        )

        api_client.force_authenticate(user=researcher)
        issue_expired = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": teacher_expired.id},
            format="json",
        )
        issue_used = api_client.post(
            "/api/v1/auth/password-reset-codes",
            {"targetUserId": teacher_used.id},
            format="json",
        )
        assert issue_expired.status_code == 201
        assert issue_used.status_code == 201
        api_client.force_authenticate(user=None)

        expired_code = PasswordResetCode.objects.get(request_id=issue_expired.json()["requestId"])
        expired_code.expires_at = timezone.now() - timedelta(minutes=5)
        expired_code.save(update_fields=["expires_at"])

        used_complete = api_client.post(
            "/api/v1/auth/password-resets",
            {
                "identifier": teacher_used.email,
                "resetCode": issue_used.json()["resetCode"],
                "newPassword": "Cn09UsedPass1!",
                "confirmPassword": "Cn09UsedPass1!",
            },
            format="json",
        )
        assert used_complete.status_code == 200
        used_code = PasswordResetCode.objects.get(request_id=issue_used.json()["requestId"])
        assert used_code.used_at is not None

        result = cleanup_temporary_reset_codes()
        assert result["codesDeleted"] == 2
        assert not PasswordResetCode.objects.filter(id=expired_code.id).exists()
        assert not PasswordResetCode.objects.filter(id=used_code.id).exists()
        expired_request = PasswordResetRequest.objects.get(id=issue_expired.json()["requestId"])
        assert expired_request.status == PasswordResetRequestStatus.EXPIRED

    def test_AUTH_UC_06_E2(self, api_client):
        """Reset-code validation endpoint is rate-limited after repeated failed lookups."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc06e2-teacher",
            email="uc06e2-teacher@example.com",
        )
        throttled_response = None
        for _ in range(25):
            attempt = api_client.post(
                "/api/v1/auth/reset-code-validations",
                {
                    "identifier": teacher.email,
                    "resetCode": "RESET-INVALID",
                },
                format="json",
            )
            if attempt.status_code == 429:
                throttled_response = attempt
                break
            assert attempt.status_code == 400

        assert throttled_response is not None
        assert throttled_response.status_code == 429

    # AUTH-UC-08 remaining tests
    def _assert_logout_roundtrip(self, api_client, *, identifier: str, password: str) -> None:
        """Shared logout behavior for role-specific UC-08 tests."""
        login = self._login(api_client, identifier=identifier, password=password)
        assert login.status_code == 200
        self._assert_auth_cookies(login)
        refresh_token = self._refresh_cookie_value(login)
        user = User.objects.get(id=login.json()["id"])
        api_client.force_authenticate(user=user)
        logout = api_client.post(
            "/api/v1/auth/session-revocations",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert logout.status_code == 200
        invalidated = api_client.post(
            "/api/v1/auth/token-exchanges",
            {"refreshToken": refresh_token},
            format="json",
        )
        assert invalidated.status_code == 401

    def test_AUTH_UC_08(self, api_client):
        """Domain aggregator: logout invalidates sessions for non-admin roles; admin is blocked."""
        admin = self._make_user(
            role="ADMIN",
            username="uc08-admin@example.com",
            email="uc08-admin@example.com",
        )
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc08-researcher",
            email="uc08-researcher@example.com",
        )
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc08-teacher",
            email="uc08-teacher@example.com",
        )
        student = self._make_user(
            role=Role.STUDENT,
            username="uc08-student",
            email="uc08-student@example.com",
        )
        # Admin login blocked
        admin_login = self._login(api_client, identifier=admin.email, password="StartPass123!")
        assert admin_login.status_code == 403

        self._assert_logout_roundtrip(
            api_client,
            identifier=researcher.email,
            password="StartPass123!",
        )
        self._assert_logout_roundtrip(
            api_client, identifier=teacher.email, password="StartPass123!"
        )
        self._assert_logout_roundtrip(
            api_client,
            identifier=student.username,
            password="StartPass123!",
        )

    def test_AUTH_UC_08_ADMIN(self, api_client):
        """Admin password login is blocked; cannot reach logout flow."""
        admin = self._make_user(
            role="ADMIN",
            username="uc08-admin-only@example.com",
            email="uc08-admin-only@example.com",
        )
        login = self._login(api_client, identifier=admin.email, password="StartPass123!")
        assert login.status_code == 403

    def test_AUTH_UC_08_RESEARCHER(self, api_client):
        """Researcher can logout and invalidate refresh token."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="uc08-researcher-only",
            email="uc08-researcher-only@example.com",
        )
        self._assert_logout_roundtrip(
            api_client,
            identifier=researcher.email,
            password="StartPass123!",
        )

    def test_AUTH_UC_08_TEACHER(self, api_client):
        """Teacher can logout and invalidate refresh token."""
        teacher = self._make_user(
            role=Role.TEACHER,
            username="uc08-teacher-only",
            email="uc08-teacher-only@example.com",
        )
        self._assert_logout_roundtrip(
            api_client, identifier=teacher.email, password="StartPass123!"
        )

    def test_AUTH_UC_08_STUDENT(self, api_client):
        """Student can logout and invalidate refresh token."""
        student = self._make_user(
            role=Role.STUDENT,
            username="uc08-student-only",
            email="uc08-student-only@example.com",
        )
        self._assert_logout_roundtrip(
            api_client,
            identifier=student.username,
            password="StartPass123!",
        )

    # REG-UC-01 / REG-UC-01a remaining tests
    def test_REG_UC_01_E1(self, api_client):
        """Invalid invite code returns a generic invalid/expired error."""
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-UC01-E1-INVALID",
                "firstName": "Bad",
                "lastName": "Codeuser",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Invalid or expired code" in response.json()["detail"]

    def test_REG_UC_01_E2(self, api_client):
        """Duplicate non-student email identifiers are rejected."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="reg-e2-researcher",
            email="reg-e2-researcher@example.com",
        )
        self._non_student_code(
            researcher,
            code="REG-E2-TEACHER-1",
            code_type=RegistrationCodeType.TEACHER,
        )
        self._non_student_code(
            researcher,
            code="REG-E2-TEACHER-2",
            code_type=RegistrationCodeType.TEACHER,
        )
        first = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-E2-TEACHER-1",
                "firstName": "First",
                "lastName": "Teacher",
                "email": "dup-teacher@example.com",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert first.status_code == 201

        duplicate = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-E2-TEACHER-2",
                "firstName": "Second",
                "lastName": "Teacher",
                "email": "dup-teacher@example.com",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert duplicate.status_code == 400
        assert "Email already taken" in duplicate.json()["detail"]

    def test_REG_UC_01_E4(self, api_client, monkeypatch):
        """OAuth registration returns error when provider token verification fails."""
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="reg-e4-researcher",
            email="reg-e4-researcher@example.com",
        )
        self._non_student_code(
            researcher,
            code="REG-E4-TEACHER",
            code_type=RegistrationCodeType.TEACHER,
        )
        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: (_ for _ in ()).throw(Exception("oauth-failed")),
        )
        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "OAUTH",
                "code": "REG-E4-TEACHER",
                "accessToken": "bad-token",
                "firstName": "OAuth",
                "lastName": "Failure",
            },
            format="json",
        )
        assert response.status_code == 401

    def test_REG_CN_03(self, api_client, teacher_user, student_user, monkeypatch):
        """Registration and join-course redemption roll back when enrollment step fails."""
        student_code = self._student_code(teacher_user, "REG-CN03-REGISTER")

        def fail_enrollment(*_args, **_kwargs):
            raise ValueError("Enrollment creation failed")

        monkeypatch.setattr(
            "accounts.services._registration._ensure_student_enrollment", fail_enrollment
        )
        before_users = User.objects.count()
        register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN03-REGISTER",
                "firstName": "Atomic",
                "lastName": "Failurestudent",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert register.status_code == 400
        assert User.objects.count() == before_users
        student_code.refresh_from_db()
        assert student_code.times_used == 0

        join_code = self._student_code(teacher_user, "REG-CN03-JOIN")
        api_client.force_authenticate(user=student_user)
        join = api_client.post(
            "/api/v1/enrollments",
            {"code": "REG-CN03-JOIN"},
            format="json",
        )
        assert join.status_code == 400
        join_code.refresh_from_db()
        assert join_code.times_used == 0

    def test_REG_CN_13(self, api_client, teacher_user):
        """Student code registration and redemption always enroll into linked course."""
        primary_code = self._student_code(teacher_user, "REG-CN13-PRIMARY")
        register = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN13-PRIMARY",
                "firstName": "Cnthirteen",
                "lastName": "Student",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert register.status_code == 201
        student = User.objects.get(username=register.json()["username"])
        assert register.json()["courseId"] == primary_code.course_id
        assert Enrollment.objects.filter(
            course_id=primary_code.course_id,
            student_profile=student.student_profile,
            status=EnrollmentStatus.ACTIVE,
        ).exists()

        secondary_code = self._student_code(teacher_user, "REG-CN13-SECONDARY")
        api_client.force_authenticate(user=student)
        join = api_client.post(
            "/api/v1/enrollments",
            {"code": "REG-CN13-SECONDARY"},
            format="json",
        )
        assert join.status_code == 201
        assert Enrollment.objects.filter(
            course_id=secondary_code.course_id,
            student_profile=student.student_profile,
            status=EnrollmentStatus.ACTIVE,
        ).exists()

    def test_REG_UC_01a_E1(self, api_client, student_user):
        """Join-course redemption rejects invalid/expired/revoked codes."""
        api_client.force_authenticate(user=student_user)
        response = api_client.post(
            "/api/v1/enrollments",
            {"code": "REG-UC01A-E1-INVALID"},
            format="json",
        )
        assert response.status_code == 400
        assert "Invalid or expired code" in response.json()["detail"]

    # REG-UC-02 remaining tests
    def test_REG_UC_02(self, api_client):
        """Domain aggregator: admin/researcher/teacher can generate scoped code types."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-uc02-admin@example.com",
            email="reg-uc02-admin@example.com",
        )
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="reg-uc02-researcher",
            email="reg-uc02-researcher@example.com",
        )
        teacher = self._make_user(
            role=Role.TEACHER,
            username="reg-uc02-teacher",
            email="reg-uc02-teacher@example.com",
        )
        teacher_course = Course.objects.create(
            name="REG-UC02 Teacher Course", teacher_profile=teacher.teacher_profile
        )

        api_client.force_authenticate(user=admin)
        admin_create = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.RESEARCHER,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        assert admin_create.status_code == 201

        api_client.force_authenticate(user=researcher)
        researcher_create = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.TEACHER,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        assert researcher_create.status_code == 201

        api_client.force_authenticate(user=teacher)
        teacher_create = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "courseId": teacher_course.id,
            },
            format="json",
        )
        assert teacher_create.status_code == 201

    def test_REG_UC_02_ADMIN(self, api_client):
        """Admin can generate researcher registration codes."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-uc02-admin-only@example.com",
            email="reg-uc02-admin-only@example.com",
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.RESEARCHER,
                "count": 2,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["count"] == 2

    def test_REG_UC_02_RESEARCHER_WITH_PERMISSION(self, api_client):
        """Researcher with ISSUE_RESEARCHER_REG_CODE can generate researcher codes."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-uc02-admin-grant@example.com",
            email="reg-uc02-admin-grant@example.com",
        )
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="reg-uc02-researcher-granted",
            email="reg-uc02-researcher-granted@example.com",
        )
        SudoGrant.objects.create(
            user=researcher,
            granted_by=admin,
            permissions=[SudoPermission.ISSUE_RESEARCHER_REG_CODE.value],
            can_grant_sudo=False,
        )
        api_client.force_authenticate(user=researcher)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.RESEARCHER,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_REG_UC_02_E1(self, api_client, teacher_user):
        """Code generation rejects invalid count/uses-per-code values."""
        course = Course.objects.create(
            name="REG-UC02-E1", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 0,
                "usesPerCode": 0,
                "expiresAt": (timezone.now() + timedelta(days=2)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert response.status_code == 400

    def test_REG_UC_02_E2(self, api_client, teacher_user):
        """Code generation rejects missing or invalid expiration."""
        course = Course.objects.create(
            name="REG-UC02-E2", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)

        missing = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "courseId": course.id,
            },
            format="json",
        )
        assert missing.status_code == 400

        past = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() - timedelta(minutes=1)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert past.status_code == 400

    def test_REG_UC_02_E3(self, api_client, teacher_user):
        """Teacher student-code generation requires a course identifier."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 400
        assert "courseId is required" in response.json()["detail"]

    def test_REG_UC_02_E5(self, api_client, teacher_user):
        """Insufficient role permissions are rejected for code generation."""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.TEACHER,
                "count": 1,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_REG_CN_07(self, api_client, teacher_user):
        """Generation requires both count and usesPerCode fields."""
        course = Course.objects.create(
            name="REG-CN07", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)
        missing_count = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert missing_count.status_code == 400

        missing_uses = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
                "courseId": course.id,
            },
            format="json",
        )
        assert missing_uses.status_code == 400

    def test_REG_CN_11(self, api_client, researcher_user):
        """Metadata payloads are allowed only when generating exactly one code."""
        api_client.force_authenticate(user=researcher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.TEACHER,
                "count": 2,
                "usesPerCode": 1,
                "expiresAt": (timezone.now() + timedelta(days=1)).isoformat(),
                "metadata": {"district": "Wake"},
            },
            format="json",
        )
        assert response.status_code == 400
        assert "count must be 1" in str(response.json())

    def test_REG_CN_12(self, api_client, teacher_user):
        """All generated codes require explicit expiration input."""
        course = Course.objects.create(
            name="REG-CN12", teacher_profile=teacher_user.teacher_profile
        )
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/codes",
            {
                "codeType": RegistrationCodeType.STUDENT,
                "count": 1,
                "usesPerCode": 1,
                "courseId": course.id,
            },
            format="json",
        )
        assert response.status_code == 400

    # REG-UC-03 remaining tests
    def test_REG_UC_03(self, api_client):
        """Domain aggregator: scoped listing and lifecycle transitions for all managing roles."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-uc03-admin@example.com",
            email="reg-uc03-admin@example.com",
        )
        researcher = self._make_user(
            role=Role.RESEARCHER,
            username="reg-uc03-researcher",
            email="reg-uc03-researcher@example.com",
        )
        teacher = self._make_user(
            role=Role.TEACHER,
            username="reg-uc03-teacher",
            email="reg-uc03-teacher@example.com",
        )
        teacher_code = self._non_student_code(
            researcher,
            code="REG-UC03-TEACHER-CODE",
            code_type=RegistrationCodeType.TEACHER,
        )
        student_code = self._student_code(teacher, "REG-UC03-STUDENT-CODE")

        api_client.force_authenticate(user=admin)
        admin_list = api_client.get("/api/v1/codes")
        assert admin_list.status_code == 200

        api_client.force_authenticate(user=researcher)
        researcher_patch = api_client.patch(
            f"/api/v1/codes/{teacher_code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert researcher_patch.status_code == 200

        api_client.force_authenticate(user=teacher)
        teacher_patch = api_client.patch(
            f"/api/v1/codes/{student_code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert teacher_patch.status_code == 200

    def test_REG_UC_03_ADMIN(self, api_client, teacher_user):
        """Admin can view and transition any registration code."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-uc03-admin-only@example.com",
            email="reg-uc03-admin-only@example.com",
        )
        code = self._student_code(teacher_user, "REG-UC03-ADMIN")
        api_client.force_authenticate(user=admin)
        detail = api_client.get(f"/api/v1/codes/{code.id}")
        assert detail.status_code == 200
        revoke = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert revoke.status_code == 200

    def test_REG_UC_03_RESEARCHER(self, api_client, researcher_user):
        """Researcher can manage lifecycle for their own teacher codes."""
        code = self._non_student_code(
            researcher_user,
            code="REG-UC03-RESEARCHER",
            code_type=RegistrationCodeType.TEACHER,
        )
        api_client.force_authenticate(user=researcher_user)
        detail = api_client.get(f"/api/v1/codes/{code.id}")
        assert detail.status_code == 200
        revoke = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert revoke.status_code == 200

    def test_REG_UC_03_E2(self, api_client, teacher_user):
        """Invalid lifecycle transitions are rejected."""
        code = self._student_code(teacher_user, "REG-UC03-E2")
        api_client.force_authenticate(user=teacher_user)
        response = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "ARCHIVED"},
            format="json",
        )
        assert response.status_code == 409
        assert "Only EXHAUSTED, EXPIRED, or REVOKED" in response.json()["detail"]

    def test_REG_CN_04(self, api_client, teacher_user):
        """Code visibility is role-scoped, with admin global visibility."""
        admin = self._make_user(
            role="ADMIN",
            username="reg-cn04-admin@example.com",
            email="reg-cn04-admin@example.com",
        )
        researcher_a = self._make_user(
            role=Role.RESEARCHER,
            username="reg-cn04-researcher-a",
            email="reg-cn04-researcher-a@example.com",
        )
        researcher_b = self._make_user(
            role=Role.RESEARCHER,
            username="reg-cn04-researcher-b",
            email="reg-cn04-researcher-b@example.com",
        )
        code_a = self._non_student_code(
            researcher_a,
            code="REG-CN04-A",
            code_type=RegistrationCodeType.TEACHER,
        )
        code_b = self._non_student_code(
            researcher_b,
            code="REG-CN04-B",
            code_type=RegistrationCodeType.TEACHER,
        )
        teacher_code = self._student_code(teacher_user, "REG-CN04-STUDENT")

        api_client.force_authenticate(user=admin)
        admin_ids = {entry["id"] for entry in api_client.get("/api/v1/codes").json()["results"]}
        assert code_a.id in admin_ids and code_b.id in admin_ids and teacher_code.id in admin_ids

        api_client.force_authenticate(user=researcher_a)
        researcher_ids = {
            entry["id"] for entry in api_client.get("/api/v1/codes").json()["results"]
        }
        assert code_a.id in researcher_ids
        assert code_b.id not in researcher_ids
        assert teacher_code.id not in researcher_ids

        api_client.force_authenticate(user=teacher_user)
        teacher_ids = {entry["id"] for entry in api_client.get("/api/v1/codes").json()["results"]}
        assert teacher_code.id in teacher_ids
        assert code_a.id not in teacher_ids

    def test_REG_CN_05(self, api_client, teacher_user):
        """Registration code lifecycle status mapping matches ACTIVE/EXPIRED/EXHAUSTED/REVOKED/ARCHIVED."""
        active = self._student_code(teacher_user, "REG-CN05-ACTIVE")
        expired = self._student_code(teacher_user, "REG-CN05-EXPIRED")
        exhausted = self._student_code(teacher_user, "REG-CN05-EXHAUSTED")
        revoked = self._student_code(teacher_user, "REG-CN05-REVOKED")
        archived = self._student_code(teacher_user, "REG-CN05-ARCHIVED")

        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["expires_at"])
        exhausted.max_uses = 1
        exhausted.times_used = 1
        exhausted.save(update_fields=["max_uses", "times_used"])
        revoked.is_active = False
        revoked.save(update_fields=["is_active"])
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get("/api/v1/codes?includeArchived=true")
        assert response.status_code == 200
        by_id = {entry["id"]: entry for entry in response.json()["results"]}
        assert by_id[active.id]["status"] == "ACTIVE"
        assert by_id[expired.id]["status"] == "EXPIRED"
        assert by_id[exhausted.id]["status"] == "EXHAUSTED"
        assert by_id[revoked.id]["status"] == "REVOKED"
        assert by_id[archived.id]["status"] == "ARCHIVED"

    def test_REG_CN_15(self, api_client, teacher_user):
        """Revoke blocks new registrations; archive only hides code from default listings."""
        code = self._student_code(teacher_user, "REG-CN15-CODE", max_uses=2)
        first_registration = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN15-CODE",
                "firstName": "Cnfifteen",
                "lastName": "Existingstudent",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert first_registration.status_code == 201
        existing_username = first_registration.json()["username"]

        api_client.force_authenticate(user=teacher_user)
        revoke = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "REVOKED"},
            format="json",
        )
        assert revoke.status_code == 200
        assert revoke.json()["status"] == "REVOKED"

        api_client.force_authenticate(user=None)
        blocked_registration = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REG-CN15-CODE",
                "firstName": "Cnfifteen",
                "lastName": "Blockedstudent",
                "password": "StartPass123!",
                "confirmPassword": "StartPass123!",
            },
            format="json",
        )
        assert blocked_registration.status_code == 400

        existing_login = self._login(
            api_client,
            identifier=existing_username,
            password="StartPass123!",
        )
        assert existing_login.status_code == 200

        api_client.force_authenticate(user=teacher_user)
        archive = api_client.patch(
            f"/api/v1/codes/{code.id}",
            {"status": "ARCHIVED"},
            format="json",
        )
        assert archive.status_code == 200
        assert archive.json()["status"] == "ARCHIVED"

        default_list = api_client.get("/api/v1/codes")
        default_ids = {entry["id"] for entry in default_list.json()["results"]}
        assert code.id not in default_ids

        archived_list = api_client.get("/api/v1/codes?includeArchived=true")
        archived_ids = {entry["id"] for entry in archived_list.json()["results"]}
        assert code.id in archived_ids
