"""
Test suite for Document Intelligence Pipeline (Fragments 65–72).
Covers: OCR extraction, type classification, entity extraction,
        document validation, expiry detection, profile mismatch detection,
        and full pipeline orchestration.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.document_intelligence import (
    ExpiryStatus,
    ExtractedFields,
    classify_document_type,
    compute_expiry_status,
    detect_profile_mismatches,
    extract_fields,
    validate_document,
)
from app.models.document import DocumentType
from app.ocr.ocr_engine import MockOCRAdapter, get_ocr_adapter


# ---------------------------------------------------------------------------
# Fragment 64 — OCR Engine Tests
# ---------------------------------------------------------------------------

class TestOCREngine:
    def test_mock_adapter_pdf_returns_text(self):
        adapter = MockOCRAdapter()
        result = adapter.extract_text(b"fake pdf", "application/pdf")
        assert "PAN:" in result
        assert len(result) > 20

    def test_mock_adapter_image_returns_text(self):
        adapter = MockOCRAdapter()
        result = adapter.extract_text(b"fake img", "image/jpeg")
        assert "GSTIN:" in result

    def test_mock_adapter_other_returns_text(self):
        adapter = MockOCRAdapter()
        result = adapter.extract_text(b"fake doc", "application/pdf")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_ocr_adapter_returns_mock_by_default(self):
        adapter = get_ocr_adapter()
        assert isinstance(adapter, MockOCRAdapter)


# ---------------------------------------------------------------------------
# Fragment 66 — Document Type Classification Tests
# ---------------------------------------------------------------------------

class TestDocumentClassification:
    def test_classifies_pan_card(self):
        text = "PERMANENT ACCOUNT NUMBER CARD\nPAN: AAACB1234F\nIncome Tax Department"
        result = classify_document_type(text)
        assert result == DocumentType.PAN_CARD

    def test_classifies_gst_certificate(self):
        text = "GSTIN: 27AAACB1234F1Z5\nGoods and Services Tax Registration Certificate"
        result = classify_document_type(text)
        assert result == DocumentType.GST_CERTIFICATE

    def test_classifies_udyam(self):
        text = "UDYAM REGISTRATION CERTIFICATE\nMinistry of Micro Small and Medium Enterprises"
        result = classify_document_type(text)
        assert result == DocumentType.UDYAM_REGISTRATION

    def test_classifies_certificate_of_incorporation(self):
        text = "Certificate of Incorporation\nCIN: U27100MH2020PTC345678\nRegistrar of Companies"
        result = classify_document_type(text)
        assert result == DocumentType.CERTIFICATE_OF_INCORPORATION

    def test_classifies_fire_safety(self):
        text = "FIRE NOC\nFire Safety Plan and Evacuation Plan submitted"
        result = classify_document_type(text)
        assert result == DocumentType.FIRE_SAFETY_PLAN

    def test_returns_none_for_unknown(self):
        result = classify_document_type("random text with no keywords")
        assert result is None

    def test_case_insensitive(self):
        text = "permanent account number card income tax department pan:"
        result = classify_document_type(text)
        assert result == DocumentType.PAN_CARD


# ---------------------------------------------------------------------------
# Fragment 67 — Entity Extraction Tests
# ---------------------------------------------------------------------------

class TestFieldExtraction:
    def test_extracts_pan(self):
        result = extract_fields("PAN: AAACB1234F\nSome other text")
        assert result.pan == "AAACB1234F"

    def test_extracts_gstin(self):
        result = extract_fields("GSTIN: 27AAACB1234F1Z5 Maharashtra")
        assert result.gstin == "27AAACB1234F1Z5"

    def test_extracts_cin(self):
        result = extract_fields("CIN: U27100MH2020PTC345678 MCA")
        assert result.cin == "U27100MH2020PTC345678"

    def test_extracts_udyam_number(self):
        result = extract_fields("Udyam Number: UDYAM-MH-01-0012345")
        assert result.udyam_number == "UDYAM-MH-01-0012345"

    def test_extracts_dates(self):
        result = extract_fields("Issue Date: 15/08/2020 Expiry Date: 14/08/2025")
        assert len(result.raw_dates) >= 2

    def test_extracts_company_name(self):
        result = extract_fields("Legal Name: BHARAT STEEL AND ALLOYS PRIVATE LIMITED")
        assert result.company_name and "BHARAT STEEL" in result.company_name

    def test_confidence_increases_with_more_fields(self):
        sparse = extract_fields("random text no identifiers")
        rich = extract_fields(
            "PAN: AAACB1234F\nGSTIN: 27AAACB1234F1Z5\n"
            "Legal Name: BHARAT STEEL AND ALLOYS\n15/08/2020"
        )
        assert rich.confidence > sparse.confidence

    def test_empty_text_returns_empty_fields(self):
        result = extract_fields("")
        assert result.pan is None
        assert result.gstin is None
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Fragment 68 — Validation Engine Tests
# ---------------------------------------------------------------------------

class TestDocumentValidation:
    def test_valid_pdf_passes(self):
        result = validate_document(
            ocr_text="Sufficient OCR text that is long enough to pass the legibility check " * 2,
            detected_type=DocumentType.PAN_CARD,
            file_size_bytes=50_000,
            mime_type="application/pdf",
        )
        assert result.is_legible
        assert result.is_complete
        assert result.overall_valid

    def test_empty_ocr_fails_legibility(self):
        result = validate_document(
            ocr_text="",
            detected_type=None,
            file_size_bytes=50_000,
            mime_type="application/pdf",
        )
        assert not result.is_legible
        assert not result.overall_valid
        assert any("illegible" in i.lower() for i in result.issues)

    def test_tiny_file_fails_completeness(self):
        result = validate_document(
            ocr_text="PAN card text " * 5,
            detected_type=DocumentType.PAN_CARD,
            file_size_bytes=100,    # 100 bytes — below 5KB threshold
            mime_type="application/pdf",
        )
        assert not result.is_complete
        assert not result.overall_valid

    def test_image_format_adds_warning(self):
        result = validate_document(
            ocr_text="Sufficient text content here which is long enough to pass checks " * 2,
            detected_type=DocumentType.PAN_CARD,
            file_size_bytes=200_000,
            mime_type="image/jpeg",
        )
        # Should add format warning but still valid if text is legible and size ok
        assert any("PDF" in i for i in result.issues)


# ---------------------------------------------------------------------------
# Fragment 71 — Expiry Detection Tests
# ---------------------------------------------------------------------------

class TestExpiryDetection:
    def test_no_expiry_date_returns_none_severity(self):
        result = compute_expiry_status(None)
        assert result.has_expiry is False
        assert result.severity == "NONE"
        assert result.is_expired is False

    def test_far_future_expiry_returns_low(self):
        future = date.today() + timedelta(days=180)
        result = compute_expiry_status(future)
        assert result.severity == "LOW"
        assert not result.is_expired

    def test_medium_risk_31_to_90_days(self):
        soon = date.today() + timedelta(days=60)
        result = compute_expiry_status(soon)
        assert result.severity == "MEDIUM"

    def test_high_risk_within_30_days(self):
        soon = date.today() + timedelta(days=15)
        result = compute_expiry_status(soon)
        assert result.severity == "HIGH"
        assert result.is_expiring_soon

    def test_expired_document_critical(self):
        expired = date.today() - timedelta(days=5)
        result = compute_expiry_status(expired)
        assert result.is_expired
        assert result.severity == "CRITICAL"
        assert result.days_remaining < 0


# ---------------------------------------------------------------------------
# Fragment 72 — Profile Mismatch Detection Tests
# ---------------------------------------------------------------------------

class TestProfileMismatch:
    def _make_profile(self, pan="AAACB1234F", gstin="27AAACB1234F1Z5", cin=None):
        business = MagicMock()
        business.pan = pan
        business.gstin = gstin
        business.cin = cin
        profile = MagicMock()
        profile.business = business
        return profile

    def test_no_mismatches_when_fields_match(self):
        profile = self._make_profile(pan="AAACB1234F", gstin="27AAACB1234F1Z5")
        extracted = ExtractedFields(pan="AAACB1234F", gstin="27AAACB1234F1Z5")
        mismatches = detect_profile_mismatches(extracted, profile)
        assert mismatches == []

    def test_detects_pan_mismatch(self):
        profile = self._make_profile(pan="AAACB1234F")
        extracted = ExtractedFields(pan="BBBBB9999Z")
        mismatches = detect_profile_mismatches(extracted, profile)
        assert any("PAN mismatch" in m for m in mismatches)

    def test_detects_gstin_mismatch(self):
        profile = self._make_profile(gstin="27AAACB1234F1Z5")
        extracted = ExtractedFields(gstin="29XYZAB5678C1Z3")
        mismatches = detect_profile_mismatches(extracted, profile)
        assert any("GSTIN mismatch" in m for m in mismatches)

    def test_no_mismatch_if_extracted_field_is_none(self):
        """If the document doesn't contain a field, no mismatch should be raised."""
        profile = self._make_profile(pan="AAACB1234F")
        extracted = ExtractedFields(pan=None)  # Field not found in document
        mismatches = detect_profile_mismatches(extracted, profile)
        assert mismatches == []
