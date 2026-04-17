"""
Constraint tests for SUDO feature domain.

SUDO-CN-02: Default-deny / opt-in permission semantics
SUDO-CN-06: Permission enum payload validation
"""

import pytest
from django.core.exceptions import ValidationError

from accounts.models import SudoPermission
from tests.factories import SudoGrantFactory

pytestmark = pytest.mark.integration



@pytest.mark.django_db
class TestSudoConstraints:
    """
    Tests for SudoGrant model validation.

    These test the clean() method which enforces permission constraints.
    """

    # =========================================================================
    # SUDO-CN-06: Permission enum payload validation
    # =========================================================================

    def test_SUDO_CN_06_permissions_must_be_list(self):
        """Non-list permissions are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions="not_a_list")
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "must be a list" in str(exc_info.value)

    # =========================================================================
    # SUDO-CN-06: Permission enum payload validation
    # =========================================================================

    def test_SUDO_CN_06_valid_permissions_accepted(self):
        """Valid SudoPermission values are accepted."""
        grant = SudoGrantFactory.build(
            permissions=[
                SudoPermission.CREATE_TEACHER.value,
                SudoPermission.CREATE_STUDENT.value,
            ]
        )
        grant.clean()  # Should not raise

    def test_SUDO_CN_06_E1_invalid_permission_rejected(self):
        """Invalid permission values are rejected with ValidationError."""
        grant = SudoGrantFactory.build(permissions=["INVALID_PERMISSION"])
        with pytest.raises(ValidationError) as exc_info:
            grant.clean()
        assert "permissions" in exc_info.value.message_dict
        assert "Invalid permissions" in str(exc_info.value)

    # =========================================================================
    # SUDO-CN-02: Empty permissions list is valid (opt-in semantics)
    # =========================================================================

    def test_SUDO_CN_02_empty_permissions_allowed(self):
        """Empty permissions list is valid (opt-in semantics)."""
        grant = SudoGrantFactory.build(permissions=[])
        grant.clean()  # Should not raise
