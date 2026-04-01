"""Storage abstraction for submission images (FR-15 IMG-CN-15).

Re-exports from core.media.storage for backward compatibility.
"""

from core.media.storage import (  # noqa: F401
    ImageStorageBackend,
    LocalStorageBackend,
    get_storage_backend,
)
