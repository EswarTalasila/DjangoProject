"""Unit tests for key model __str__ representations."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import PasswordResetRequestStatus, RegistrationCodeType, Role, UserRole
from tests.factories import (
    OAuthAccountFactory,
    PasswordResetCodeFactory,
    PasswordResetRequestFactory,
    RegistrationCodeFactory,
    ResearcherProfileFactory,
    StudentProfileFactory,
    SudoGrantFactory,
    TeacherProfileFactory,
    UserFactory,
)


@pytest.mark.django_db
@pytest.mark.integration
def test_model_str_representations():
    """Core account-domain models return readable __str__ values."""

    user = UserFactory(username="str-user", name="String User")
    role = UserRole.objects.create(user=user, role=Role.STUDENT)
    researcher_profile = ResearcherProfileFactory()
    teacher_profile = TeacherProfileFactory()
    student_profile = StudentProfileFactory()
    grant = SudoGrantFactory(
        user=researcher_profile.user, granted_by=user, permissions=["CREATE_STUDENT"]
    )

    reg_code = RegistrationCodeFactory(
        created_by=user,
        code_type=RegistrationCodeType.STUDENT,
        code_prefix="REG12345",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    reset_request = PasswordResetRequestFactory(
        user=user,
        status=PasswordResetRequestStatus.PENDING,
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    reset_code = PasswordResetCodeFactory(request=reset_request)
    oauth = OAuthAccountFactory(user=user, subject="sub-1")

    assert str(user) == "String User <str-user>"
    assert str(role) == f"{user.username}: {Role.STUDENT}"
    assert "ResearcherProfile(" in str(researcher_profile)
    assert "TeacherProfile(" in str(teacher_profile)
    assert "StudentProfile(" in str(student_profile)
    assert "SudoGrant(" in str(grant)
    assert str(reg_code) == f"{RegistrationCodeType.STUDENT}:REG12345"
    assert "PasswordResetRequest(" in str(reset_request)
    assert "PasswordResetCode(" in str(reset_code)
    assert str(oauth).startswith("GOOGLE:")
