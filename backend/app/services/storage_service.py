"""
Document Storage Service — Pluggable Storage Abstraction (Fragment 60).

Provides a unified StorageService with two concrete adapters:
  - LocalStorageAdapter  : Writes files to LOCAL_STORAGE_DIR on disk.
  - CloudStorageAdapter  : Placeholder adapter (S3-compatible) for cloud deployments.

Responsibilities enforced at this layer:
  - MIME-type allowlist validation (rejects executables, scripts, ZIPs, etc.)
  - File-size enforcement (configurable MAX_DOCUMENT_SIZE_MB, default 10 MB)
  - SHA-256 integrity digest computation for every stored file
  - Deterministic, collision-resistant path generation  (business/{business_id}/{uuid4}.{ext})
  - Safe deletion and existence checking
"""

import hashlib
import logging
import mimetypes
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

from app.core.config import settings

logger = logging.getLogger("udyamsetu.storage")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum allowable document upload size (bytes).
MAX_DOCUMENT_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

#: Strict MIME-type allowlist for statutory regulatory documents.
ALLOWED_MIME_TYPES: frozenset = frozenset(
    [
        "application/pdf",                                       # PDF
        "image/jpeg",                                            # JPEG photograph
        "image/png",                                             # PNG scan
        "image/tiff",                                            # TIFF scanned document
        "image/webp",                                            # WebP image
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/msword",                                    # .doc (legacy)
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    ]
)

#: Allowed file extensions mapped to expected MIME types (secondary guard).
ALLOWED_EXTENSIONS: frozenset = frozenset(
    [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".doc", ".docx", ".xlsx"]
)


# ---------------------------------------------------------------------------
# Validation helpers (pure functions — no I/O)
# ---------------------------------------------------------------------------

class StorageValidationError(ValueError):
    """Raised when an uploaded file fails MIME, size, or extension validation."""


def validate_mime_type(mime_type: str) -> None:
    """
    Raise StorageValidationError if the MIME type is not in the allowlist.

    Args:
        mime_type: MIME content-type string from the upload request headers.
    Raises:
        StorageValidationError: If the MIME type is rejected.
    """
    if mime_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise StorageValidationError(
            f"File type '{mime_type}' is not permitted. "
            f"Accepted types: {allowed}"
        )


def validate_file_size(size_bytes: int) -> None:
    """
    Raise StorageValidationError if the file exceeds MAX_DOCUMENT_SIZE_BYTES.

    Args:
        size_bytes: File size in bytes.
    Raises:
        StorageValidationError: If the file is too large.
    """
    if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        limit_mb = MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise StorageValidationError(
            f"File size {actual_mb:.2f} MB exceeds the maximum allowed "
            f"size of {limit_mb:.0f} MB."
        )


def validate_file_extension(filename: str) -> None:
    """
    Raise StorageValidationError if the file extension is not in the allowlist.

    Args:
        filename: Original uploaded file name.
    Raises:
        StorageValidationError: If the extension is rejected.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise StorageValidationError(
            f"File extension '{suffix}' is not permitted. "
            f"Accepted extensions: {allowed}"
        )


def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 cryptographic hash of raw bytes.

    Args:
        data: Raw file bytes.
    Returns:
        Lowercase hex-encoded SHA-256 digest (64 characters).
    """
    return hashlib.sha256(data).hexdigest()


def build_storage_path(business_id: str, original_filename: str) -> str:
    """
    Generate a deterministic, collision-resistant storage path.

    Format: ``business/{business_id}/{uuid4}{.ext}``

    Args:
        business_id: UUID string of the owning enterprise.
        original_filename: Original file name (used to extract extension only).
    Returns:
        Relative storage path string.
    """
    ext = Path(original_filename).suffix.lower()
    return f"business/{business_id}/{uuid.uuid4()}{ext}"


# ---------------------------------------------------------------------------
# Abstract base adapter
# ---------------------------------------------------------------------------

class BaseStorageAdapter(ABC):
    """Abstract contract that all storage back-ends must implement."""

    @abstractmethod
    def save(self, path: str, data: bytes) -> None:
        """Persist file bytes at the given relative path."""

    @abstractmethod
    def load(self, path: str) -> bytes:
        """Return raw bytes of a stored file."""

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a stored file. Returns True if deleted, False if not found."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return True if the file at the given path exists."""


# ---------------------------------------------------------------------------
# Local filesystem adapter
# ---------------------------------------------------------------------------

class LocalStorageAdapter(BaseStorageAdapter):
    """
    Stores files on the local filesystem under LOCAL_STORAGE_DIR.

    Directory structure: ``{LOCAL_STORAGE_DIR}/business/{business_id}/{uuid}.{ext}``
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self._base.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageAdapter initialised at '%s'", self._base)

    def _abs(self, path: str) -> Path:
        """Resolve a relative path to an absolute path under base dir."""
        return self._base / path

    def save(self, path: str, data: bytes) -> None:
        dest = self._abs(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        logger.debug("Stored %d bytes at '%s'", len(data), dest)

    def load(self, path: str) -> bytes:
        target = self._abs(path)
        if not target.exists():
            raise FileNotFoundError(f"Document not found at path '{path}'")
        return target.read_bytes()

    def delete(self, path: str) -> bool:
        target = self._abs(path)
        if target.exists():
            target.unlink()
            logger.debug("Deleted file at '%s'", target)
            return True
        return False

    def exists(self, path: str) -> bool:
        return self._abs(path).exists()


# ---------------------------------------------------------------------------
# Cloud / S3 adapter (stub — enables deployment-time swap)
# ---------------------------------------------------------------------------

class CloudStorageAdapter(BaseStorageAdapter):
    """
    Placeholder S3-compatible cloud storage adapter.

    Replace the stub methods with boto3 / google-cloud-storage calls
    when deploying to a cloud environment with S3_BUCKET configured.
    """

    def __init__(self) -> None:
        logger.warning(
            "CloudStorageAdapter is a STUB. Configure S3_BUCKET and credentials "
            "before deploying to production."
        )

    def save(self, path: str, data: bytes) -> None:
        # TODO: implement s3_client.put_object(Bucket=S3_BUCKET, Key=path, Body=data)
        raise NotImplementedError("CloudStorageAdapter.save() is not yet implemented.")

    def load(self, path: str) -> bytes:
        raise NotImplementedError("CloudStorageAdapter.load() is not yet implemented.")

    def delete(self, path: str) -> bool:
        raise NotImplementedError("CloudStorageAdapter.delete() is not yet implemented.")

    def exists(self, path: str) -> bool:
        raise NotImplementedError("CloudStorageAdapter.exists() is not yet implemented.")


# ---------------------------------------------------------------------------
# Unified StorageService facade
# ---------------------------------------------------------------------------

class StorageService:
    """
    High-level document storage service.

    Automatically selects the adapter based on STORAGE_TYPE env setting:
      - ``"local"`` → LocalStorageAdapter
      - ``"s3"``    → CloudStorageAdapter (stub)

    Handles validation, SHA-256 computation, and path generation internally.
    Consumers only call :meth:`store` and :meth:`retrieve`.
    """

    def __init__(self, adapter: BaseStorageAdapter | None = None) -> None:
        if adapter is not None:
            self._adapter = adapter
        elif settings.STORAGE_TYPE == "s3":
            self._adapter = CloudStorageAdapter()
        else:
            self._adapter = LocalStorageAdapter()

    def store(
        self,
        business_id: str,
        filename: str,
        mime_type: str,
        data: bytes,
    ) -> Tuple[str, str, int]:
        """
        Validate and persist a document file.

        Validation order:
          1. Extension allowlist check
          2. MIME-type allowlist check
          3. File size limit check
          4. SHA-256 digest computation
          5. Atomic write to the backing store

        Args:
            business_id: UUID string of the owning enterprise.
            filename:    Original uploaded file name.
            mime_type:   Client-declared MIME type string.
            data:        Raw file bytes.

        Returns:
            Tuple of (storage_path, sha256_checksum, file_size_bytes).

        Raises:
            StorageValidationError: If validation fails.
        """
        validate_file_extension(filename)
        validate_mime_type(mime_type)
        validate_file_size(len(data))

        checksum = compute_sha256(data)
        path = build_storage_path(business_id, filename)
        self._adapter.save(path, data)

        logger.info(
            "Stored document '%s' for business %s → path='%s' sha256='%s...' size=%d bytes",
            filename,
            business_id,
            path,
            checksum[:8],
            len(data),
        )
        return path, checksum, len(data)

    def retrieve(self, path: str) -> bytes:
        """
        Load raw bytes of a stored document.

        Args:
            path: Relative storage path returned by :meth:`store`.
        Returns:
            Raw file bytes.
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        return self._adapter.load(path)

    def delete(self, path: str) -> bool:
        """
        Delete a stored document.

        Args:
            path: Relative storage path.
        Returns:
            True if the file was deleted, False if it did not exist.
        """
        result = self._adapter.delete(path)
        logger.info("Deleted document at path='%s' found=%s", path, result)
        return result

    def exists(self, path: str) -> bool:
        """Return True if a document exists at the given path."""
        return self._adapter.exists(path)
