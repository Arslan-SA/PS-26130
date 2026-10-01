"""
Pydantic schemas for Document upload, retrieval, and listing (Fragments 61–62).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentType, DocumentVerificationStatus


class DocumentUploadResponse(BaseModel):
    """
    Response returned immediately after a successful document upload.
    Contains storage metadata and the initial PENDING verification status.
    """
    id: str = Field(..., description="Document UUID")
    business_id: str
    requirement_id: Optional[str] = None
    document_type: DocumentType
    file_name: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    verification_status: DocumentVerificationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    """Full document read response including OCR and metadata fields."""
    id: str
    business_id: str
    uploaded_by_user_id: Optional[str] = None
    requirement_id: Optional[str] = None
    document_type: DocumentType
    file_name: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    verification_status: DocumentVerificationStatus
    ocr_raw_text: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    deficiency_notes: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Paginated list of documents belonging to a business."""
    total: int
    documents: List[DocumentRead]
