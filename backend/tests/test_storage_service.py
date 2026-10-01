"""
Test suite for Document Storage Service (Fragment 60).
Covers: MIME validation, extension guard, size enforcement,
        SHA-256 integrity, path generation, Local adapter CRUD,
        and StorageService store/retrieve/delete lifecycle.
"""

import hashlib
import tempfile
from pathlib import Path

import pytest

from app.services.storage_service import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_DOCUMENT_SIZE_BYTES,
    LocalStorageAdapter,
    StorageService,
    StorageValidationError,
    build_storage_path,
    compute_sha256,
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_storage(tmp_path: Path) -> LocalStorageAdapter:
    """Return a LocalStorageAdapter backed by a temporary directory."""
    return LocalStorageAdapter(base_dir=str(tmp_path))


@pytest.fixture
def tmp_service(tmp_path: Path) -> StorageService:
    """Return a StorageService using a LocalStorageAdapter in a temp dir."""
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    return StorageService(adapter=adapter)


SAMPLE_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing" + b"\x00" * 10
SAMPLE_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake png data" * 5
BUSINESS_ID = "biz-test-1234-uuid"


# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------

class TestComputeSha256:
    def test_known_digest(self):
        data = b"hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert compute_sha256(data) == expected

    def test_returns_64_hex_chars(self):
        result = compute_sha256(b"udyamsetu regulatory document data")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_differ(self):
        assert compute_sha256(b"doc_a") != compute_sha256(b"doc_b")


# ---------------------------------------------------------------------------
# validate_mime_type
# ---------------------------------------------------------------------------

class TestValidateMimeType:
    def test_accepts_pdf(self):
        validate_mime_type("application/pdf")  # no exception

    def test_accepts_jpeg(self):
        validate_mime_type("image/jpeg")

    def test_accepts_png(self):
        validate_mime_type("image/png")

    def test_accepts_docx(self):
        validate_mime_type(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_rejects_zip(self):
        with pytest.raises(StorageValidationError, match="not permitted"):
            validate_mime_type("application/zip")

    def test_rejects_executable(self):
        with pytest.raises(StorageValidationError):
            validate_mime_type("application/x-msdownload")

    def test_rejects_text_html(self):
        with pytest.raises(StorageValidationError):
            validate_mime_type("text/html")


# ---------------------------------------------------------------------------
# validate_file_size
# ---------------------------------------------------------------------------

class TestValidateFileSize:
    def test_accepts_within_limit(self):
        validate_file_size(1024)  # 1 KB — no exception

    def test_accepts_exactly_at_limit(self):
        validate_file_size(MAX_DOCUMENT_SIZE_BYTES)

    def test_rejects_over_limit(self):
        with pytest.raises(StorageValidationError, match="exceeds the maximum"):
            validate_file_size(MAX_DOCUMENT_SIZE_BYTES + 1)

    def test_error_shows_mb_values(self):
        with pytest.raises(StorageValidationError, match="MB"):
            validate_file_size(MAX_DOCUMENT_SIZE_BYTES + 1)


# ---------------------------------------------------------------------------
# validate_file_extension
# ---------------------------------------------------------------------------

class TestValidateFileExtension:
    def test_accepts_pdf(self):
        validate_file_extension("cte_approval.pdf")

    def test_accepts_uppercase_extension(self):
        validate_file_extension("PAN_CARD.JPEG")  # normalized to lowercase internally

    def test_rejects_exe(self):
        with pytest.raises(StorageValidationError):
            validate_file_extension("malware.exe")

    def test_rejects_sh(self):
        with pytest.raises(StorageValidationError):
            validate_file_extension("setup.sh")

    def test_rejects_no_extension(self):
        with pytest.raises(StorageValidationError):
            validate_file_extension("nodot")


# ---------------------------------------------------------------------------
# build_storage_path
# ---------------------------------------------------------------------------

class TestBuildStoragePath:
    def test_path_starts_with_business(self):
        path = build_storage_path("biz-abc", "myfile.pdf")
        assert path.startswith("business/biz-abc/")

    def test_path_ends_with_pdf_extension(self):
        path = build_storage_path("biz-abc", "certificate.pdf")
        assert path.endswith(".pdf")

    def test_unique_paths_for_same_file(self):
        p1 = build_storage_path("biz-abc", "doc.pdf")
        p2 = build_storage_path("biz-abc", "doc.pdf")
        assert p1 != p2  # UUID4 guarantee

    def test_path_contains_business_id(self):
        biz = "enterprise-12345"
        path = build_storage_path(biz, "plan.png")
        assert biz in path


# ---------------------------------------------------------------------------
# LocalStorageAdapter
# ---------------------------------------------------------------------------

class TestLocalStorageAdapter:
    def test_save_and_load(self, tmp_storage: LocalStorageAdapter):
        path = f"business/{BUSINESS_ID}/test.pdf"
        tmp_storage.save(path, SAMPLE_PDF_BYTES)
        loaded = tmp_storage.load(path)
        assert loaded == SAMPLE_PDF_BYTES

    def test_exists_after_save(self, tmp_storage: LocalStorageAdapter):
        path = "business/biz/exist_check.pdf"
        assert not tmp_storage.exists(path)
        tmp_storage.save(path, SAMPLE_PDF_BYTES)
        assert tmp_storage.exists(path)

    def test_delete_removes_file(self, tmp_storage: LocalStorageAdapter):
        path = "business/biz/to_delete.pdf"
        tmp_storage.save(path, SAMPLE_PDF_BYTES)
        result = tmp_storage.delete(path)
        assert result is True
        assert not tmp_storage.exists(path)

    def test_delete_nonexistent_returns_false(self, tmp_storage: LocalStorageAdapter):
        result = tmp_storage.delete("business/biz/ghost.pdf")
        assert result is False

    def test_load_raises_if_missing(self, tmp_storage: LocalStorageAdapter):
        with pytest.raises(FileNotFoundError):
            tmp_storage.load("business/biz/does_not_exist.pdf")

    def test_save_creates_nested_directories(self, tmp_storage: LocalStorageAdapter):
        deep_path = "business/deep/nested/path/doc.pdf"
        tmp_storage.save(deep_path, SAMPLE_PDF_BYTES)
        assert tmp_storage.exists(deep_path)


# ---------------------------------------------------------------------------
# StorageService.store + retrieve + delete
# ---------------------------------------------------------------------------

class TestStorageService:
    def test_store_pdf_success(self, tmp_service: StorageService):
        path, checksum, size = tmp_service.store(
            business_id=BUSINESS_ID,
            filename="cte_consent.pdf",
            mime_type="application/pdf",
            data=SAMPLE_PDF_BYTES,
        )
        assert path.startswith(f"business/{BUSINESS_ID}/")
        assert path.endswith(".pdf")
        assert checksum == compute_sha256(SAMPLE_PDF_BYTES)
        assert size == len(SAMPLE_PDF_BYTES)

    def test_store_png_success(self, tmp_service: StorageService):
        path, checksum, size = tmp_service.store(
            business_id=BUSINESS_ID,
            filename="site_plan.png",
            mime_type="image/png",
            data=SAMPLE_PNG_BYTES,
        )
        assert path.endswith(".png")

    def test_store_rejects_zip_mime(self, tmp_service: StorageService):
        with pytest.raises(StorageValidationError, match="not permitted"):
            tmp_service.store(
                business_id=BUSINESS_ID,
                filename="archive.zip",
                mime_type="application/zip",
                data=b"fake zip data",
            )

    def test_store_rejects_oversized_file(self, tmp_service: StorageService):
        huge = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)
        with pytest.raises(StorageValidationError, match="exceeds the maximum"):
            tmp_service.store(
                business_id=BUSINESS_ID,
                filename="huge.pdf",
                mime_type="application/pdf",
                data=huge,
            )

    def test_retrieve_matches_original(self, tmp_service: StorageService):
        path, _, _ = tmp_service.store(
            business_id=BUSINESS_ID,
            filename="pan_card.pdf",
            mime_type="application/pdf",
            data=SAMPLE_PDF_BYTES,
        )
        retrieved = tmp_service.retrieve(path)
        assert retrieved == SAMPLE_PDF_BYTES

    def test_delete_after_store(self, tmp_service: StorageService):
        path, _, _ = tmp_service.store(
            business_id=BUSINESS_ID,
            filename="temp.pdf",
            mime_type="application/pdf",
            data=SAMPLE_PDF_BYTES,
        )
        assert tmp_service.exists(path)
        result = tmp_service.delete(path)
        assert result is True
        assert not tmp_service.exists(path)

    def test_integrity_sha256_is_deterministic(self, tmp_service: StorageService):
        """Same data uploaded twice should produce the same SHA-256 hash."""
        _, c1, _ = tmp_service.store(BUSINESS_ID, "a.pdf", "application/pdf", SAMPLE_PDF_BYTES)
        _, c2, _ = tmp_service.store(BUSINESS_ID, "b.pdf", "application/pdf", SAMPLE_PDF_BYTES)
        assert c1 == c2
