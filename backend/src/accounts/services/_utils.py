"""Shared utilities: normalizers, hash functions, throttle helpers, username generators."""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.crypto import salted_hmac

from core.permissions import primary_role

from ..models import Role, User

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
DEFAULT_RESET_CODE_WINDOW = timedelta(minutes=30)
REGISTRATION_CODE_TOKEN_BYTES = 12

REGISTRATION_CODE_STATUS_ACTIVE = "ACTIVE"
REGISTRATION_CODE_STATUS_EXHAUSTED = "EXHAUSTED"
REGISTRATION_CODE_STATUS_EXPIRED = "EXPIRED"
REGISTRATION_CODE_STATUS_REVOKED = "REVOKED"
REGISTRATION_CODE_STATUS_ARCHIVED = "ARCHIVED"
REGISTRATION_CODE_HMAC_SALT = "registration-code"
REGISTRATION_CODE_PREFIX_LENGTH = 8

MANAGED_USERNAME_LENGTH = 8
MANAGED_USERNAME_BASE_LENGTH = 7


def normalize_username_identifier(username: str) -> str:
    """Normalize login identifiers to lowercase for consistent uniqueness checks."""
    return str(username).strip().lower()


def normalize_registration_code_input(code: str) -> str:
    """Normalize invite code input for deterministic hashing and comparisons."""
    return str(code).strip().upper()


def registration_code_hash(code: str, *, secret: str | None = None) -> str:
    """Return deterministic salted HMAC digest for a registration code."""
    normalized = normalize_registration_code_input(code)
    if not normalized:
        return ""
    return salted_hmac(
        REGISTRATION_CODE_HMAC_SALT,
        normalized,
        secret=secret or settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def registration_code_prefix(code: str) -> str:
    """Return non-sensitive preview prefix for list/detail views."""
    normalized = normalize_registration_code_input(code)
    return normalized[:REGISTRATION_CODE_PREFIX_LENGTH]


def _registration_code_hashes_for_lookup(code: str) -> list[str]:
    """
    Build deterministic code hashes for current and fallback Django secrets.

    This allows seamless SECRET_KEY rotation using SECRET_KEY_FALLBACKS.
    Expected runtime bound is small: 1 hash normally, 2 during rotation.
    """
    normalized = normalize_registration_code_input(code)
    if not normalized:
        return []

    secrets_in_order: list[str] = []
    for secret in [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]:
        if not secret or secret in secrets_in_order:
            continue
        secrets_in_order.append(secret)

    return [
        salted_hmac(
            REGISTRATION_CODE_HMAC_SALT,
            normalized,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()
        for secret in secrets_in_order
    ]


def _hash_secret_token(value: str) -> str:
    """Hash a secret token before persisting it."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generate_secret_token(prefix: str, nbytes: int = 12) -> str:
    """Generate a prefixed token string for reset/invite flows."""
    return f"{prefix}-{secrets.token_hex(nbytes).upper()}"


def identifier_allowed_for_user(identifier: str, user: User) -> bool:
    """
    Validate whether an identifier is allowed for a specific user.

    Students must use username; non-students can use username or email.
    """
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return False

    normalized_username = normalize_username_identifier(user.username)
    role = primary_role(user)

    if role == Role.STUDENT:
        return normalized == normalized_username

    if normalized == normalized_username:
        return True

    if user.email:
        return normalized == normalize_username_identifier(user.email)
    return False


def check_identifier_throttle(scope: str, identifier: str) -> bool:
    """Return True if requests for an identifier are still allowed."""
    key = _identifier_throttle_key(scope, identifier)
    attempts = int(cache.get(key, 0))
    return attempts < LOGIN_RATE_LIMIT_ATTEMPTS


def register_identifier_failure(scope: str, identifier: str) -> None:
    """Increment failed-attempt counter for an identifier."""
    key = _identifier_throttle_key(scope, identifier)
    attempts = int(cache.get(key, 0)) + 1
    cache.set(key, attempts, LOGIN_RATE_LIMIT_WINDOW_SECONDS)


def clear_identifier_failures(scope: str, identifier: str) -> None:
    """Clear failed-attempt counter for an identifier after successful auth."""
    key = _identifier_throttle_key(scope, identifier)
    cache.delete(key)


def identifier_throttle_retry_after(scope: str, identifier: str) -> int:
    """
    Return Retry-After seconds for identifier lockout responses.

    Cache backends don't expose a portable TTL API, so we return the configured
    lockout window once the identifier has crossed the attempt threshold.
    TODO(infra): If we standardize on a cache backend with TTL introspection
    (e.g., Redis), switch this to true remaining TTL for precision.
    """
    if check_identifier_throttle(scope, identifier):
        return 0
    return LOGIN_RATE_LIMIT_WINDOW_SECONDS


def _identifier_throttle_key(scope: str, identifier: str) -> str:
    """Build cache key for identifier-throttle bookkeeping."""
    return f"auth-throttle:{scope}:{normalize_username_identifier(identifier)}"


def password_strength_errors(password: str) -> list[str]:
    """Return all password policy violations for AUTH-CN-01."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not any(ch.isupper() for ch in password):
        errors.append("Password must include at least one uppercase letter.")
    if not any(ch.islower() for ch in password):
        errors.append("Password must include at least one lowercase letter.")
    if not any(ch.isdigit() for ch in password):
        errors.append("Password must include at least one number.")
    if not any(not ch.isalnum() for ch in password):
        errors.append("Password must include at least one special character.")
    return errors


def _compact_alnum(value: str) -> str:
    """Keep only lowercase alphanumeric characters."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _unique_username_from_base(base: str) -> str:
    """Generate a unique username candidate by appending numeric suffixes."""
    max_len: int = User._meta.get_field("username").max_length or 150
    normalized_base = normalize_username_identifier(base)[:max_len] or "user"
    candidate = normalized_base
    suffix = 0
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        suffix_text = str(suffix)
        available = max_len - len(suffix_text)
        trimmed_base = normalized_base[:available] if available > 0 else ""
        candidate = f"{trimmed_base}{suffix_text}"
    return candidate


def _normalize_registration_name(
    first_name: str | None = None,
    last_name: str | None = None,
    name: str | None = None,
) -> tuple[str, str, str]:
    """Resolve first/last/full name inputs for registration."""
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    full = (name or "").strip()
    if not full and (first or last):
        full = " ".join(part for part in (first, last) if part)
    if full and (not first or not last):
        parts = [p for p in full.split() if p]
        if parts and not first:
            first = parts[0]
        if len(parts) > 1 and not last:
            last = parts[-1]
    return first, last, full


def _managed_username_seed(first_name: str, last_name: str, name: str) -> str:
    """Build username seed using first initial + last name."""
    first_compact = _compact_alnum(first_name)
    first_initial = first_compact[:1]
    last = _compact_alnum(last_name)
    if last:
        return f"{first_initial}{last}" or "user"
    if first_compact:
        return first_compact

    parts = [p for p in (name or "").split() if p]
    if len(parts) >= 2:
        candidate = f"{_compact_alnum(parts[0])[:1]}{_compact_alnum(parts[-1])}"
        if candidate:
            return candidate
    if len(parts) == 1:
        one = _compact_alnum(parts[0])
        if one:
            return one
    return "user"


def generate_managed_username(
    *, first_name: str | None = None, last_name: str | None = None, name: str | None = None
) -> str:
    """
    Generate fixed-width managed usernames for non-admin registrations.

    Format:
    - Seed: {first initial}{last name}
    - Width: 8 chars
    - Collision index: trailing numeric suffix starting at 0
    """
    first, last, full = _normalize_registration_name(first_name, last_name, name)
    seed = _managed_username_seed(first, last, full)
    base7 = (seed + ("0" * MANAGED_USERNAME_BASE_LENGTH))[:MANAGED_USERNAME_BASE_LENGTH]

    index = 0
    while True:
        index_text = str(index)
        prefix_len = max(1, MANAGED_USERNAME_LENGTH - len(index_text))
        prefix = (base7 + ("0" * prefix_len))[:prefix_len]
        candidate = f"{prefix}{index_text}"
        if len(candidate) > MANAGED_USERNAME_LENGTH:
            candidate = candidate[:MANAGED_USERNAME_LENGTH]
        if not identifier_in_use(candidate):
            return candidate
        index += 1


def generate_student_username(name: str) -> str:
    """Backward-compatible alias for managed username generation by full name."""
    return generate_managed_username(name=name)


def identifier_in_use(identifier: str, exclude_user_id: int | None = None) -> bool:
    """Check whether identifier is already used as username or email."""
    normalized = normalize_username_identifier(identifier)
    if not normalized:
        return False
    queryset = User.objects.filter(
        models.Q(username__iexact=normalized) | models.Q(email__iexact=normalized)
    )
    if exclude_user_id is not None:
        queryset = queryset.exclude(id=exclude_user_id)
    return queryset.exists()
