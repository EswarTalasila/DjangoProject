"""Authentication, sessions, and token management."""

from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import primary_role

from ..models import OAuthAccount, OAuthProvider, User
from ._utils import normalize_username_identifier


def build_user_response(user: User, access_token: str, refresh_token: str | None = None) -> dict:
    """
    Build the login response payload for a user.

    This creates the response structure expected by the frontend after
    successful authentication, including the JWT token and user metadata.

    Args:
        user: The authenticated user
        access_token: The JWT access token to include

    Returns:
        Dict with username/name/accessToken/tokenType/role/id fields
    """
    role = primary_role(user)
    payload: dict[str, str | None] = {
        "email": user.email or None,
        "username": user.username,
        "name": user.name,
        "accessToken": access_token,
        "tokenType": "Bearer",
        "role": role,
        "id": str(user.id),
    }
    if refresh_token:
        payload["refreshToken"] = refresh_token
    return payload


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.

    Args:
        username: The user's login identifier
        password: The user's password

    Returns:
        The authenticated User object, or None if authentication fails
    """
    normalized = normalize_username_identifier(username)
    if not normalized:
        return None

    user = find_user_by_identifier(normalized)
    if not user:
        return None

    return authenticate(username=user.username, password=password)


def find_user_by_identifier(identifier: str) -> User | None:
    """Resolve a user using the normalized identifier field."""
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return None
    user = User.objects.filter(username__iexact=normalized).first()
    if user:
        return user
    return User.objects.filter(email__iexact=normalized).first()


def invalidate_user_sessions(user: User) -> int:
    """
    Invalidate all outstanding refresh tokens for a user.

    Returns the number of tokens newly blacklisted.
    """
    blacklisted = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            blacklisted += 1
    return blacklisted


def blacklist_refresh_token(refresh_token: str) -> bool:
    """Blacklist a single refresh token for logout."""
    try:
        token = RefreshToken(refresh_token)  # type: ignore[arg-type]
        token.blacklist()
    except TokenError:
        return False
    return True


def link_or_create_oauth_account(user: User, subject: str, email: str) -> OAuthAccount:
    """
    Link a Google OAuth account to a user, or update an existing link.

    This is called during Google OAuth login to associate the Google account
    with the local user account. If the link already exists, it updates the
    email in case it has changed.

    Args:
        user: The local user to link
        subject: The Google account subject ID (unique identifier)
        email: The email from the Google account

    Returns:
        The OAuthAccount linking the user to their Google account
    """
    account, _ = OAuthAccount.objects.update_or_create(
        provider=OAuthProvider.GOOGLE,
        subject=subject,
        defaults={"user": user, "email": email},
    )
    return account
