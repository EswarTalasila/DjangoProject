"""DRF throttle classes for public (AllowAny) endpoints."""

from rest_framework.throttling import AnonRateThrottle


class AnonAuthThrottle(AnonRateThrottle):
    """Standard rate limit for anonymous auth endpoints (20/min)."""

    scope = "anon_auth"


class AnonBurstThrottle(AnonRateThrottle):
    """Stricter burst limit for sensitive endpoints like login (5/min)."""

    scope = "anon_burst"
