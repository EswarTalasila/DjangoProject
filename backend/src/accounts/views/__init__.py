"""
Accounts views package.

Re-exports all view functions and their dependencies for URL routing
and test mock-patch compatibility.

IMPORTANT: Base dependencies (services, models, core, serializers) are
imported FIRST so they exist in this namespace before submodules load.
Submodules import their dependencies from `accounts.views` (this package)
rather than from the original source, ensuring that test patches applied
to `accounts.views.<name>` are visible at call time.
"""

import json  # noqa: F401
import logging  # noqa: F401
from typing import Any, Literal, cast  # noqa: F401
from urllib.error import HTTPError, URLError  # noqa: F401
from urllib.request import Request, urlopen  # noqa: F401

from django.conf import settings  # noqa: F401
from django.contrib.auth import get_user_model  # noqa: F401
from django.utils import timezone  # noqa: F401
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes, throttle_classes  # noqa: F401
from rest_framework.permissions import AllowAny, IsAuthenticated  # noqa: F401
from rest_framework.response import Response  # noqa: F401
from rest_framework_simplejwt.exceptions import TokenError  # noqa: F401
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: F401

from django.db.models import Exists, OuterRef, Prefetch, Q  # noqa: F401

from core.audit import complete_audit, get_client_ip, log_audit  # noqa: F401
from core.errors import error_response, server_error_response  # noqa: F401
from core.models import AuditAction, AuditOutcome  # noqa: F401
from core.pagination import paginate  # noqa: F401
from core.permissions import (  # noqa: F401
    IsResearcherOrAdmin,
    IsTeacherOrAbove,
    primary_role,
)
from core.throttles import AnonAuthThrottle, AnonBurstThrottle  # noqa: F401

from courses.models import Enrollment, EnrollmentStatus  # noqa: F401

from accounts.models import (  # noqa: F401
    OAuthAccount,
    OAuthProvider,
    RegistrationCodeType,
    Role,
    SudoGrant,
    SudoPermission,
)
from accounts.serializers import (  # noqa: F401
    GoogleOAuthLoginSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetCodeCompleteSerializer,
    PasswordResetCodeIssueSerializer,
    PasswordResetCodeVerifySerializer,
    RefreshTokenSerializer,
    RegistrationCodeCreateSerializer,
    RegistrationCodeUpdateSerializer,
    RegistrationCodeValidateInputSerializer,
    RegistrationOAuthSerializer,
    StudentInviteRegisterSerializer,
    StudentJoinCourseSerializer,
    StudentListSerializer,
    UserInputSerializer,
    UserOutputSerializer,
)
from accounts.services import (  # noqa: F401
    authenticate_user,
    blacklist_refresh_token,
    build_user_response,
    can_create_user,
    can_delete_user,
    can_edit_user,
    check_identifier_throttle,
    clear_identifier_failures,
    complete_password_reset,
    create_registration_codes,
    create_user_from_payload,
    ensure_profiles_for_role,
    find_user_by_identifier,
    generate_managed_username,
    grant_sudo_to_researcher,
    identifier_allowed_for_user,
    identifier_in_use,
    identifier_throttle_retry_after,
    invalidate_user_sessions,
    issue_password_reset_code,
    link_or_create_oauth_account,
    normalize_username_identifier,
    password_strength_errors,
    redeem_non_student_local_invite,
    redeem_non_student_oauth_invite,
    redeem_student_invite,
    redeem_student_join_course,
    register_identifier_failure,
    registration_code_scope_queryset,
    registration_code_status,
    revoke_sudo_grant,
    set_single_role,
    transition_registration_code_status,
    validate_registration_code,
    verify_password_reset_code,
)

User = get_user_model()  # noqa: F401
logger = logging.getLogger(__name__)  # noqa: F401
USERNAME_IMMUTABLE_DETAIL = "username is system-managed and must not be provided"  # noqa: F401
ACCESS_COOKIE_NAME = "access_token"  # noqa: F401
REFRESH_COOKIE_NAME = "refresh_token"  # noqa: F401
AUTH_COOKIE_SAMESITE: Literal["Lax"] = "Lax"  # noqa: F401

# ---------------------------------------------------------------------------
# Now import view functions from submodules.
# Submodules import their dependencies from this package (accounts.views),
# so mock patches on accounts.views.<name> propagate correctly.
# ---------------------------------------------------------------------------

from .auth import (  # noqa: F401, E402
    _cookie_secure,
    _set_auth_cookies,
    _clear_auth_cookies,
    _extract_refresh_token,
    _identifier_throttle_response,
    _google_userinfo,
    login,
    current_user_profile,
    refresh,
    logout,
    change_password,
    login_with_google,
    issue_password_reset_code_view,
    verify_reset_code,
    complete_reset_code,
)
from .registration import (  # noqa: F401, E402
    register_account,
    _register_local,
    _register_oauth,
    validate_registration_code_view,
    join_course_with_code,
    _serialize_registration_code,
    _create_codes,
    _list_codes,
    codes_collection,
    code_detail,
)
from .users import (  # noqa: F401, E402
    create_user,
    manage_user,
    _edit_user,
    _delete_user,
)
from .sudo import (  # noqa: F401, E402
    my_sudo_grant,
    _list_sudo_grants,
    sudo_grants_collection,
    _grant_sudo,
    revoke_sudo,
)
from .staff import (  # noqa: F401, E402
    list_staff,
    list_students,
)
