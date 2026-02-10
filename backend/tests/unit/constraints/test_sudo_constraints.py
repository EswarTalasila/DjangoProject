"""
Constraint tests for SUDO feature domain.

Tests for SudoGrant model validation constraints.

SUDO-CN-01: Permissions field must be a list
SUDO-CN-02: Permissions must be valid SudoPermission enum values
SUDO-CN-03: Empty permissions list is valid (opt-in semantics)
"""

import pytest
from django.core.exceptions import ValidationError

from accounts.models import SudoPermission
from tests.factories import SudoGrantFactory


@pytest.mark.django_db
class TestSudoConstraints:
    """
    Tests for SudoGrant model validation.

    These test the clean() method which enforces permission constraints.
    """

    # =========================================================================
    # SUDO-CN-01: Permissions field must be a list
    # =========================================================================

    def test_SUDO_CN_01(self):
        """Non-list permissions are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions="not_a_list")
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "must be a list" in str(exc_info.value)

    # =========================================================================
    # SUDO-CN-02: Permissions must be valid SudoPermission enum values
    # =========================================================================

    def test_SUDO_CN_02(self):
        """Valid SudoPermission values are accepted."""
        grant = SudoGrantFactory.build(
            permissions=[
                SudoPermission.CREATE_TEACHER.value,
                SudoPermission.CREATE_STUDENT.value,
            ]
        )
        grant.clean()  # Should not raise

    def test_SUDO_CN_02_E1(self):
        """Invalid permission values are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions=["INVALID_PERMISSION"])
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "Invalid permissions" in str(exc_info.value)

    # =========================================================================
    # SUDO-CN-03: Empty permissions list is valid (opt-in semantics)
    # =========================================================================

    def test_SUDO_CN_03(self):
        """Empty permissions list is valid (opt-in semantics)."""
        grant = SudoGrantFactory.build(permissions=[])
        grant.clean()  # Should not raise
