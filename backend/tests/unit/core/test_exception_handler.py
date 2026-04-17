"""Unit tests for DRF exception response normalization."""

from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

import core.exception_handler as handler

pytestmark = pytest.mark.unit



def test_unhandled_exception_returns_generic_500(monkeypatch):
    """Unhandled exceptions are normalized to a generic 500 response."""
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: None)

    response = handler.custom_exception_handler(Exception("boom"), {})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == {"detail": "Internal server error"}


def test_detail_payload_passes_through(monkeypatch):
    """Responses already using {detail: ...} are returned as-is."""
    original = Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: original)

    response = handler.custom_exception_handler(Exception("x"), {})

    assert response is original
    assert response.data == {"detail": "Forbidden"}


def test_error_key_is_remapped_to_detail(monkeypatch):
    """Legacy {error: ...} payloads are converted to {detail: ...}."""
    original = Response({"error": "Nope"}, status=status.HTTP_400_BAD_REQUEST)
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: original)

    response = handler.custom_exception_handler(Exception("x"), {})

    assert response.data == {"detail": "Nope"}


def test_field_validation_dict_returns_first_field_message(monkeypatch):
    """Field-error dictionaries return the first field and first message."""
    original = Response(
        {"email": ["This field is required."], "password": ["Too short."]},
        status=status.HTTP_400_BAD_REQUEST,
    )
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: original)

    response = handler.custom_exception_handler(Exception("x"), {})

    assert response.data == {"detail": "email: This field is required."}


def test_non_field_errors_return_plain_message(monkeypatch):
    """non_field_errors are rendered without the field-name prefix."""
    original = Response(
        {"non_field_errors": ["Invalid credentials."]},
        status=status.HTTP_400_BAD_REQUEST,
    )
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: original)

    response = handler.custom_exception_handler(Exception("x"), {})

    assert response.data == {"detail": "Invalid credentials."}


def test_list_and_string_payloads_are_normalized(monkeypatch):
    """List and string response payloads are converted to detail payloads."""
    list_response = Response(["First error", "Second error"], status=status.HTTP_400_BAD_REQUEST)
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: list_response)
    normalized_list = handler.custom_exception_handler(Exception("x"), {})
    assert normalized_list.data == {"detail": "First error"}

    string_response = Response("Bad request", status=status.HTTP_400_BAD_REQUEST)
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: string_response)
    normalized_string = handler.custom_exception_handler(Exception("y"), {})
    assert normalized_string.data == {"detail": "Bad request"}


def test_unknown_response_shape_falls_back_to_generic_message(monkeypatch):
    """Unexpected payload structures use generic fallback detail."""
    original = Response({"email": "invalid"}, status=status.HTTP_400_BAD_REQUEST)
    monkeypatch.setattr(handler, "exception_handler", lambda exc, context: original)

    response = handler.custom_exception_handler(Exception("x"), {})

    assert response.data == {"detail": "An error occurred"}
