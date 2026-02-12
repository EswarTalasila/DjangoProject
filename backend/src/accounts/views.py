"""
Authentication and user management API endpoints.

This module provides REST API views for:
- User registration and login (username/password and Google OAuth)
- User CRUD operations (create, read, update, delete)
- Password management (set initial password, reset password)
- Bulk user creation for administrators

All endpoints return JSON responses. Authentication uses JWT tokens via
SimpleJWT. Role-based access control is enforced via permission classes.

Endpoints:
    POST /api/v1/auth/register      - Public self-registration (student only)
    POST /api/v1/auth/login         - Username/password authentication
    POST /api/v1/auth/login/google  - Google OAuth authentication
    POST /api/v1/auth/check-email   - Check if email exists in system
    POST /api/v1/users              - Create user (teacher/admin, sudoed researcher)
    POST /api/v1/users/{id}         - Update user (teacher/admin, sudoed researcher)
    DELETE /api/v1/users/{username} - Delete user (teacher/admin, sudoed researcher)
    GET /api/v1/users/staff         - List staff (researcher/admin)
    POST /api/v1/users/{id}/password - Set initial password (first login flow)
    PUT /api/v1/users/{id}/password/reset - Reset password (admin, sudoed researcher)
    POST /api/v1/users/bulk         - Bulk create users (admin only)
"""

import json
from typing import Any, cast
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import (
    IsResearcherOrAdmin,
    IsTeacherOrAbove,
    has_sudo_permission,
    primary_role,
)

from .models import OAuthAccount, OAuthProvider, Role, SudoPermission
from .serializers import CheckEmailSerializer, UserInputSerializer, UserOutputSerializer
from .services import (
    authenticate_user,
    build_user_response,
    can_create_user,
    can_delete_user,
    can_edit_user,
    can_reset_password,
    create_user_from_payload,
    ensure_profiles_for_role,
    grant_sudo_to_researcher,
    link_or_create_oauth_account,
    revoke_sudo_grant,
    set_single_role,
)

User = get_user_model()


def _google_userinfo(access_token: str) -> dict[str, Any]:
    """
    Fetch Google user profile information using an OAuth access token.

    Makes an HTTP request to Google's userinfo endpoint to retrieve the
    authenticated user's profile data including their unique subject ID and email.

    Args:
        access_token: A valid Google OAuth2 access token obtained from the
            frontend after the user completes Google Sign-In.

    Returns:
        Dict containing Google user profile fields:
            - sub: Unique Google user identifier
            - email: User's email address
            - email_verified: Whether email is verified
            - name: User's display name
            - picture: URL to profile picture

    Raises:
        URLError: If the request to Google fails (network error, timeout)
        JSONDecodeError: If the response is not valid JSON
        HTTPError: If Google returns an error (invalid token, expired, etc.)
    """
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        return cast("dict[str, Any]", json.loads(response.read().decode("utf-8")))


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user account via public self-registration.

    This endpoint allows anyone to create a new account. For security,
    all self-registered users are assigned the STUDENT role regardless
    of any role specified in the request payload.

    Request Body:
        {
            "username": "user@example.com",  # Required, must be unique email
            "password": "securepassword",    # Required
            "name": "User Name"              # Required, display name
        }

    Returns:
        200: "User registered" on success
        400: "name, username, and password are required" if missing fields
        400: "Username already taken" if email exists

    Security Note:
        Role is forced to STUDENT to prevent privilege escalation.
        Use /api/v1/users endpoint for creating teachers/admins.
    """
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    if not payload.get("username") or not payload.get("password") or not payload.get("name"):
        return Response(
            "name, username, and password are required",
            status=status.HTTP_400_BAD_REQUEST,
        )
    if User.objects.filter(username__iexact=payload.get("username")).exists():
        return Response("Username already taken", status=status.HTTP_400_BAD_REQUEST)
    create_user_from_payload(payload, role_override=Role.STUDENT, creator=None)
    return Response("User registered", status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate a user with username and password, returning a JWT token.

    Validates credentials against the database and returns a JWT access token
    on success. The token should be included in subsequent requests via the
    Authorization header: "Bearer <token>".

    Request Body:
        {
            "username": "user@example.com",  # Required
            "password": "userpassword"       # Required
        }

    Returns:
        200: {
            "accessToken": "eyJ...",  # JWT access token
            "tokenType": "Bearer",
            "role": "STUDENT|TEACHER|RESEARCHER",
            "id": "123",
            "name": "User Name",
            "username": "user@example.com"
        }
        400: "username and password are required" if missing fields
        401: "Invalid username or password" if credentials invalid
    """
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    if not payload.get("username") or not payload.get("password"):
        return Response("username and password are required", status=status.HTTP_400_BAD_REQUEST)
    user = authenticate_user(payload.get("username"), payload.get("password"))
    if not user:
        return Response("Invalid username or password", status=status.HTTP_401_UNAUTHORIZED)
    refresh = RefreshToken.for_user(user)
    body = build_user_response(user, str(refresh.access_token))
    return Response(body, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_with_google(request):
    """
    Authenticate a user via Google OAuth, returning a JWT token.

    The frontend completes Google Sign-In and sends the access token here.
    This endpoint verifies the token with Google, then either:
    1. Links to an existing OAuth account and logs in, or
    2. Links to an existing user account by email (first Google login), or
    3. Returns an error if no matching account exists.

    Note: Users must be pre-created in the system before using Google login.
    This endpoint does NOT create new accounts - use register or create_user.

    Request Body:
        {
            "accessToken": "ya29.a0..."  # Google OAuth access token from frontend
        }

    Returns:
        200: {
            "accessToken": "eyJ...",  # JWT access token
            "tokenType": "Bearer",
            "role": "STUDENT|TEACHER|RESEARCHER",
            "id": "123"
        }
        400: "accessToken is required" if missing
        401: "Access token verification failed" if Google rejects token
        401: "Invalid Google userinfo" if response missing required fields
        401: "No account associated with this Google email" if user not found
    """
    access_token = request.data.get("accessToken")
    if not access_token:
        return Response({"error": "accessToken is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        userinfo = _google_userinfo(access_token)
    except Exception as exc:
        return Response(
            {"error": f"Access token verification failed: {exc}"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    subject = userinfo.get("sub")
    email = userinfo.get("email")
    if not subject or not email:
        return Response({"error": "Invalid Google userinfo"}, status=status.HTTP_401_UNAUTHORIZED)

    account = OAuthAccount.objects.filter(provider=OAuthProvider.GOOGLE, subject=subject).first()
    if account:
        account.email = email
        account.last_login_at = timezone.now()
        account.save(update_fields=["email", "last_login_at"])
        user = account.user
    else:
        found_user = User.objects.filter(username__iexact=email).first()
        if not found_user:
            return Response(
                {"error": "No account associated with this Google email."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        link_or_create_oauth_account(found_user, subject, email)
        user = found_user

    refresh = RefreshToken.for_user(user)
    body = {
        "accessToken": str(refresh.access_token),
        "tokenType": "Bearer",
        "role": primary_role(user),
        "id": str(user.id),
    }
    return Response(body, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def check_email(request):
    """
    Check if an email address exists in the system and if password is set.

    Used by the frontend during login flow to determine whether to show
    password input or first-time password setup screen.

    Request Body:
        {
            "email": "user@example.com"  # Email to check
        }

    Returns:
        200: {
            "exists": true,
            "userId": 123,           # User's database ID
            "needsPassword": false   # True if user has no password set
        }
        404: {"exists": false, "userId": -1, "needsPassword": false} if not found

    Security Note:
        This endpoint enables user enumeration. Consider adding rate limiting
        or captcha for production deployments (tracked in issue #18).
    """
    email = request.data.get("email")
    if not email:
        return Response({"exists": False, "userId": -1, "needsPassword": False})
    user = User.objects.filter(username__iexact=email).first()
    if not user:
        serializer = CheckEmailSerializer({"exists": False, "userId": -1, "needsPassword": False})
        return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
    needs_password = user.password is None
    serializer = CheckEmailSerializer(
        {"exists": True, "userId": user.id, "needsPassword": needs_password}
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def create_user(request):
    """
    Create a new user account with specified role (privileged operation).

    Teachers can create students only. Admins can create users of any role.
    The created user will have no password set initially - they must use
    the set_password endpoint or Google OAuth on first login.

    Request Body:
        {
            "username": "user@example.com",  # Required, must be unique
            "name": "User Name",             # Required
            "role": "STUDENT|TEACHER|RESEARCHER", # Optional, defaults to STUDENT
            "password": "optional"           # Optional initial password
        }

    Returns:
        200: "User created successfully."
        400: "name and username are required" if missing fields
        400: "Username already taken" if email exists
        403: "Forbidden" if requester lacks permission for requested role

    Permission Rules:
        - TEACHER: Can create STUDENT only
        - Researcher with CREATE_TEACHER/CREATE_STUDENT sudo permission
        - Admin (is_staff): Can create RESEARCHER or TEACHER
    """
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    if not payload.get("username") or not payload.get("name"):
        return Response("name and username are required", status=status.HTTP_400_BAD_REQUEST)
    requested_role = payload.get("role") or Role.STUDENT
    if not can_create_user(request.user, requested_role):
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    if User.objects.filter(username__iexact=payload.get("username")).exists():
        return Response("Username already taken", status=status.HTTP_400_BAD_REQUEST)
    create_user_from_payload(payload, role_override=requested_role, creator=request.user)
    return Response("User created successfully.", status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def edit_user(request, user_id: int):
    """
    Update an existing user's profile, role, or password.

    Enforces ownership rules: teachers can only edit their own students,
    admins can edit any user. Role changes trigger profile creation
    (e.g., promoting to teacher creates TeacherProfile).

    Args:
        user_id: Database ID of the user to update (path parameter)

    Request Body:
        {
            "name": "New Name",              # Optional
            "username": "new@example.com",   # Optional, must be unique
            "password": "newpassword",       # Optional
            "role": "STUDENT|TEACHER|RESEARCHER"  # Optional, changes user's role
        }

    Returns:
        200: "User edited successfully."
        400: "Username already taken" if new username exists
        403: "Forbidden" if requester lacks permission
        404: "User not found" if user_id doesn't exist

    Permission Rules:
        - TEACHER: Can edit own students only
        - Researcher with EDIT_USER sudo permission
        - Admin (is_staff): Can edit researchers and teachers
    """
    serializer = UserInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)
    requested_role = payload.get("role") or primary_role(user)
    if not can_edit_user(request.user, user, requested_role):
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    if payload.get("name"):
        user.name = payload["name"]
    if payload.get("username") and payload["username"] != user.username:
        if User.objects.filter(username__iexact=payload["username"]).exclude(id=user_id).exists():
            return Response("Username already taken", status=status.HTTP_400_BAD_REQUEST)
        user.username = payload["username"]
    if payload.get("password"):
        user.set_password(payload["password"])
    user.save()
    if payload.get("role"):
        set_single_role(user, payload["role"])
        ensure_profiles_for_role(user, payload["role"], creator=request.user)
    return Response("User edited successfully.", status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsTeacherOrAbove])
def delete_user(request, username: str):
    """
    Permanently delete a user account from the system.

    This is a hard delete - the user and all associated data (profiles,
    enrollments, submissions) are permanently removed. Teachers can only
    delete their own students; admins can delete any non-admin user.

    Args:
        username: Email/username of the user to delete (path parameter)

    Returns:
        200: "User deleted successfully."
        403: "Forbidden" if requester lacks permission
        404: "User not found" if username doesn't exist

    Permission Rules:
        - TEACHER: Can delete own students only
        - Researcher with DELETE_USER sudo permission
        - Admin (is_staff): Can delete researchers and teachers

    Warning:
        This performs a hard delete. Consider implementing soft delete
        for audit trail purposes (tracked in issue #24).
    """
    user = User.objects.filter(username=username).first()
    if not user:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)
    if not can_delete_user(request.user, user):
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    user.delete()
    return Response("User deleted successfully.", status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsResearcherOrAdmin])
def list_staff(request):
    """
    List all non-student users (researchers, teachers, and admins).

    Used by the admin/researcher dashboard to display staff members who can
    create courses and manage students. Researchers have read access for
    data oversight; admins have full access.

    Returns:
        200: [
            {
                "id": 123,
                "name": "Teacher Name",
                "username": "teacher@example.com",
                "role": "ROLE_TEACHER"  # Includes ROLE_ prefix for frontend
            },
            ...
        ]

    Note:
        The role field includes the "ROLE_" prefix for compatibility
        with the Angular frontend's role-based routing.
    """
    users = User.objects.filter(roles__role__in=[Role.TEACHER, Role.RESEARCHER]).distinct()
    serializer = UserOutputSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def set_password(request, user_id: int):
    """
    Set password for a user's first login (initial password setup).

    This endpoint is used when a user is created without a password
    (e.g., by a teacher/admin) and needs to set their password on
    first login. The frontend calls this after check_email returns
    needsPassword=true.

    Args:
        user_id: Database ID of the user (path parameter)

    Request Body:
        Raw text string containing the new password (not JSON)

    Returns:
        200: "Password set succesfully."
        400: "Password is required" if body is empty
        404: "User not found" if user_id doesn't exist

    Security Warning:
        This endpoint is currently unauthenticated, allowing anyone who
        knows a user ID to set their password. This should be secured
        with a time-limited, single-use token (tracked in issue #17).
    """
    password = request.body.decode("utf-8").strip()
    if not password:
        return Response("Password is required", status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)
    user.set_password(password)
    user.save()
    return Response("Password set succesfully.", status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsTeacherOrAbove])
def reset_password(request, user_id: int):
    """
    Reset a user's password, requiring them to set a new one on next login.

    Sets the user's password to null, which forces them through the
    first-login password setup flow. Teachers can reset passwords for
    their students; admins can reset any non-admin user's password.

    Args:
        user_id: Database ID of the user (path parameter)

    Returns:
        200: "Password reset successfully."
        403: "Forbidden" if requester lacks permission
        404: "User not found" if user_id doesn't exist

    Permission Rules:
        - Researcher with RESET_PASSWORD sudo permission
        - Admin (is_staff): Can reset password for researchers and teachers
    """
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)
    if not can_reset_password(request.user, user):
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    user.password = None
    user.save(update_fields=["password"])
    return Response("Password reset successfully.", status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsResearcherOrAdmin])
def bulk_create(request):
    """
    Create multiple user accounts in a single request.

    Processes a list of user objects and creates valid ones, silently
    skipping invalid entries. Useful for importing users from CSV or
    spreadsheet exports.

    Request Body:
        [
            {
                "username": "user1@example.com",
                "name": "User One",
                "role": "STUDENT",     # Optional, defaults to STUDENT
                "password": "optional" # Optional
            },
            {
                "username": "user2@example.com",
                "name": "User Two"
            },
            ...
        ]

    Returns:
        200: Integer count of successfully created users

    Skipped Entries:
        - Missing required fields (username, name)
        - Duplicate usernames (already exist)
        - Invalid serializer data
        - Roles requester cannot create (non-admin trying to create admin)

    Permission Rules:
        - Admin (is_staff): Full access
        - Researcher with BULK_CREATE sudo permission: Can bulk create

    Note:
        Failed entries are silently skipped. For detailed error reporting,
        use individual create_user calls instead.
    """
    # Researchers need BULK_CREATE sudo permission
    if not request.user.is_staff and not has_sudo_permission(
        request.user, SudoPermission.BULK_CREATE
    ):
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    if not isinstance(request.data, list):
        return Response("Expected list of users", status=status.HTTP_400_BAD_REQUEST)
    created = 0
    for entry in request.data:
        serializer = UserInputSerializer(data=entry)
        if not serializer.is_valid():
            continue
        payload = serializer.validated_data
        if not payload.get("username") or not payload.get("name"):
            continue
        requested_role = payload.get("role") or Role.STUDENT
        if not can_create_user(request.user, requested_role):
            continue
        if User.objects.filter(username__iexact=payload.get("username")).exists():
            continue
        create_user_from_payload(payload, role_override=requested_role, creator=request.user)
        created += 1
    return Response(created, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsResearcherOrAdmin])
def grant_sudo(request):
    """
    Grant sudo permissions to a researcher.

    Admins can grant any permissions and set can_grant_sudo=True.
    Sudoed researchers with can_grant_sudo=True can grant a subset of their
    own permissions, but cannot set can_grant_sudo=True (admin only).

    Request Body:
        {
            "user_id": 123,                    # Researcher to grant sudo to
            "permissions": ["CREATE_TEACHER"], # List of SudoPermission values
            "can_grant_sudo": false            # Optional, default false
        }

    Returns:
        200: {"message": "Sudo granted", "grant_id": N}
        400: Validation errors (missing user_id, invalid permissions)
        403: Permission denied (escalation attempt or unauthorized)
        404: User not found or not a researcher

    Permission Rules:
        - Admin (is_staff): Can grant any permissions, set can_grant_sudo=True
        - Researcher with can_grant_sudo: Can grant subset of own permissions
    """
    user_id = request.data.get("user_id")
    permissions = request.data.get("permissions", [])
    can_grant_sudo_flag = request.data.get("can_grant_sudo", False)

    if not user_id:
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    grantee = User.objects.filter(id=user_id).first()
    if not grantee:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        grant = grant_sudo_to_researcher(
            granter=request.user,
            grantee=grantee,
            permissions=permissions,
            can_grant_sudo=can_grant_sudo_flag,
        )
        return Response(
            {"message": "Sudo granted", "grant_id": grant.id}, status=status.HTTP_200_OK
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


@api_view(["DELETE"])
@permission_classes([IsResearcherOrAdmin])
def revoke_sudo(request, grant_id: int):
    """
    Revoke a sudo grant.

    Admins can revoke any grant. Sudoed researchers can revoke grants
    they created (where they are the granted_by user).

    Args:
        grant_id: ID of the SudoGrant to revoke (path parameter)

    Returns:
        200: {"message": "Sudo revoked"}
        403: Permission denied (not authorized to revoke this grant)
        404: Grant not found

    Permission Rules:
        - Admin (is_staff): Can revoke any grant
        - Researcher: Can revoke grants they created
    """
    try:
        revoke_sudo_grant(revoker=request.user, grant_id=grant_id)
        return Response({"message": "Sudo revoked"}, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
