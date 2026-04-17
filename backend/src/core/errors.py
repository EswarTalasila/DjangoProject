"""
Shared error response helpers for consistent API error formatting.

This module provides factory functions for creating standardized error
responses across all API endpoints. Using these helpers ensures consistent
error message format and HTTP status codes throughout the application.

Usage:
    from core.errors import error_response, server_error_response

    # For validation/business logic errors
    return error_response("Username already taken")
    return error_response(ValueError("Course not found"))

    # For unexpected server errors
    return server_error_response()
"""

from rest_framework import status
from rest_framework.response import Response


def error_response(exc: Exception | str, status_code: int | None = None) -> Response:
    """
    Build a standardized error response from an exception or message.

    Automatically detects "not found" errors and uses 404 status code.
    Otherwise defaults to 400 Bad Request.

    Args:
        exc: Exception instance or error message string
        status_code: Optional override for HTTP status code

    Returns:
        Response with error message and appropriate HTTP status

    Examples:
        error_response("Invalid email format")  # 400 Bad Request
        error_response("User not found")        # 404 Not Found (auto-detected)
        error_response("Unauthorized", 401)     # 401 Unauthorized (explicit)
    """
    message = str(exc) if exc else "Bad request"
    code = status_code or status.HTTP_400_BAD_REQUEST
    if "not found" in message.lower():
        code = status.HTTP_404_NOT_FOUND
    return Response({"detail": message}, status=code)


def server_error_response() -> Response:
    """
    Return a generic 500 Internal Server Error response.

    Use this when an unexpected exception occurs that shouldn't expose
    internal details to the client. The actual exception should be logged
    separately for debugging.

    Returns:
        Response with generic error message and 500 status
    """
    return Response(
        {"detail": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
