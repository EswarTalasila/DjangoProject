"""Unit tests for model-level validation hooks."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import RegistrationCodeType, User
from tests.factories import RegistrationCodeFactory


@pytest.mark.django_db
@pytest.mark.integration
def test_registration_code_clean_rejects_invalid_usage_bounds():
    """RegistrationCode.clean enforces max_uses/times_used boundaries."""

    creator = User.objects.create_user(
        username="clean-creator", name="Creator", password="StartPass123!"
    )

    with pytest.raises(ValidationError, match="max_uses"):
        code = RegistrationCodeFactory(
            created_by=creator,
            code_type=RegistrationCodeType.RESEARCHER,
            max_uses=0,
            times_used=0,
            expires_at=timezone.now(),
        )
        code.full_clean()

    with pytest.raises(ValidationError, match="times_used cannot exceed"):
        code = RegistrationCodeFactory(
            created_by=creator,
            code_type=RegistrationCodeType.RESEARCHER,
            max_uses=1,
            times_used=2,
            expires_at=timezone.now(),
        )
        code.full_clean()


@pytest.mark.django_db
@pytest.mark.integration
def test_registration_code_clean_accepts_boundary_values():
    """times_used == max_uses is valid boundary condition."""

    creator = User.objects.create_user(
        username="clean-creator-2",
        name="Creator",
        password="StartPass123!",
    )
    code = RegistrationCodeFactory(
        created_by=creator,
        code_type=RegistrationCodeType.RESEARCHER,
        max_uses=1,
        times_used=1,
    )
    code.full_clean()
