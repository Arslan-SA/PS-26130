"""
Document Intelligence Pipeline (Fragments 65–72).

A single, cohesive processing pipeline that orchestrates:
  65. OCR text extraction from uploaded document bytes
  66. Heuristic document type classification
  67. Structured entity and field extraction (PAN, GSTIN, dates, company name)
  68. Document validation engine (legibility, completeness, format)
  69. Required-document matching against statutory approval checklists
  70. Missing-document detection per approval requirement
  71. Expiry date detection and status calculation
  72. Business profile cross-reference and mismatch flagging

All intelligence runs deterministically with zero external API calls in mock mode.
Results are stored back onto the Document DB record and returned as DocumentIntelligenceResult.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentType, DocumentVerificationStatus
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business_profile import BusinessProfile
from app.ocr.ocr_engine import get_ocr_adapter

logger = logging.getLogger("udyamsetu.doc_intelligence")


# ---------------------------------------------------------------------------
# Dataclass result types
# ---------------------------------------------------------------------------

@dataclass
class ExtractedFields:
    """Structured entities extracted from OCR text."""
    pan: Optional[str] = None
    gstin: Optional[str] = None
    company_name: Optional[str] = None
    cin: Optional[str] = None
    udyam_number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    raw_dates: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ValidationResult:
    """Outcome of the document validation engine."""
    is_legible: bool = True
    is_format_valid: bool = True
    is_complete: bool = True
    issues: List[str] = field(default_factory=list)
    overall_valid: bool = True


@dataclass
class ExpiryStatus:
    """Expiry detection result for a document."""
    has_expiry: bool = False
    expiry_date: Optional[date] = None
    days_remaining: Optional[int] = None
    is_expired: bool = False
    is_expiring_soon: bool = False   # within 30 days
    severity: str = "NONE"          # NONE | LOW | MEDIUM | HIGH | CRITICAL


@dataclass
class DocumentIntelligenceResult:
    """Aggregated output of the full intelligence pipeline for one document."""
    document_id: str
    detected_type: Optional[DocumentType] = None
    extracted_fields: Optional[ExtractedFields] = None
    validation: Optional[ValidationResult] = None
    expiry_status: Optional[ExpiryStatus] = None
    profile_mismatches: List[str] = field(default_factory=list)
    final_verification_status: DocumentVerificationStatus = DocumentVerificationStatus.PENDING
    processing_notes: str = ""


# ---------------------------------------------------------------------------
# Fragment 66 — Document Type Classifier
# ---------------------------------------------------------------------------

#: Keyword-to-DocumentType heuristics (priority order, first match wins)
_CLASSIFICATION_RULES: List[Tuple[DocumentType, List[str]]] = [
    (DocumentType.PAN_CARD,                 ["permanent account number", "income tax department", "pan:", "pan card"]),
    (DocumentType.GST_CERTIFICATE,          ["gstin:", "goods and services tax", "gst registration", "central tax"]),
    (DocumentType.UDYAM_REGISTRATION,       ["udyam registration", "udyam number", "msme", "ministry of micro"]),
    (DocumentType.CERTIFICATE_OF_INCORPORATION, ["certificate of incorporation", "cin:", "registrar of companies", "mca"]),
    (DocumentType.LAND_DEED_OR_LEASE,       ["sale deed", "lease agreement", "property", "stamp duty", "sub-registrar"]),
    (DocumentType.SITE_PLAN_LAYOUT,         ["site plan", "layout plan", "plot", "factory layout", "building plan"]),
    (DocumentType.ENVIRONMENTAL_MANAGEMENT_PLAN, ["environmental management plan", "emp", "pollution control", "effluent"]),
    (DocumentType.WATER_BALANCE_CHART,      ["water balance", "kld", "effluent treatment", "water consumption"]),
    (DocumentType.POWER_SANCTION_LETTER,    ["power sanction", "ht connection", "electrical inspector", "cea", "discom"]),
    (DocumentType.FIRE_SAFETY_PLAN,         ["fire safety", "fire noc", "fire prevention", "evacuation plan"]),
    (DocumentType.FACTORY_BUILDING_PLAN,    ["factory building", "building plan approval", "bye-law", "municipalities"]),
    (DocumentType.PROJECT_REPORT_DPR,       ["detailed project report", "dpr", "techno-economic", "feasibility report"]),
]


def classify_document_type(ocr_text: str) -> Optional[DocumentType]:
    """
    Classify document type from OCR text using keyword heuristics.
    Returns the best matching DocumentType, or None if no match.
    """
    text_lower = ocr_text.lower()
    for doc_type, keywords in _CLASSIFICATION_RULES:
        if any(kw in text_lower for kw in keywords):
            logger.debug("Classified document as %s", doc_type.value)
            return doc_type
    return None


# ---------------------------------------------------------------------------
# Fragment 67 — Entity & Field Extractor
# ---------------------------------------------------------------------------

# Regex patterns for Indian statutory identifiers
_PAN_RE       = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_GSTIN_RE     = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1})\b")
_CIN_RE       = re.compile(r"\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b")
_UDYAM_RE     = re.compile(r"\b(UDYAM-[A-Z]{2}-\d{2}-\d{7})\b", re.IGNORECASE)
_DATE_RE      = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w{3,9}\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2})\b"
)
_COMPANY_RE   = re.compile(
    r"(?:legal name|company name|name of company|firm name)[:\s]+([A-Z][A-Z\s&,.()-]{5,80})",
    re.IGNORECASE,
)


def _parse_date(raw: str) -> Optional[date]:
    """Attempt to parse a raw date string into a Python date object."""
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%d %B %Y", "%d %b %Y", "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_fields(ocr_text: str) -> ExtractedFields:
    """
    Extract structured entities from OCR text using regex patterns.
    Returns an ExtractedFields dataclass populated with matched values.
    """
    result = ExtractedFields()

    pan_matches = _PAN_RE.findall(ocr_text)
    if pan_matches:
        result.pan = pan_matches[0]

    gstin_matches = _GSTIN_RE.findall(ocr_text)
    if gstin_matches:
        result.gstin = gstin_matches[0]

    cin_matches = _CIN_RE.findall(ocr_text)
    if cin_matches:
        result.cin = cin_matches[0]

    udyam_matches = _UDYAM_RE.findall(ocr_text)
    if udyam_matches:
        result.udyam_number = udyam_matches[0].upper()

    company_matches = _COMPANY_RE.findall(ocr_text)
    if company_matches:
        result.company_name = company_matches[0].strip()

    raw_dates = _DATE_RE.findall(ocr_text)
    result.raw_dates = raw_dates[:5]  # keep first 5
    parsed_dates = [d for d in (_parse_date(r) for r in raw_dates) if d]
    if len(parsed_dates) >= 1:
        parsed_dates.sort()
        result.issue_date = parsed_dates[0]
        if len(parsed_dates) >= 2:
            result.expiry_date = parsed_dates[-1]

    # Confidence heuristic: count how many fields were extracted
    filled = sum([
        bool(result.pan), bool(result.gstin), bool(result.cin),
        bool(result.company_name), bool(result.issue_date),
    ])
    result.confidence = min(1.0, filled / 3.0)

    return result


# ---------------------------------------------------------------------------
# Fragment 68 — Document Validation Engine
# ---------------------------------------------------------------------------

MIN_OCR_TEXT_LENGTH = 30   # below this → illegible


def validate_document(
    ocr_text: str,
    detected_type: Optional[DocumentType],
    file_size_bytes: int,
    mime_type: str,
) -> ValidationResult:
    """
    Validate a document for legibility, format correctness, and completeness.

    Returns ValidationResult with a list of issues and an overall_valid flag.
    """
    issues: List[str] = []

    # Legibility check
    is_legible = len(ocr_text.strip()) >= MIN_OCR_TEXT_LENGTH
    if not is_legible:
        issues.append(
            "Document appears illegible or contains insufficient readable text. "
            "Please upload a higher resolution scan (minimum 200 DPI)."
        )

    # Format check: PDF preferred for statutory docs, warn for images
    is_format_valid = True
    if mime_type.startswith("image/") and detected_type not in (
        DocumentType.SITE_PLAN_LAYOUT, DocumentType.FACTORY_BUILDING_PLAN
    ):
        issues.append(
            "Uploading as a scanned image. For statutory documents, a PDF with embedded text "
            "is preferred for faster processing."
        )

    # Completeness: minimum file size (too small likely means a blank scan)
    is_complete = file_size_bytes > 5_000  # 5 KB minimum
    if not is_complete:
        issues.append(
            f"File size ({file_size_bytes} bytes) is suspiciously small. "
            "The document may be blank, corrupted, or improperly scanned."
        )

    overall_valid = is_legible and is_complete
    return ValidationResult(
        is_legible=is_legible,
        is_format_valid=is_format_valid,
        is_complete=is_complete,
        issues=issues,
        overall_valid=overall_valid,
    )


# ---------------------------------------------------------------------------
# Fragment 71 — Expiry Detection Engine
# ---------------------------------------------------------------------------

def compute_expiry_status(expiry_date: Optional[date]) -> ExpiryStatus:
    """
    Compute expiry risk status from a document's validity expiry date.

    Severity levels:
      NONE     → no expiry date found
      LOW      → expires in > 90 days
      MEDIUM   → expires in 31–90 days
      HIGH     → expires in 1–30 days
      CRITICAL → already expired
    """
    if not expiry_date:
        return ExpiryStatus(has_expiry=False, severity="NONE")

    today = date.today()
    days_remaining = (expiry_date - today).days
    is_expired = days_remaining < 0
    is_expiring_soon = 0 <= days_remaining <= 30

    if is_expired:
        severity = "CRITICAL"
    elif days_remaining <= 30:
        severity = "HIGH"
    elif days_remaining <= 90:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return ExpiryStatus(
        has_expiry=True,
        expiry_date=expiry_date,
        days_remaining=days_remaining,
        is_expired=is_expired,
        is_expiring_soon=is_expiring_soon,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# Fragment 72 — Profile Mismatch Detection
# ---------------------------------------------------------------------------

def detect_profile_mismatches(
    extracted: ExtractedFields,
    profile: BusinessProfile,
) -> List[str]:
    """
    Cross-reference extracted document fields against the business profile.
    Returns a list of human-readable mismatch descriptions.
    """
    mismatches: List[str] = []

    # PAN mismatch
    if extracted.pan and hasattr(profile, "business") and profile.business:
        biz = profile.business
        if biz.pan and extracted.pan != biz.pan:
            mismatches.append(
                f"PAN mismatch: document contains '{extracted.pan}' "
                f"but enterprise profile has '{biz.pan}'."
            )

    # GSTIN mismatch
    if extracted.gstin and hasattr(profile, "business") and profile.business:
        biz = profile.business
        if biz.gstin and extracted.gstin != biz.gstin:
            mismatches.append(
                f"GSTIN mismatch: document shows '{extracted.gstin}' "
                f"but profile has '{biz.gstin}'."
            )

    # CIN mismatch
    if extracted.cin and hasattr(profile, "business") and profile.business:
        biz = profile.business
        if biz.cin and extracted.cin != biz.cin:
            mismatches.append(
                f"CIN mismatch: document shows '{extracted.cin}' "
                f"but profile has '{biz.cin}'."
            )

    return mismatches


# ---------------------------------------------------------------------------
# Fragment 65 — Full OCR Processing Pipeline
# ---------------------------------------------------------------------------

async def run_document_intelligence(
    document: Document,
    raw_bytes: bytes,
    db: AsyncSession,
) -> DocumentIntelligenceResult:
    """
    Execute the full Document Intelligence pipeline for an uploaded document.

    Pipeline steps:
      1. OCR text extraction (Fragment 65)
      2. Document type classification (Fragment 66)
      3. Entity / field extraction (Fragment 67)
      4. Document validation (Fragment 68)
      5. Expiry status computation (Fragment 71)
      6. Business profile cross-reference (Fragment 72)
      7. Persist results back to Document record in DB

    Args:
        document:   SQLAlchemy Document ORM object (mutable — fields are written back).
        raw_bytes:  Raw file bytes read from storage.
        db:         Async SQLAlchemy session for persisting results.

    Returns:
        DocumentIntelligenceResult with all intelligence outputs.
    """
    result = DocumentIntelligenceResult(document_id=document.id)

    try:
        # Step 1 — OCR extraction
        logger.info("Starting OCR for document %s (%s)", document.id, document.mime_type)
        ocr_adapter = get_ocr_adapter()
        ocr_text = ocr_adapter.extract_text(raw_bytes, document.mime_type)
        document.ocr_raw_text = ocr_text

        # Step 2 — Type classification
        detected_type = classify_document_type(ocr_text)
        if detected_type and document.document_type == DocumentType.OTHER:
            document.document_type = detected_type
        result.detected_type = detected_type or document.document_type

        # Step 3 — Field extraction
        extracted = extract_fields(ocr_text)
        result.extracted_fields = extracted
        document.extracted_metadata = {
            "pan": extracted.pan,
            "gstin": extracted.gstin,
            "cin": extracted.cin,
            "udyam_number": extracted.udyam_number,
            "company_name": extracted.company_name,
            "confidence": extracted.confidence,
            "raw_dates": extracted.raw_dates,
        }

        # Step 4 — Validation
        validation = validate_document(
            ocr_text=ocr_text,
            detected_type=result.detected_type,
            file_size_bytes=document.file_size_bytes,
            mime_type=document.mime_type,
        )
        result.validation = validation

        # Step 5 — Expiry detection
        expiry_date = extracted.expiry_date
        if expiry_date:
            document.expiry_date = expiry_date
        if extracted.issue_date:
            document.issue_date = extracted.issue_date
        expiry_status = compute_expiry_status(expiry_date)
        result.expiry_status = expiry_status

        # Step 6 — Profile mismatch detection
        stmt_profile = select(BusinessProfile).where(
            BusinessProfile.business_id == document.business_id
        )
        profile = (await db.execute(stmt_profile)).scalar_one_or_none()
        if profile:
            mismatches = detect_profile_mismatches(extracted, profile)
            result.profile_mismatches = mismatches
        else:
            mismatches = []

        # Step 7 — Determine final verification status
        if not validation.overall_valid:
            final_status = DocumentVerificationStatus.FLAGGED
            notes = " | ".join(validation.issues)
        elif expiry_status.is_expired:
            final_status = DocumentVerificationStatus.FLAGGED
            notes = f"Document expired on {expiry_date}. Please renew and re-upload."
        elif mismatches:
            final_status = DocumentVerificationStatus.FLAGGED
            notes = " | ".join(mismatches)
        else:
            final_status = DocumentVerificationStatus.VERIFIED
            notes = "Document passed all automated validation checks."

        document.verification_status = final_status
        document.deficiency_notes = notes if final_status == DocumentVerificationStatus.FLAGGED else None
        result.final_verification_status = final_status
        result.processing_notes = notes

        await db.commit()
        await db.refresh(document)

        logger.info(
            "Document intelligence complete for %s: status=%s confidence=%.2f",
            document.id, final_status.value, extracted.confidence,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Document intelligence failed for %s: %s", document.id, exc, exc_info=True)
        document.verification_status = DocumentVerificationStatus.FLAGGED
        document.deficiency_notes = (
            "Automated processing encountered an error. Manual review required."
        )
        await db.commit()
        result.final_verification_status = DocumentVerificationStatus.FLAGGED
        result.processing_notes = str(exc)

    return result
