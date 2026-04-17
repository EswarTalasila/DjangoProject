"""
Shared query-parameter parsing helpers.

Reusable parsers for common query-string patterns across multiple views
(assessments, assignments, courses, etc.).
"""

from rest_framework import status
from rest_framework.response import Response


def parse_include_archived(request):
    """
    Parse the ``includeArchived`` boolean query parameter.

    Returns:
        (bool, None) on success — the parsed boolean and no error.
        (None, Response) on invalid input — None and a 400 error Response.
        Defaults to False when the parameter is absent or empty.
    """
    raw = request.query_params.get("includeArchived")
    if raw is None or raw == "":
        return False, None
    value = raw.lower()
    if value not in {"true", "false"}:
        return (
            None,
            Response(
                {"detail": "includeArchived must be true or false"},
                status=status.HTTP_400_BAD_REQUEST,
            ),
        )
    return value == "true", None
