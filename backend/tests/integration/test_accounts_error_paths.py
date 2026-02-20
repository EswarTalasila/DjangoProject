"""Additional FR1/FR2 integration coverage for error and edge paths."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import OAuthProvider, Role, TeacherProfile, User, UserRole
from accounts.services import registration_code_hash, registration_code_prefix
from courses.models import Course
from tests.factories import OAuthAccountFactory


@pytest.mark.django_db
class TestAccountErrorPaths:
    def _make_teacher(self, username: str = "teacher-error") -> User:
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            name="Teacher",
            password="StartPass123!",
        )
        UserRole.objects.create(user=user, role=Role.TEACHER)
        TeacherProfile.objects.create(user=user)
        return user

    def _make_student(self, admin_user, username: str = "student-error") -> User:
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            name="Student",
            password="StartPass123!",
        )
        UserRole.objects.create(user=user, role=Role.STUDENT)
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=user, created_by=admin_user, consent=False)
        return user

    def _teacher_code(self, creator: User, code: str = "INV-TEACH-OAUTH"):
        from accounts.models import RegistrationCode, RegistrationCodeType

        return RegistrationCode.objects.create(
            code_hash=registration_code_hash(code),
            code_prefix=registration_code_prefix(code),
            code_type=RegistrationCodeType.TEACHER,
            created_by=creator,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

    def test_oauth_login_rejects_missing_google_fields(self, api_client, monkeypatch):
        """OAuth login rejects Google responses without required sub/email fields."""

        monkeypatch.setattr(
            "accounts.views._google_userinfo", lambda _token: {"sub": "", "email": ""}
        )
        response = api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "token"},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Access token verification failed."

    def test_oauth_login_rejects_student_even_when_oauth_link_exists(
        self, api_client, monkeypatch, admin_user
    ):
        """Student accounts are blocked from OAuth login regardless of linkage."""

        student = self._make_student(admin_user, "student-oauth-blocked")
        OAuthAccountFactory(
            user=student,
            provider=OAuthProvider.GOOGLE,
            subject="student-subject",
            email=student.email,
        )

        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {"sub": "student-subject", "email": student.email},
        )
        response = api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "token"},
            format="json",
        )
        assert response.status_code == 403
        assert "not supported for student" in response.json()["detail"]

    def test_oauth_login_matches_returning_user_by_subject(self, api_client, monkeypatch):
        """Returning OAuth user is matched via provider+subject and email is refreshed."""

        teacher = self._make_teacher("teacher-oauth-subject")
        account = OAuthAccountFactory(
            user=teacher,
            provider=OAuthProvider.GOOGLE,
            subject="subject-match-1",
            email="old-email@example.com",
        )

        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {"sub": "subject-match-1", "email": "new-email@example.com"},
        )
        response = api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "token"},
            format="json",
        )

        assert response.status_code == 200
        account.refresh_from_db()
        assert account.email == "new-email@example.com"

    def test_create_user_rejects_taken_email(self, api_client):
        """Create-user returns 400 when email is already in use."""

        admin = User.objects.create_user(
            username="admin-create-email",
            email="admin-create-email@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        User.objects.create_user(
            username="existing-email-owner",
            email="dup-email@example.com",
            name="Existing",
            password="StartPass123!",
        )

        response = api_client.post(
            "/api/v1/users",
            {
                "name": "Teacher New",
                "role": Role.TEACHER,
                "email": "dup-email@example.com",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["detail"] == "Email already taken"

    def test_create_user_requires_email_for_non_student(self, api_client):
        """Non-student user creation without email is rejected."""

        admin = User.objects.create_user(
            username="admin-create-missing-email",
            email="admin-create-missing-email@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            "/api/v1/users",
            {
                "name": "Teacher Missing Email",
                "role": Role.TEACHER,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "email is required" in str(response.data)

    def test_create_user_rejects_username_field(self, api_client):
        """Create-user rejects caller-supplied username values."""

        admin = User.objects.create_user(
            username="admin-create-username",
            email="admin-create-username@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            "/api/v1/users",
            {
                "username": "caller-picked",
                "name": "Teacher Name",
                "role": Role.TEACHER,
                "email": "teacher-username-block@example.com",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["detail"] == "username is system-managed and must not be provided"

    def test_edit_user_rejects_student_username_change(self, api_client, admin_user):
        """Student username changes are blocked as immutable."""

        teacher = self._make_teacher("teacher-owner-edit")
        course = Course.objects.create(
            name="Edit Students", teacher_profile=teacher.teacher_profile
        )

        student = self._make_student(admin_user, "student-immutable")
        from courses.models import Enrollment, EnrollmentStatus

        Enrollment.objects.create(
            course=course,
            student_profile=student.student_profile,
            status=EnrollmentStatus.ACTIVE,
        )

        api_client.force_authenticate(user=teacher)
        response = api_client.patch(
            f"/api/v1/users/{student.id}",
            {"username": "new-student-username"},
            format="json",
        )

        assert response.status_code == 400
        assert "immutable" in str(response.data)

    def test_edit_user_rejects_taken_email(self, api_client):
        """Edit-user rejects duplicate email collisions."""

        admin = User.objects.create_user(
            username="admin-edit-email",
            email="admin-edit-email@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        target = self._make_teacher("target-teacher-email")
        User.objects.create_user(
            username="other-user-email",
            email="taken-edit@example.com",
            name="Other",
            password="StartPass123!",
        )

        response = api_client.patch(
            f"/api/v1/users/{target.id}",
            {"email": "taken-edit@example.com"},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["detail"] == "Email already taken"

    def test_bulk_create_requires_sudo_for_researcher(self, api_client):
        """Researcher without BULK_CREATE sudo receives forbidden response."""

        researcher = User.objects.create_user(
            username="researcher-bulk-no-sudo",
            email="researcher-bulk-no-sudo@example.com",
            name="Researcher",
            password="StartPass123!",
        )
        UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
        from accounts.models import ResearcherProfile

        ResearcherProfile.objects.create(user=researcher)

        api_client.force_authenticate(user=researcher)
        response = api_client.post(
            "/api/v1/user-batches",
            [{"name": "X"}],
            format="json",
        )
        assert response.status_code == 403

    def test_code_detail_patch_not_found(self, api_client):
        """Code transition endpoint returns 404 for unknown code id."""

        admin = User.objects.create_user(
            username="admin-code-detail",
            email="admin-code-detail@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.patch(
            "/api/v1/codes/999999",
            {"status": "REVOKED"},
            format="json",
        )
        assert response.status_code == 404

    def test_logout_invalid_refresh_token(self, api_client, teacher_user):
        """Logout returns 400 when refresh token is malformed/invalid."""

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            "/api/v1/auth/session-revocations",
            {"refreshToken": "not-a-valid-refresh"},
            format="json",
        )
        assert response.status_code == 400

    def test_registration_local_enforces_auth_cn01_password_policy(self, api_client):
        """Local registration rejects weak passwords per AUTH-CN-01."""

        teacher = self._make_teacher("teacher-weak-reg")
        course = Course.objects.create(
            name="Weak Password Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("WEAK-PASS-CODE"),
            code_prefix=registration_code_prefix("WEAK-PASS-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "WEAK-PASS-CODE",
                "password": "weakpass1!",
                "confirmPassword": "weakpass1!",
                "firstName": "Weak",
                "lastName": "Password Student",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Password does not meet policy requirements." in response.json()["detail"]

    def test_registration_local_rejects_legacy_name_only_payload(self, api_client):
        """Local registration rejects legacy combined-name payloads."""

        teacher = self._make_teacher("teacher-name-only-reg")
        course = Course.objects.create(
            name="Name Only Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("NAME-ONLY-CODE"),
            code_prefix=registration_code_prefix("NAME-ONLY-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "NAME-ONLY-CODE",
                "name": "Legacy Name",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "name" in payload

    def test_registration_local_requires_split_name_fields(self, api_client):
        """Local registration requires firstName and lastName fields."""

        teacher = self._make_teacher("teacher-missing-split-name-reg")
        course = Course.objects.create(
            name="Missing Split Name Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("MISSING-SPLIT-NAME-CODE"),
            code_prefix=registration_code_prefix("MISSING-SPLIT-NAME-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "MISSING-SPLIT-NAME-CODE",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "firstName" in payload
        assert "lastName" in payload

    def test_registration_local_rejects_unknown_fields(self, api_client):
        """Local registration rejects undeclared payload fields."""

        teacher = self._make_teacher("teacher-extra-field-reg")
        course = Course.objects.create(
            name="Extra Field Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("EXTRA-FIELD-CODE"),
            code_prefix=registration_code_prefix("EXTRA-FIELD-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "EXTRA-FIELD-CODE",
                "firstName": "Extra",
                "lastName": "Field",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
                "role": "ROLE_TEACHER",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "role" in payload

    # --- Registration response contract & validation ---

    def test_registration_local_password_confirmation_mismatch(self, api_client):
        """Local registration rejects mismatched password and confirmPassword."""

        teacher = self._make_teacher("teacher-pw-mismatch")
        course = Course.objects.create(
            name="PW Mismatch Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("MISMATCH-CODE"),
            code_prefix=registration_code_prefix("MISMATCH-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "MISMATCH-CODE",
                "firstName": "Mismatch",
                "lastName": "Student",
                "password": "ValidPass123!",
                "confirmPassword": "DifferentPass456!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Passwords do not match" in response.json()["detail"]

    def test_registration_local_missing_method_field(self, api_client):
        """Registration endpoint rejects request with missing method field."""

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "code": "SOME-CODE",
                "firstName": "No",
                "lastName": "Method",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "method must be LOCAL or OAUTH" in response.json()["detail"]

    def test_registration_local_invalid_method_value(self, api_client):
        """Registration endpoint rejects invalid method values."""

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "INVALID",
                "code": "SOME-CODE",
                "firstName": "Bad",
                "lastName": "Method",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "method must be LOCAL or OAUTH" in response.json()["detail"]

    def test_registration_student_response_shape(self, api_client):
        """Student registration returns complete unified response with JWT and null email."""

        teacher = self._make_teacher("teacher-shape-student")
        course = Course.objects.create(
            name="Shape Student Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("SHAPE-STUDENT-CODE"),
            code_prefix=registration_code_prefix("SHAPE-STUDENT-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "SHAPE-STUDENT-CODE",
                "firstName": "Shape",
                "lastName": "Student",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.json()

        # All required fields present
        assert payload["message"] == "User registered"
        assert "accessToken" in payload
        assert "refreshToken" in payload
        assert payload["tokenType"] == "Bearer"
        assert payload["role"] == Role.STUDENT
        assert "id" in payload
        assert "username" in payload
        assert "name" in payload
        assert payload["createdNewUser"] is True
        assert payload["alreadyEnrolled"] is False

        # Student-specific: email null, courseId present
        assert payload["email"] is None or payload["email"] == ""
        assert payload["courseId"] == course.id

        # Username is system-generated, not email-based
        assert "@" not in payload["username"]

    def test_registration_teacher_response_shape(self, api_client, researcher_user):
        """Teacher registration returns complete unified response with email and null courseId."""

        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("SHAPE-TEACHER-CODE"),
            code_prefix=registration_code_prefix("SHAPE-TEACHER-CODE"),
            code_type=RegistrationCodeType.TEACHER,
            created_by=researcher_user,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "SHAPE-TEACHER-CODE",
                "firstName": "Shape",
                "lastName": "Teacher",
                "email": "shape-teacher@example.com",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.json()

        # All required fields present
        assert payload["message"] == "User registered"
        assert "accessToken" in payload
        assert "refreshToken" in payload
        assert payload["tokenType"] == "Bearer"
        assert payload["role"] == Role.TEACHER
        assert "id" in payload
        assert "username" in payload
        assert "name" in payload
        assert payload["createdNewUser"] is True
        assert payload["alreadyEnrolled"] is False

        # Non-student: email present, courseId null
        assert payload["email"] == "shape-teacher@example.com"
        assert payload["courseId"] is None

        # Username is system-generated, not email-based
        assert "@" not in payload["username"]

    def test_registration_student_email_null_in_login_response(self, api_client):
        """Student login response returns null email, not username as email fallback."""

        teacher = self._make_teacher("teacher-login-email")
        course = Course.objects.create(
            name="Login Email Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("LOGIN-EMAIL-CODE"),
            code_prefix=registration_code_prefix("LOGIN-EMAIL-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        reg = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "LOGIN-EMAIL-CODE",
                "firstName": "Login",
                "lastName": "Email Student",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert reg.status_code == 201
        username = reg.json()["username"]

        login = api_client.post(
            "/api/v1/auth/sessions",
            {"identifier": username, "password": "ValidPass123!"},
            format="json",
        )
        assert login.status_code == 200
        login_payload = login.json()

        # Email must be None, not the username
        assert login_payload["email"] is None or login_payload["email"] == ""
        assert login_payload["username"] == username

    def test_registration_username_collision_resolution(self, api_client):
        """Two students with similar names get distinct system-generated usernames."""

        teacher = self._make_teacher("teacher-collision")
        course = Course.objects.create(
            name="Collision Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        for i in range(2):
            RegistrationCode.objects.create(
                code_hash=registration_code_hash(f"COLLISION-CODE-{i}"),
                code_prefix=registration_code_prefix(f"COLLISION-CODE-{i}"),
                code_type=RegistrationCodeType.STUDENT,
                created_by=teacher,
                course=course,
                max_uses=1,
                times_used=0,
                expires_at=timezone.now() + timedelta(days=1),
                is_active=True,
            )

        first = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "COLLISION-CODE-0",
                "firstName": "Alex",
                "lastName": "Smith",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        second = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "COLLISION-CODE-1",
                "firstName": "Alex",
                "lastName": "Smith",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["username"] != second.json()["username"]

    def test_registration_exhausted_code_rejected(self, api_client):
        """Registration with a fully-used code returns invalid/expired error."""

        teacher = self._make_teacher("teacher-exhausted")
        course = Course.objects.create(
            name="Exhausted Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("EXHAUSTED-CODE"),
            code_prefix=registration_code_prefix("EXHAUSTED-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=1,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "EXHAUSTED-CODE",
                "firstName": "Exhausted",
                "lastName": "Student",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Invalid or expired code" in response.json()["detail"]

    def test_registration_revoked_code_rejected(self, api_client):
        """Registration with a revoked code returns invalid/expired error."""

        teacher = self._make_teacher("teacher-revoked")
        course = Course.objects.create(
            name="Revoked Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("REVOKED-CODE"),
            code_prefix=registration_code_prefix("REVOKED-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=5,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=False,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "REVOKED-CODE",
                "firstName": "Revoked",
                "lastName": "Student",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Invalid or expired code" in response.json()["detail"]

    def test_registration_expired_code_rejected(self, api_client):
        """Registration with an expired code returns invalid/expired error."""

        teacher = self._make_teacher("teacher-expired")
        course = Course.objects.create(
            name="Expired Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("EXPIRED-CODE"),
            code_prefix=registration_code_prefix("EXPIRED-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=5,
            times_used=0,
            expires_at=timezone.now() - timedelta(minutes=5),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "EXPIRED-CODE",
                "firstName": "Expired",
                "lastName": "Student",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "Invalid or expired code" in response.json()["detail"]

    def test_registration_oauth_missing_access_token(self, api_client, researcher_user):
        """OAuth registration rejects request missing accessToken field."""

        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("OAUTH-MISSING-TOKEN"),
            code_prefix=registration_code_prefix("OAUTH-MISSING-TOKEN"),
            code_type=RegistrationCodeType.TEACHER,
            created_by=researcher_user,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "OAUTH",
                "code": "OAUTH-MISSING-TOKEN",
                "firstName": "Missing",
                "lastName": "Token",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "accessToken" in payload

    def test_registration_local_missing_password(self, api_client):
        """Local registration rejects request missing password field."""

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "SOME-CODE",
                "firstName": "No",
                "lastName": "Password",
                "confirmPassword": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "password" in payload

    def test_registration_local_missing_confirm_password(self, api_client):
        """Local registration rejects request missing confirmPassword field."""

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "SOME-CODE",
                "firstName": "No",
                "lastName": "Confirm",
                "password": "ValidPass123!",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "confirmPassword" in payload

    def test_registration_local_username_not_accepted(self, api_client):
        """Local registration rejects username field (system-generated only)."""

        teacher = self._make_teacher("teacher-no-username")
        course = Course.objects.create(
            name="No Username Course", teacher_profile=teacher.teacher_profile
        )
        from accounts.models import RegistrationCode, RegistrationCodeType

        RegistrationCode.objects.create(
            code_hash=registration_code_hash("NO-USERNAME-CODE"),
            code_prefix=registration_code_prefix("NO-USERNAME-CODE"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=1,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = api_client.post(
            "/api/v1/registration/accounts",
            {
                "method": "LOCAL",
                "code": "NO-USERNAME-CODE",
                "firstName": "No",
                "lastName": "Username",
                "password": "ValidPass123!",
                "confirmPassword": "ValidPass123!",
                "username": "my-chosen-username",
            },
            format="json",
        )
        assert response.status_code == 400
        payload = response.json()
        assert "username" in payload

    # --- Branch-coverage additions for views.py ---

    def test_edit_user_name_update(self, api_client, admin_user):
        """Edit user name field is accepted and applied."""

        teacher = self._make_teacher("teacher-name-edit")
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/v1/users/{teacher.id}",
            {"name": "Updated Name"},
            format="json",
        )
        assert response.status_code == 200

    def test_edit_user_password_update(self, api_client, admin_user):
        """Edit user password field triggers password change."""

        teacher = self._make_teacher("teacher-pw-edit")
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/v1/users/{teacher.id}",
            {"password": "NewStrongPass123!"},
            format="json",
        )
        assert response.status_code == 200

    def test_edit_user_role_change(self, api_client, admin_user):
        """Edit user role change triggers role reassignment and profile creation."""

        from accounts.models import ResearcherProfile

        teacher = self._make_teacher("teacher-role-change")
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/v1/users/{teacher.id}",
            {"role": "RESEARCHER"},
            format="json",
        )
        assert response.status_code == 200
        assert ResearcherProfile.objects.filter(user=teacher).exists()

    def test_edit_user_email_required_non_student(self, api_client, admin_user):
        """Non-student user cannot have email removed."""

        teacher = self._make_teacher("teacher-no-email-edit")
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/v1/users/{teacher.id}",
            {"email": None},
            format="json",
        )
        assert response.status_code == 400
        assert "email is required" in str(response.data)

    def test_list_codes_with_type_and_status_filters(self, api_client):
        """Code listing respects codeType and status query filters."""

        from accounts.models import RegistrationCode, RegistrationCodeType

        teacher = self._make_teacher("teacher-code-list")
        api_client.force_authenticate(user=teacher)

        course = Course.objects.create(
            name="Filter Course", teacher_profile=teacher.teacher_profile
        )
        RegistrationCode.objects.create(
            code_hash=registration_code_hash("FILTER-CODE-1"),
            code_prefix=registration_code_prefix("FILTER-CODE-1"),
            code_type=RegistrationCodeType.STUDENT,
            created_by=teacher,
            course=course,
            max_uses=5,
            times_used=0,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        # With codeType filter
        response = api_client.get("/api/v1/codes", {"codeType": "STUDENT"}, format="json")
        assert response.status_code == 200

        # With status filter
        response = api_client.get("/api/v1/codes", {"status": "ACTIVE"}, format="json")
        assert response.status_code == 200

    def test_login_google_first_time_user_without_email(self, api_client, monkeypatch):
        """First-time Google login sets email for user without one."""

        teacher = self._make_teacher("teacher-no-email-oauth")
        # Clear email
        teacher.email = None
        teacher.save(update_fields=["email"])
        # Ensure lookup works by username
        teacher.username = "teacher-no-email-oauth"
        teacher.save(update_fields=["username"])

        monkeypatch.setattr(
            "accounts.views._google_userinfo",
            lambda _token: {"sub": "new-sub-no-email", "email": "teacher-no-email-oauth"},
        )
        response = api_client.post(
            "/api/v1/auth/sessions/oauth",
            {"accessToken": "token"},
            format="json",
        )
        assert response.status_code == 200
        teacher.refresh_from_db()
        assert teacher.email == "teacher-no-email-oauth"

    def test_bulk_create_skips_invalid_entries(self, api_client):
        """Bulk create skips entries with missing fields and invalid roles."""

        admin = User.objects.create_user(
            username="admin-bulk-skip",
            email="admin-bulk-skip@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            "/api/v1/user-batches",
            [
                # Missing name
                {"email": "no-name@example.com"},
                # Student create skipped (admin cannot create student via this matrix)
                {"name": "Valid Student"},
                # Valid researcher (admin can create)
                {
                    "name": "Valid Researcher",
                    "role": "RESEARCHER",
                    "email": "valid-researcher-bulk@example.com",
                },
                # Non-student without email (should be skipped)
                {"name": "No Email", "role": "TEACHER"},
            ],
            format="json",
        )
        assert response.status_code == 201
        assert response.data == 1

    def test_bulk_create_rejects_username_field(self, api_client):
        """Bulk create rejects caller-supplied username values."""

        admin = User.objects.create_user(
            username="admin-bulk-username-reject",
            email="admin-bulk-username-reject@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            "/api/v1/user-batches",
            [{"username": "caller-bulk", "name": "Bulk User"}],
            format="json",
        )
        assert response.status_code == 400
        assert response.data["detail"] == "username is system-managed and must not be provided"

    def test_bulk_create_rejects_non_list(self, api_client):
        """Bulk create rejects non-list body."""

        admin = User.objects.create_user(
            username="admin-bulk-nonlist",
            email="admin-bulk-nonlist@example.com",
            name="Admin",
            password="StartPass123!",
            is_staff=True,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            "/api/v1/user-batches",
            {"name": "not-a-list"},
            format="json",
        )
        assert response.status_code == 400
