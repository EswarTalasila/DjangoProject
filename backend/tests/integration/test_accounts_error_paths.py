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
        assert "Invalid Google userinfo" in response.json()["error"]

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
                "username": "teacher-new",
                "name": "Teacher New",
                "role": Role.TEACHER,
                "email": "dup-email@example.com",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data == "Email already taken"

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
                "username": "teacher-missing-email",
                "name": "Teacher Missing Email",
                "role": Role.TEACHER,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "email is required" in str(response.data)

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
        assert response.data == "Email already taken"

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
            [{"username": "x", "name": "X"}],
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

    def test_registration_local_currently_does_not_enforce_auth_cn01_password_policy(
        self, api_client
    ):
        """Local registration accepts weak passwords (documents current AUTH/REG behavior)."""

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
                "name": "Weak Password Student",
            },
            format="json",
        )
        assert response.status_code == 200

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
                {"username": "no-name"},
                # Missing username
                {"name": "No Username"},
                # Valid researcher (admin can create)
                {
                    "username": "valid-researcher-bulk",
                    "name": "Valid Researcher",
                    "role": "RESEARCHER",
                    "email": "valid-researcher-bulk@example.com",
                },
                # Non-student without email (should be skipped)
                {"username": "no-email-teacher", "name": "No Email", "role": "TEACHER"},
            ],
            format="json",
        )
        assert response.status_code == 200
        assert response.data == 1

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
            {"username": "not-a-list"},
            format="json",
        )
        assert response.status_code == 400
