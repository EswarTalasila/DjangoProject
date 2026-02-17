"""
Custom DRF exception handler for unified error response format.

This handler normalizes all exceptions (validation errors, permission denied,
authentication failed, throttle exceeded, and unhandled exceptions) into a
consistent {"detail": "message"} format.

All error responses from the API will use this single shape, making client-side
error handling simple and predictable.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Normalize all DRF exceptions to {"detail": "message"} format.

    Handles:
    - DRF serializer validation errors (multi-field dict format)
    - Non-field validation errors (list format)
    - Permission denied, authentication failed
    - Throttle exceeded
    - Already-correct {"detail": ...} errors
    - Unhandled exceptions (returns 500 with generic message)

    Args:
        exc: Exception instance
        context: Request context

    Returns:
        Response with {"detail": "user-facing message"} and appropriate status code
    """
    # Delegate to DRF's default handler first
    response = exception_handler(exc, context)

    # Unhandled exception (not a DRF exception)
    if response is None:
        return Response(
            {"detail": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Already correct format
    if isinstance(response.data, dict) and "detail" in response.data:
        return response

    # Pattern B: {"error": "message"} → {"detail": "message"}
    if isinstance(response.data, dict) and "error" in response.data:
        response.data = {"detail": response.data["error"]}
        return response

    # Pattern C: DRF serializer validation errors (multi-field dict)
    # Example: {"email": ["This field is required."], "password": ["Too short."]}
    # → Extract first error from first field and format as "{field}: {message}"
    if isinstance(response.data, dict) and len(response.data) > 0:
        # Get first field name and its errors
        first_field = next(iter(response.data))
        field_errors = response.data[first_field]

        # Extract first error message
        if isinstance(field_errors, list) and len(field_errors) > 0:
            first_error = str(field_errors[0])
            # Format with field name for clarity (unless it's "non_field_errors")
            if first_field == "non_field_errors":
                message = first_error
            else:
                message = f"{first_field}: {first_error}"
            response.data = {"detail": message}
            return response

    # Pattern D: List format (non-field errors)
    # Example: ["Invalid credentials", "Account inactive"]
    if isinstance(response.data, list) and len(response.data) > 0:
        response.data = {"detail": str(response.data[0])}
        return response

    # Pattern E: Bare string (shouldn't happen with DRF, but handle it)
    if isinstance(response.data, str):
        response.data = {"detail": response.data}
        return response

    # Fallback: unknown format
    response.data = {"detail": "An error occurred"}
    return response
