"""Unit tests for registration/invite service helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from accounts.models import (
    RegistrationCodeType,
    Role,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from accounts.services import (
    _get_role_value,
    _role_from_registration_code_type,
    _select_valid_code_for_update,
    create_registration_codes,
    generate_student_username,
    identifier_in_use,
    redeem_non_student_oauth_invite,
    redeem_student_invite,
    redeem_student_join_course,
    registration_code_hash,
    registration_code_prefix,
    transition_registration_code_status,
)
from courses.models import Course
from tests.factories import RegistrationCodeFactory, SudoGrantFactory


@pytest.mark.django_db
@pytest.mark.integration
def test_registration_code_hash_empty_input_returns_empty_string():
    """Hash helper returns empty digest for empty/whitespace code."""

    assert registration_code_hash("") == ""
    assert registration_code_hash("   ") == ""


@pytest.mark.django_db
@pytest.mark.integration
@override_settings(SECRET_KEY="primary", SECRET_KEY_FALLBACKS=["old"])
def test_REG_CN_22_hash_lookup_works_after_key_rotation():
    """Lookup supports fallback secret hashes during key rotation."""

    creator = User.objects.create_user(username="creator", name="Creator", password="StartPass123!")
    UserRole.objects.create(user=creator, role=Role.RESEARCHER)

    code = "REG-ROTATE"
    old_hash = registration_code_hash(code, secret="old")
    record = RegistrationCodeFactory(
        code_hash=old_hash, code_prefix=registration_code_prefix(code), created_by=creator
    )

    assert _select_valid_code_for_update(code).id == record.id


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_CN_16_generate_student_username_managed_format_edge_cases():
    """Managed username format is fixed-width and index-suffixed."""

    assert generate_student_username("") == "user0000"
    assert generate_student_username("Plato") == "plato000"
    assert generate_student_username("Jane Smith") == "jsmith00"


@pytest.mark.django_db
@pytest.mark.integration
def test_get_role_value_accepts_legacy_prefix_and_rejects_invalid():
    """Role normalization accepts ROLE_ prefix and rejects unknown values."""

    assert _get_role_value("ROLE_TEACHER") == Role.TEACHER
    with pytest.raises(ValueError, match="Invalid role"):
        _get_role_value("ROLE_NOT_A_ROLE")


@pytest.mark.django_db
@pytest.mark.integration
def test_role_from_registration_code_type_mapping():
    """Code type to role mapping returns expected role values."""

    assert _role_from_registration_code_type(RegistrationCodeType.STUDENT) == Role.STUDENT
    assert _role_from_registration_code_type(RegistrationCodeType.TEACHER) == Role.TEACHER
    assert _role_from_registration_code_type(RegistrationCodeType.RESEARCHER) == Role.RESEARCHER


@pytest.mark.django_db
@pytest.mark.integration
def testidentifier_in_use_respects_exclusion_filter():
    """Identifier collision check ignores excluded user id."""

    user = User.objects.create_user(
        username="collision-user",
        email="collision@example.com",
        name="Collision",
        password="StartPass123!",
    )

    assert identifier_in_use("collision-user") is True
    assert identifier_in_use("collision@example.com") is True
    assert identifier_in_use("collision-user", exclude_user_id=user.id) is False


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01a_E2_redeem_student_join_course_rejects_non_student_user():
    """Only student-role users can redeem student course join codes."""

    teacher = User.objects.create_user(
        username="teacher-a", name="Teacher", password="StartPass123!"
    )
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    teacher_profile = TeacherProfile.objects.create(user=teacher)

    code = "JOIN-STUDENT"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code),
        code_prefix=registration_code_prefix(code),
        code_type=RegistrationCodeType.STUDENT,
        created_by=teacher,
        course=Course.objects.create(name="Join Course", teacher_profile=teacher_profile),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(PermissionError, match="Only student accounts"):
        redeem_student_join_course(teacher, code)


@pytest.mark.django_db
@pytest.mark.integration
def test_redeem_student_invite_requires_split_name_fields():
    """Student invite redemption enforces firstName/lastName for username generation."""

    teacher = User.objects.create_user(
        username="teacher-b", name="Teacher", password="StartPass123!"
    )
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    teacher_profile = TeacherProfile.objects.create(user=teacher)
    code = "STUDENT-INV-1"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code),
        code_prefix=registration_code_prefix(code),
        code_type=RegistrationCodeType.STUDENT,
        created_by=teacher,
        course=Course.objects.create(name="Student Invite", teacher_profile=teacher_profile),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="firstName and lastName are required"):
        redeem_student_invite({"code": code, "password": "StartPass123!"})


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_02_E3_create_registration_codes_student_requires_course_id():
    """Student code generation requires courseId."""

    teacher = User.objects.create_user(
        username="teacher-c", name="Teacher", password="StartPass123!"
    )
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=teacher)

    with pytest.raises(ValueError, match="courseId is required"):
        create_registration_codes(
            creator=teacher,
            code_type=RegistrationCodeType.STUDENT,
            count=1,
            uses_per_code=1,
            expires_at=timezone.now() + timedelta(hours=1),
            course_id=None,
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_02_E4_create_registration_codes_metadata_rules_enforced():
    """Metadata allowed only for single teacher code generation."""

    researcher = User.objects.create_user(
        username="researcher-c", name="Researcher", password="StartPass123!"
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)

    with pytest.raises(ValueError, match="metadata can only be set when count is 1"):
        create_registration_codes(
            creator=researcher,
            code_type=RegistrationCodeType.TEACHER,
            count=2,
            uses_per_code=1,
            expires_at=timezone.now() + timedelta(hours=1),
            metadata={"note": "x"},
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_create_registration_codes_researcher_requires_sudo_for_researcher_codes():
    """Researcher code generation requires ISSUE_RESEARCHER_REG_CODE sudo permission."""

    researcher = User.objects.create_user(
        username="researcher-no-researcher-codes",
        name="Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)

    with pytest.raises(PermissionError, match="Not authorized to generate this code type"):
        create_registration_codes(
            creator=researcher,
            code_type=RegistrationCodeType.RESEARCHER,
            count=1,
            uses_per_code=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_create_registration_codes_researcher_with_permission_can_generate_researcher_codes():
    """Researcher with ISSUE_RESEARCHER_REG_CODE can generate researcher invite codes."""

    admin = User.objects.create_user(
        username="admin-grants-researcher-codes",
        email="admin-grants-researcher-codes@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    researcher = User.objects.create_user(
        username="researcher-with-researcher-codes",
        name="Researcher",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)
    SudoGrantFactory(
        user=researcher,
        granted_by=admin,
        permissions=[SudoPermission.ISSUE_RESEARCHER_REG_CODE.value],
    )

    created = create_registration_codes(
        creator=researcher,
        code_type=RegistrationCodeType.RESEARCHER,
        count=1,
        uses_per_code=1,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert len(created) == 1
    assert created[0].code_type == RegistrationCodeType.RESEARCHER


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_03_E2_transition_registration_code_status_rejects_invalid_current_state():
    """Cannot revoke exhausted/non-active code states."""

    admin = User.objects.create_user(username="admin-c", name="Admin", password="StartPass123!")
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    code = RegistrationCodeFactory(
        created_by=admin,
        code_type=RegistrationCodeType.RESEARCHER,
        times_used=1,
        max_uses=1,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="Only ACTIVE codes"):
        transition_registration_code_status(
            actor=admin,
            registration_code_id=code.id,
            next_status="REVOKED",
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_redeem_non_student_oauth_invite_rejects_existing_subject_link():
    """OAuth invite redemption blocks already-linked OAuth subjects."""

    admin = User.objects.create_user(
        username="admin-oauth",
        email="admin-oauth@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    code = "TEACHER-OAUTH-CODE"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code),
        code_prefix=registration_code_prefix(code),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    existing = User.objects.create_user(
        username="existing-oauth",
        email="existing-oauth@example.com",
        name="Existing OAuth",
        password="StartPass123!",
    )
    from tests.factories import OAuthAccountFactory

    OAuthAccountFactory(user=existing, subject="dup-subject", email="existing-oauth@example.com")

    with pytest.raises(ValueError, match="already linked"):
        redeem_non_student_oauth_invite(
            code=code,
            oauth_subject="dup-subject",
            oauth_email="new-email@example.com",
            first_name="New",
            last_name="User",
        )


# --- Branch-coverage additions ---


@pytest.mark.django_db
@pytest.mark.integration
def test_registration_code_hashes_for_lookup_empty_returns_empty():
    """Empty/whitespace code returns no hashes."""

    from accounts.services import _registration_code_hashes_for_lookup

    assert _registration_code_hashes_for_lookup("") == []
    assert _registration_code_hashes_for_lookup("   ") == []


@pytest.mark.django_db
@pytest.mark.integration
@override_settings(SECRET_KEY="primary", SECRET_KEY_FALLBACKS=["", "primary", "fallback"])
def test_registration_code_hashes_deduplicates_and_skips_empty():
    """Lookup deduplicates primary/fallback keys and skips empty."""

    from accounts.services import _registration_code_hashes_for_lookup

    hashes = _registration_code_hashes_for_lookup("SOME-CODE")
    # Empty string skipped, "primary" deduplicated — expect 2 hashes
    assert len(hashes) == 2


@pytest.mark.django_db
@pytest.mark.integration
def test_get_role_value_none_defaults_to_student():
    """None input returns STUDENT as default."""

    assert _get_role_value(None) == Role.STUDENT


@pytest.mark.django_db
@pytest.mark.integration
def test_unique_username_from_base_collision_loop():
    """Username generation appends numeric suffix when base is taken."""

    from accounts.services import _unique_username_from_base

    User.objects.create_user(username="testbase", name="Base", password="StartPass123!")
    result = _unique_username_from_base("testbase")
    assert result == "testbase1"

    User.objects.create_user(username="testbase1", name="Base1", password="StartPass123!")
    result2 = _unique_username_from_base("testbase")
    assert result2 == "testbase2"


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_CN_16_generate_student_username_collision_loop():
    """Managed username generator uses fixed width and collision index suffix."""

    from accounts.services import generate_student_username

    User.objects.create_user(username="jsmith00", name="Existing", password="StartPass123!")
    result = generate_student_username("Jane Smith")
    assert result == "jsmith01"

    User.objects.create_user(username="jsmith01", name="Existing2", password="StartPass123!")
    result2 = generate_student_username("Jane Smith")
    assert result2 == "jsmith02"


@pytest.mark.django_db
@pytest.mark.integration
def testidentifier_in_use_empty_returns_false():
    """Empty identifier is never in use."""

    assert identifier_in_use("") is False
    assert identifier_in_use("   ") is False


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01_redeem_non_student_local_invite_happy_path_and_exhaustion():
    """Non-student local invite creates user and exhausts code at max uses."""

    from accounts.models import RegistrationCode
    from accounts.services import redeem_non_student_local_invite

    admin = User.objects.create_user(
        username="admin-local-inv",
        email="admin-local-inv@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    code_text = "TEACHER-LOCAL-1"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        max_uses=1,
        times_used=0,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    user = redeem_non_student_local_invite(
        {
            "code": code_text,
            "firstName": "New",
            "lastName": "Teacher",
            "email": "new-teacher-local@example.com",
            "password": "StartPass123!",
        }
    )
    assert user.username == "nteache0"

    # Check code was exhausted
    record = RegistrationCode.objects.get(code_hash=registration_code_hash(code_text))
    assert record.times_used == 1
    assert record.is_active is False


@pytest.mark.django_db
@pytest.mark.integration
def test_redeem_non_student_local_invite_rejects_student_code():
    """Student codes cannot be redeemed via non-student local flow."""

    from accounts.services import redeem_non_student_local_invite

    teacher = User.objects.create_user(
        username="t-student-code", name="T", password="StartPass123!"
    )
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=teacher)

    code_text = "STUDENT-LOCAL-ERR"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.STUDENT,
        created_by=teacher,
        course=Course.objects.create(name="Local Err", teacher_profile=teacher.teacher_profile),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="student registration"):
        redeem_non_student_local_invite(
            {
                "code": code_text,
                "firstName": "Blocked",
                "lastName": "User",
                "email": "blocked@example.com",
                "password": "StartPass123!",
            }
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01_E3_redeem_non_student_local_invite_missing_split_name():
    """Missing first/last name fields are rejected for non-student registration."""

    from accounts.services import redeem_non_student_local_invite

    admin = User.objects.create_user(
        username="admin-missing-un",
        email="admin-missing-un@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    code_text = "TEACHER-NO-UN"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="firstName and lastName are required"):
        redeem_non_student_local_invite(
            {
                "code": code_text,
                "email": "no-un@example.com",
                "password": "StartPass123!",
            }
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01_E3_redeem_non_student_local_invite_missing_email():
    """Missing email rejected for non-student registration."""

    from accounts.services import redeem_non_student_local_invite

    admin = User.objects.create_user(
        username="admin-missing-em",
        email="admin-missing-em@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    code_text = "TEACHER-NO-EM"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="email is required"):
        redeem_non_student_local_invite(
            {
                "code": code_text,
                "firstName": "No",
                "lastName": "Email",
                "password": "StartPass123!",
            }
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_redeem_non_student_local_invite_username_taken():
    """Generated username collision resolves via numeric index."""

    from accounts.services import redeem_non_student_local_invite

    admin = User.objects.create_user(
        username="admin-taken-un",
        email="admin-taken-un@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    User.objects.create_user(username="euser000", name="Existing", password="StartPass123!")

    code_text = "TEACHER-TAKEN-UN"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    user = redeem_non_student_local_invite(
        {
            "code": code_text,
            "firstName": "E",
            "lastName": "User",
            "email": "unique-email@example.com",
            "password": "StartPass123!",
        }
    )
    assert user.username == "euser001"


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01_E2_redeem_non_student_local_invite_email_taken():
    """Taken email blocks non-student registration."""

    from accounts.services import redeem_non_student_local_invite

    admin = User.objects.create_user(
        username="admin-taken-em",
        email="admin-taken-em@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    User.objects.create_user(
        username="em-owner",
        email="taken-email@example.com",
        name="Owner",
        password="StartPass123!",
    )

    code_text = "TEACHER-TAKEN-EM"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code_text),
        code_prefix=registration_code_prefix(code_text),
        code_type=RegistrationCodeType.TEACHER,
        created_by=admin,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="Email already taken"):
        redeem_non_student_local_invite(
            {
                "code": code_text,
                "firstName": "Unique",
                "lastName": "User",
                "email": "taken-email@example.com",
                "password": "StartPass123!",
            }
        )


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_CN_04_registration_code_scope_queryset_teacher_scope():
    """Teacher queryset scoped to own student codes only."""

    from accounts.services import registration_code_scope_queryset

    teacher = User.objects.create_user(username="scope-t", name="T", password="StartPass123!")
    UserRole.objects.create(user=teacher, role=Role.TEACHER)
    TeacherProfile.objects.create(user=teacher)

    code = RegistrationCodeFactory(
        created_by=teacher,
        code_type=RegistrationCodeType.STUDENT,
        course=Course.objects.create(name="Scope C", teacher_profile=teacher.teacher_profile),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    qs = registration_code_scope_queryset(teacher)
    assert qs.filter(id=code.id).exists()


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_CN_04_registration_code_scope_queryset_student_gets_nothing():
    """Student role returns empty queryset for code listing."""

    from accounts.services import registration_code_scope_queryset

    student = User.objects.create_user(username="scope-s", name="S", password="StartPass123!")
    UserRole.objects.create(user=student, role=Role.STUDENT)

    qs = registration_code_scope_queryset(student)
    assert qs.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_REG_UC_01_E1_validate_registration_code_various_invalid_states():
    """Validation rejects archived, inactive, expired, and exhausted codes."""

    from accounts.services import validate_registration_code

    admin = User.objects.create_user(
        username="val-admin",
        email="val-admin@example.com",
        name="Admin",
        password="StartPass123!",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])

    # Archived
    code1_text = "VAL-ARCH"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code1_text),
        code_prefix=registration_code_prefix(code1_text),
        code_type=RegistrationCodeType.RESEARCHER,
        created_by=admin,
        archived_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert validate_registration_code(code1_text) is None

    # Inactive (revoked)
    code2_text = "VAL-REVOKED"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code2_text),
        code_prefix=registration_code_prefix(code2_text),
        code_type=RegistrationCodeType.RESEARCHER,
        created_by=admin,
        is_active=False,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert validate_registration_code(code2_text) is None

    # Expired
    code3_text = "VAL-EXPIRED"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code3_text),
        code_prefix=registration_code_prefix(code3_text),
        code_type=RegistrationCodeType.RESEARCHER,
        created_by=admin,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    assert validate_registration_code(code3_text) is None

    # Exhausted
    code4_text = "VAL-EXHAUST"
    RegistrationCodeFactory(
        code_hash=registration_code_hash(code4_text),
        code_prefix=registration_code_prefix(code4_text),
        code_type=RegistrationCodeType.RESEARCHER,
        created_by=admin,
        max_uses=1,
        times_used=1,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert validate_registration_code(code4_text) is None
