"""
Document Processing Trigger API (Fragment 74).

Endpoint:
  POST /documents/{document_id}/process — Trigger full Document Intelligence pipeline.

This endpoint:
  1. Loads the document from DB
  2. Reads raw bytes from StorageService
  3. Runs the full intelligence pipeline (OCR → classify → extract → validate → expiry → mismatch)
  4. Returns the processing result immediately (synchronous for SIH demo scale)

In a production system this would enqueue a Celery/ARQ task and return 202 Accepted.
For SIH demo we run synchronously and return 200 with the full result.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.business import Business
from app.models.document import Document, DocumentVerificationStatus
from app.models.user import User, UserRole
from app.services.document_intelligence import DocumentIntelligenceResult, run_document_intelligence
from app.services.storage_service import StorageService

logger = logging.getLogger("udyamsetu.api.doc_processing")

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


# ---------------------------------------------------------------------------
# Response Schema
# ---------------------------------------------------------------------------

class ProcessingResponse(BaseModel):
    document_id: str
    verification_status: DocumentVerificationStatus
    detected_type: Optional[str] = None
    confidence: Optional[float] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    expiry_severity: Optional[str] = None
    days_remaining: Optional[int] = None
    profile_mismatches: List[str] = []
    processing_notes: str = ""
    success: bool = True

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/process
# ---------------------------------------------------------------------------

@router.post(
    "/{document_id}/process",
    response_model=ProcessingResponse,
    summary="Trigger Document Intelligence pipeline for an uploaded document (Fragment 74)",
)
async def process_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingResponse:
    """
    Run the full Document Intelligence pipeline on an already-uploaded document:
      - OCR text extraction
      - Automatic document type classification
      - Entity extraction (PAN, GSTIN, CIN, dates)
      - Validation (legibility, completeness)
      - Expiry detection
      - Business profile cross-reference

    Sets verification_status to VERIFIED or FLAGGED based on results.
    Returns the processing summary.

    **Authorization:** INDUSTRY_USER may only process their own business documents.
    DEPARTMENT_OFFICER and ADMIN may process any document.
    """
    # Load document
    stmt = select(Document).where(Document.id == document_id, Document.is_active == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise NotFoundError(message=f"Document '{document_id}' not found.")

    # Ownership check
    biz_stmt = select(Business).where(Business.id == doc.business_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()
    if business and current_user.role == UserRole.INDUSTRY_USER:
        if business.user_id != current_user.id:
            raise AuthorizationError(message="Not authorized to process this document.")

    # Mark as PROCESSING immediately
    doc.verification_status = DocumentVerificationStatus.PROCESSING
    await db.commit()

    # Load file bytes from storage
    storage = StorageService()
    try:
        raw_bytes = storage.retrieve(doc.storage_path)
    except FileNotFoundError:
        doc.verification_status = DocumentVerificationStatus.FLAGGED
        doc.deficiency_notes = "Physical file not found in storage. Please re-upload the document."
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage. The document may need to be re-uploaded.",
        )

    # Run intelligence pipeline
    result: DocumentIntelligenceResult = await run_document_intelligence(
        document=doc,
        raw_bytes=raw_bytes,
        db=db,
    )

    # Build response
    expiry = result.expiry_status
    extracted = result.extracted_fields

    return ProcessingResponse(
        document_id=document_id,
        verification_status=result.final_verification_status,
        detected_type=result.detected_type.value if result.detected_type else None,
        confidence=extracted.confidence if extracted else None,
        extracted_fields={
            "pan": extracted.pan,
            "gstin": extracted.gstin,
            "cin": extracted.cin,
            "udyam_number": extracted.udyam_number,
            "company_name": extracted.company_name,
        } if extracted else None,
        expiry_severity=expiry.severity if expiry else None,
        days_remaining=expiry.days_remaining if expiry else None,
        profile_mismatches=result.profile_mismatches,
        processing_notes=result.processing_notes,
        success=result.final_verification_status == DocumentVerificationStatus.VERIFIED,
    )
