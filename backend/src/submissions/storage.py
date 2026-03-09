"""Storage abstraction for submission images (FR-15 IMG-CN-15)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class ImageStorageBackend(ABC):
    """Abstract interface for image storage."""

    @abstractmethod
    def store(self, key: str, data: bytes) -> None:
        """Write data to the storage backend at the given key."""

    @abstractmethod
    def retrieve(self, key: str) -> bytes:
        """Read data from the storage backend. Raises FileNotFoundError if missing."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete data at the given key. Idempotent — missing keys are a no-op."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check whether a key exists in the storage backend."""


class LocalStorageBackend(ImageStorageBackend):
    """Local filesystem storage using MEDIA_ROOT."""

    def __init__(self, base_path: Path | None = None):
        self._base = base_path or Path(settings.MEDIA_ROOT)

    def _full_path(self, key: str) -> Path:
        return self._base / key

    def store(self, key: str, data: bytes) -> None:
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def retrieve(self, key: str) -> bytes:
        path = self._full_path(key)
        if not path.exists():
            raise FileNotFoundError(f"Blob not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._full_path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            logger.warning("Blob already missing during delete: %s", key)

    def exists(self, key: str) -> bool:
        return self._full_path(key).exists()


def get_storage_backend() -> ImageStorageBackend:
    """Return the configured storage backend (local filesystem for now)."""
    return LocalStorageBackend()
