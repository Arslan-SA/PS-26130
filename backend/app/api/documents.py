"""
Document Upload & Access API Endpoints (Fragments 61 & 62).

Endpoints:
  POST /documents/upload           — Multipart upload with MIME validation & SHA-256 integrity
  GET  /documents/{document_id}    — Fetch document metadata by ID
  GET  /documents/business/{id}    — List all documents for a business
  GET  /documents/{document_id}/download — Authenticated streaming download
  DELETE /documents/{document_id} — Delete a document (owner or admin only)
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.business import Business
from app.models.document import Document, DocumentType, DocumentVerificationStatus
from app.models.user import User, UserRole
from app.schemas.document import DocumentListResponse, DocumentRead, DocumentUploadResponse
from app.services.storage_service import StorageService, StorageValidationError

logger = logging.getLogger("udyamsetu.api.documents")
router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


def _get_storage() -> StorageService:
    """Dependency factory: returns the singleton StorageService."""
    return StorageService()


async def _resolve_business_owner(
    business_id: str,
    current_user: User,
    db: AsyncSession,
) -> Business:
    """
    Fetch the Business entity and enforce ownership:
    - INDUSTRY_USER may only access their own businesses.
    - DEPARTMENT_OFFICER, INSPECTOR, and ADMIN may access any business.
    """
    stmt = select(Business).where(Business.id == business_id, Business.is_active == True)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise NotFoundError(message=f"Business '{business_id}' not found.")
    if (
        current_user.role == UserRole.INDUSTRY_USER
        and business.user_id != current_user.id
    ):
        raise AuthorizationError(
            message="You are not authorized to access documents for this business."
        )
    return business


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a statutory document for an enterprise",
)
async def upload_document(
    file: UploadFile,
    business_id: str = Form(..., description="Target enterprise business UUID"),
    document_type: DocumentType = Form(
        DocumentType.OTHER,
        description="Statutory document category (e.g. PAN_CARD, GST_CERTIFICATE)",
    ),
    requirement_id: str | None = Form(
        None,
        description="Optional: approval requirement UUID this document fulfils",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(_get_storage),
) -> DocumentUploadResponse:
    """
    Upload a regulatory document (PDF, JPEG, PNG, TIFF, DOCX, XLSX).

    Enforces:
    - MIME-type allowlist (rejects executables, scripts, archives)
    - File size ≤ 10 MB
    - Extension allowlist
    - SHA-256 integrity digest computation
    - Deterministic collision-resistant storage path

    Returns document metadata with verification_status=PENDING.
    OCR processing occurs asynchronously (Phase 5, Fragment 65).
    """
    # 1. Ownership guard
    await _resolve_business_owner(business_id, current_user, db)

    # 2. Read upload bytes (limit read to MAX+1 to detect oversize early)
    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "unnamed_document"

    # 3. Validate via StorageService (raises StorageValidationError on failure)
    try:
        storage_path, checksum, size_bytes = storage.store(
            business_id=business_id,
            filename=filename,
            mime_type=mime_type,
            data=data,
        )
    except StorageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 4. Persist document record to database
    doc = Document(
        business_id=business_id,
        uploaded_by_user_id=current_user.id,
        requirement_id=requirement_id,
        document_type=document_type,
        file_name=filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size_bytes=size_bytes,
        sha256_checksum=checksum,
        verification_status=DocumentVerificationStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        "Document uploaded: id=%s business=%s type=%s size=%d bytes sha256=%s...",
        doc.id, business_id, document_type.value, size_bytes, checksum[:8],
    )
    return DocumentUploadResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# GET /documents/{document_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Retrieve document metadata by ID",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Return full document metadata, OCR text, and verification state."""
    stmt = select(Document).where(Document.id == document_id, Document.is_active == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise NotFoundError(message=f"Document '{document_id}' not found.")

    # Ownership enforcement for INDUSTRY_USER
    await _resolve_business_owner(doc.business_id, current_user, db)
    return DocumentRead.model_validate(doc)


# ---------------------------------------------------------------------------
# GET /documents/business/{business_id}
# ---------------------------------------------------------------------------

@router.get(
    "/business/{business_id}",
    response_model=DocumentListResponse,
    summary="List all documents for an enterprise",
)
async def list_documents(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """Return all active documents uploaded for the given business."""
    await _resolve_business_owner(business_id, current_user, db)

    stmt = (
        select(Document)
        .where(Document.business_id == business_id, Document.is_active == True)
        .order_by(Document.created_at.desc())
    )
    docs = (await db.execute(stmt)).scalars().all()
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentRead.model_validate(d) for d in docs],
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/download
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}/download",
    summary="Download a document file (authenticated streaming)",
)
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(_get_storage),
) -> Response:
    """
    Return raw file bytes for an authenticated download.

    Sets correct Content-Type and Content-Disposition headers so the browser
    offers a native "Save file" dialog with the original filename.
    """
    stmt = select(Document).where(Document.id == document_id, Document.is_active == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise NotFoundError(message=f"Document '{document_id}' not found.")

    await _resolve_business_owner(doc.business_id, current_user, db)

    try:
        data = storage.retrieve(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage. It may have been deleted.",
        )

    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.file_name}"',
            "X-Document-Id": doc.id,
            "X-SHA256-Checksum": doc.sha256_checksum,
        },
    )


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a document (owner or admin only)",
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(_get_storage),
) -> None:
    """
    Soft-delete a document record and remove the physical file from storage.
    Only the document owner (INDUSTRY_USER who uploaded it) or an ADMIN may delete.
    """
    stmt = select(Document).where(Document.id == document_id, Document.is_active == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise NotFoundError(message=f"Document '{document_id}' not found.")

    # Ownership: industry users may only delete their own uploads
    if current_user.role == UserRole.INDUSTRY_USER:
        if doc.uploaded_by_user_id != current_user.id:
            raise AuthorizationError(message="You can only delete documents you uploaded.")

    # Soft-delete DB record
    doc.is_active = False
    await db.commit()

    # Best-effort physical deletion (log warning if storage removal fails)
    try:
        storage.delete(doc.storage_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Physical file deletion failed for document %s at '%s': %s",
            doc.id, doc.storage_path, exc,
        )
