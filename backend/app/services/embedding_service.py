"""
Embedding Pipeline — UdyamSetu AI RAG System

Handles text chunking and embedding generation for the knowledge base.
Splits documents into overlapping chunks, then generates embeddings
via the configured AI provider.
"""

import logging
import re
from typing import List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_document import (
    KnowledgeChunk,
    KnowledgeDocument,
    ProcessingStatus,
)
from app.services.ai_service import get_ai_provider

logger = logging.getLogger("udyamsetu.embedding")


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    *,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    separator_pattern: str = r"\n\n+",
) -> List[str]:
    """
    Split text into overlapping chunks suitable for embedding.

    Strategy:
    1. Split on paragraph boundaries first.
    2. Merge short paragraphs until ``max_tokens`` is reached.
    3. Apply token-level overlap between consecutive chunks.
    """
    if not text or not text.strip():
        return []

    # Approximate token count using word splitting (1 word ≈ 1.3 tokens)
    def approx_tokens(s: str) -> int:
        return max(1, int(len(s.split()) * 1.3))

    # Split into paragraphs
    paragraphs = re.split(separator_pattern, text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [text.strip()]

    chunks: List[str] = []
    current_parts: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = approx_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_parts:
            # Flush current chunk
            chunks.append("\n\n".join(current_parts))

            # Apply overlap: keep last part(s) that fit within overlap budget
            overlap_parts = []
            overlap_count = 0
            for part in reversed(current_parts):
                pt = approx_tokens(part)
                if overlap_count + pt <= overlap_tokens:
                    overlap_parts.insert(0, part)
                    overlap_count += pt
                else:
                    break
            current_parts = overlap_parts
            current_tokens = overlap_count

        current_parts.append(para)
        current_tokens += para_tokens

    # Final chunk
    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


# ---------------------------------------------------------------------------
# Embedding pipeline
# ---------------------------------------------------------------------------

async def process_document_embeddings(
    db: AsyncSession,
    document_id: str,
    *,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> KnowledgeDocument:
    """
    Process a knowledge document through the full embedding pipeline:
    1. Update status to CHUNKING
    2. Split content into chunks
    3. Update status to EMBEDDING
    4. Generate embeddings for each chunk
    5. Persist chunks with embeddings
    6. Update document status to COMPLETED
    """
    # Fetch document
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise ValueError(f"Knowledge document {document_id} not found")

    try:
        # Step 1: Chunking
        document.processing_status = ProcessingStatus.CHUNKING.value
        await db.flush()

        text_chunks = chunk_text(
            document.content,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )

        if not text_chunks:
            document.processing_status = ProcessingStatus.COMPLETED.value
            document.chunk_count = 0
            await db.flush()
            return document

        # Step 2: Embedding
        document.processing_status = ProcessingStatus.EMBEDDING.value
        await db.flush()

        provider = get_ai_provider()
        embedding_result = await provider.embed(text_chunks)

        # Step 3: Persist chunks
        # First, delete any existing chunks for re-processing
        existing_chunks = await db.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document_id
            )
        )
        for existing in existing_chunks.scalars().all():
            await db.delete(existing)
        await db.flush()

        for i, (text, embedding_vec) in enumerate(
            zip(text_chunks, embedding_result.embeddings)
        ):
            chunk = KnowledgeChunk(
                document_id=document_id,
                chunk_index=i,
                content=text,
                token_count=len(text.split()),
                embedding=embedding_vec,
                embedding_model=embedding_result.model,
                embedding_dimensions=embedding_result.dimensions,
            )
            db.add(chunk)

        # Step 4: Update document status
        document.processing_status = ProcessingStatus.COMPLETED.value
        document.chunk_count = len(text_chunks)
        document.error_message = None
        await db.flush()

        logger.info(
            f"Document '{document.title}' processed: "
            f"{len(text_chunks)} chunks, {embedding_result.dimensions}d embeddings"
        )
        return document

    except Exception as e:
        document.processing_status = ProcessingStatus.FAILED.value
        document.error_message = str(e)
        await db.flush()
        logger.error(f"Embedding pipeline failed for document {document_id}: {e}")
        raise


async def seed_knowledge_base(db: AsyncSession) -> List[KnowledgeDocument]:
    """
    Seed the knowledge base with core regulatory knowledge documents.
    Idempotent — skips documents that already exist (by title).
    """
    seed_documents = [
        {
            "title": "Udyam Registration Guide",
            "category": "regulatory",
            "content": (
                "Udyam Registration — Complete Guide\n\n"
                "Udyam Registration is a free, paperless online registration for Micro, Small, and Medium "
                "Enterprises (MSMEs) introduced by the Ministry of MSME, Government of India. It replaced "
                "the earlier Udyog Aadhaar Memorandum (UAM) system from July 1, 2020.\n\n"
                "Classification Criteria (Revised 2020):\n\n"
                "Micro Enterprise: Investment up to ₹1 Crore and Turnover up to ₹5 Crore\n"
                "Small Enterprise: Investment up to ₹10 Crore and Turnover up to ₹50 Crore\n"
                "Medium Enterprise: Investment up to ₹50 Crore and Turnover up to ₹250 Crore\n\n"
                "Required Information:\n"
                "- Aadhaar Number of the proprietor/managing partner/authorized signatory\n"
                "- PAN and GSTIN (if applicable)\n"
                "- Plant/unit location details\n"
                "- Bank account details\n"
                "- NIC 2-digit code of main business activity\n"
                "- Number of employees\n"
                "- Investment in plant and machinery\n\n"
                "Benefits of Udyam Registration:\n"
                "1. Collateral-free loans under CGTMSE\n"
                "2. Lower interest rates on bank loans\n"
                "3. Protection against delayed payments\n"
                "4. Eligibility for government tenders with price preference\n"
                "5. Concession on electricity bills\n"
                "6. Tax benefits and exemptions\n"
                "7. Access to government schemes like PMEGP, Mudra, etc."
            ),
        },
        {
            "title": "Factory License and Industrial Approvals",
            "category": "regulatory",
            "content": (
                "Factory License Under the Factories Act, 1948\n\n"
                "A Factory License is mandatory for all manufacturing premises where:\n"
                "- 10 or more workers are employed with the aid of power, OR\n"
                "- 20 or more workers are employed without the aid of power.\n\n"
                "Application Process:\n"
                "1. Submit Form 2 (Plan Approval) to the Chief Inspector of Factories\n"
                "2. Obtain plan approval for the factory building layout\n"
                "3. Submit Form 3 (License Application) with required documents\n"
                "4. Pay the prescribed fee based on number of workers and HP of machinery\n"
                "5. Factory inspection by the Inspector of Factories\n"
                "6. License issued (Form 4) — valid for 12 months, renewable annually\n\n"
                "Required Documents:\n"
                "- Building plan approved by local authority\n"
                "- Stability certificate from a registered structural engineer\n"
                "- NOC from the Fire Department\n"
                "- NOC from the State Pollution Control Board (CTE/CTO)\n"
                "- List of machinery with HP details\n"
                "- Occupancy certificate\n"
                "- PAN and GST registration\n\n"
                "Related Approvals:\n"
                "- Consent to Establish (CTE) from SPCB\n"
                "- Consent to Operate (CTO) from SPCB\n"
                "- Fire Safety NOC\n"
                "- Building Use Permission from local municipal authority\n"
                "- Electrical Installation Approval from Electrical Inspector"
            ),
        },
        {
            "title": "GST Registration and Compliance",
            "category": "compliance",
            "content": (
                "GST Registration — Comprehensive Guide\n\n"
                "Registration Threshold:\n"
                "- Mandatory for aggregate turnover exceeding ₹40 Lakh (₹20 Lakh for special category states)\n"
                "- Mandatory for inter-state supply regardless of turnover\n"
                "- Mandatory for e-commerce operators\n\n"
                "Registration Process:\n"
                "1. Visit gst.gov.in and click 'Register Now'\n"
                "2. Fill Part A: PAN, mobile, email → receive TRN\n"
                "3. Fill Part B: Business details, bank accounts, authorized signatory\n"
                "4. Upload documents: PAN, Aadhaar, business registration, bank proof, address proof\n"
                "5. E-verify using DSC or EVC\n"
                "6. GSTIN allotted within 3-7 working days\n\n"
                "Key Compliance Requirements:\n"
                "- GSTR-1: Monthly/Quarterly outward supplies (11th of next month)\n"
                "- GSTR-3B: Monthly summary return (20th of next month)\n"
                "- GSTR-9: Annual return (31st December of next FY)\n"
                "- GSTR-9C: Reconciliation statement for turnover above ₹5 Cr\n\n"
                "Composition Scheme:\n"
                "Available for businesses with turnover up to ₹1.5 Crore. "
                "Pay tax at a fixed rate (1% for manufacturers, 5% for restaurants, 6% for services). "
                "File quarterly returns via GSTR-4."
            ),
        },
        {
            "title": "Government Schemes for MSMEs",
            "category": "scheme",
            "content": (
                "Government Schemes for Micro, Small & Medium Enterprises\n\n"
                "1. PMEGP (Prime Minister's Employment Generation Programme)\n"
                "Margin money subsidy: 15-35% of project cost (max ₹25 Lakh for manufacturing, "
                "₹10 Lakh for services). Implemented by KVIC. Apply through kvic.gov.in.\n\n"
                "2. CGTMSE (Credit Guarantee Trust for MSEs)\n"
                "Collateral-free loans up to ₹5 Crore. Guarantee fee: 0.37-2% of sanctioned amount. "
                "Coverage: up to 85% for Micro enterprises, 75% for others.\n\n"
                "3. MUDRA (Micro Units Development & Refinance Agency)\n"
                "Three categories: Shishu (up to ₹50,000), Kishore (₹50,000-₹5 Lakh), "
                "Tarun (₹5-10 Lakh). No collateral required. Apply through any bank.\n\n"
                "4. PLI (Production Linked Incentive) Scheme\n"
                "Incentives of 4-6% on incremental sales for 5 years in 14 key sectors including "
                "electronics, pharmaceuticals, food processing, and textiles.\n\n"
                "5. ZED (Zero Defect Zero Effect) Certification\n"
                "Quality and environmental certification. Subsidy: 80% for Micro, 60% for Small, "
                "50% for Medium enterprises on certification costs.\n\n"
                "6. CLCSS (Credit Linked Capital Subsidy Scheme)\n"
                "15% capital subsidy on institutional credit up to ₹1 Crore for technology upgradation "
                "in specified sub-sectors."
            ),
        },
        {
            "title": "Environmental Clearance and Pollution Control",
            "category": "regulatory",
            "content": (
                "Environmental Clearance & Pollution Control for Industries\n\n"
                "State Pollution Control Board (SPCB) Consents:\n\n"
                "Consent to Establish (CTE):\n"
                "Required before setting up any industry. Application includes project report, "
                "site plan, process flow diagram, pollution control measures, and EIA report "
                "(for Red category). Validity: 5 years from date of issue.\n\n"
                "Consent to Operate (CTO):\n"
                "Required before starting operations. Issued after SPCB inspection verifies "
                "installed pollution control equipment matches the approved plan. "
                "Validity: 5 years (Green), 3 years (Orange), 2 years (Red).\n\n"
                "Industry Classification:\n"
                "- Green Category: Low pollution (food processing without effluent, IT services, etc.)\n"
                "- Orange Category: Moderate pollution (pharmaceuticals, food with effluent, etc.)\n"
                "- Red Category: High pollution (chemicals, dyes, tanneries, distilleries, etc.)\n"
                "- White Category: Practically non-polluting (solar power, wind mills, etc.)\n\n"
                "Environmental Impact Assessment (EIA):\n"
                "Mandatory for Red category and large-scale projects. Process includes screening, "
                "scoping, baseline data collection, impact prediction, public hearing, "
                "and expert committee review. Timeline: 6-12 months."
            ),
        },
    ]

    created_docs = []
    for doc_data in seed_documents:
        # Check if document already exists
        existing = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.title == doc_data["title"]
            )
        )
        if existing.scalar_one_or_none():
            continue

        doc = KnowledgeDocument(
            title=doc_data["title"],
            content=doc_data["content"],
            category=doc_data["category"],
            processing_status=ProcessingStatus.PENDING.value,
        )
        db.add(doc)
        await db.flush()
        created_docs.append(doc)

    # Process embeddings for all new documents
    for doc in created_docs:
        await process_document_embeddings(db, doc.id)

    logger.info(f"Knowledge base seeded: {len(created_docs)} new documents processed")
    return created_docs
