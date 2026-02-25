"""Custom authentication classes for API requests."""

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate JWT from Authorization header or HttpOnly cookie."""

    access_cookie_name = "access_token"

    def authenticate(self, request: Request):
        # Preserve standard bearer-token behavior first.
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(self.access_cookie_name)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
