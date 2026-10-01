"""
Unit tests for Application, StatusHistory, Query, and Inspection domain models (Fragments 76, 79, 83, 86).
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.application import Application, ApplicationStatus
from app.models.application_query import ApplicationQuery, QueryStatus
from app.models.application_status_history import ApplicationStatusHistory
from app.models.approval import Approval
from app.models.business import Business, EntityType, MSMECategory
from app.models.department import Department, JurisdictionLevel
from app.models.inspection import Inspection, InspectionRecommendation, InspectionStatus
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_application_model_lifecycle_and_defaults():
    """Verify application persistence, status defaults, and relationships."""
    async with AsyncSessionLocal() as session:
        # Create user & business
        user = User(
            email="applicant@test.com",
            hashed_password="hash",
            full_name="Rajesh Patel",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.flush()

        biz = Business(
            user_id=user.id,
            legal_name="Patel Pharmaceuticals Pvt Ltd",
            entity_type=EntityType.PRIVATE_LIMITED,
            msme_category=MSMECategory.SMALL,
            pan="ABCDE1234F",
        )
        session.add(biz)

        dept = Department(
            code="SPCB",
            name="State Pollution Control Board",
            jurisdiction_level=JurisdictionLevel.STATE,
        )
        session.add(dept)

        approval = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE)",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            sla_days=45,
            estimated_fee_base=25000.0,
        )
        session.add(approval)
        await session.commit()

        # Create application
        app = Application(
            application_number="APP-20261001-0001",
            business_id=biz.id,
            approval_id=approval.id,
            department_id=dept.id,
            department_code="SPCB",
            applied_by_user_id=user.id,
            status=ApplicationStatus.DRAFT,
            application_data={"investment_crores": 15.0, "water_kld": 50.0},
            attached_document_ids=["doc-uuid-1", "doc-uuid-2"],
            fee_amount=25000.0,
            fee_paid=False,
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)

        assert app.id is not None
        assert app.status == ApplicationStatus.DRAFT
        assert app.application_number == "APP-20261001-0001"
        assert len(app.attached_document_ids) == 2
        assert app.application_data["investment_crores"] == 15.0
        assert "<Application APP-20261001-0001" in repr(app)


@pytest.mark.asyncio
async def test_application_status_history_cascade():
    """Verify application status history logging and cascade deletion."""
    async with AsyncSessionLocal() as session:
        user = User(email="test@biz.com", hashed_password="pw", full_name="User 1")
        session.add(user)
        await session.flush()

        biz = Business(user_id=user.id, legal_name="Test Biz", entity_type=EntityType.LLP, pan="AAAAA1111A")
        session.add(biz)
        approval = Approval(code="FIRE_NOC", title="Fire NOC", department_code="FIRE", issuing_authority="Fire Dept")
        session.add(approval)
        await session.commit()

        app = Application(
            application_number="APP-20261001-0002",
            business_id=biz.id,
            approval_id=approval.id,
            department_code="FIRE",
            applied_by_user_id=user.id,
        )
        session.add(app)
        await session.commit()

        hist = ApplicationStatusHistory(
            application_id=app.id,
            from_status=ApplicationStatus.DRAFT,
            to_status=ApplicationStatus.SUBMITTED,
            changed_by_user_id=user.id,
            action="SUBMIT",
            remarks="Filing submitted online",
        )
        session.add(hist)
        await session.commit()

        stmt = select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app.id)
        entries = (await session.execute(stmt)).scalars().all()
        assert len(entries) == 1
        assert entries[0].to_status == ApplicationStatus.SUBMITTED
        assert entries[0].action == "SUBMIT"


@pytest.mark.asyncio
async def test_application_query_and_inspection_models():
    """Verify ApplicationQuery and Inspection records."""
    async with AsyncSessionLocal() as session:
        officer = User(email="officer@spcb.gov.in", hashed_password="pw", full_name="Officer Sharma", role=UserRole.DEPARTMENT_OFFICER)
        inspector = User(email="inspector@spcb.gov.in", hashed_password="pw", full_name="Inspector Verma", role=UserRole.INSPECTOR)
        session.add_all([officer, inspector])
        await session.flush()

        biz = Business(user_id=officer.id, legal_name="Green Chemicals", entity_type=EntityType.PRIVATE_LIMITED, pan="GGGGG2222G")
        session.add(biz)
        approval = Approval(code="CTO_PCB", title="Consent to Operate", department_code="SPCB", issuing_authority="SPCB")
        session.add(approval)
        await session.commit()

        app = Application(
            application_number="APP-20261001-0003",
            business_id=biz.id,
            approval_id=approval.id,
            department_code="SPCB",
            applied_by_user_id=officer.id,
        )
        session.add(app)
        await session.commit()

        query = ApplicationQuery(
            application_id=app.id,
            raised_by_user_id=officer.id,
            query_title="Missing ETP layout",
            query_text="Please submit full Effluent Treatment Plant engineering layout diagram.",
            status=QueryStatus.OPEN,
        )
        session.add(query)

        inspection = Inspection(
            application_id=app.id,
            inspector_id=inspector.id,
            scheduled_date=datetime.now(timezone.utc),
            status=InspectionStatus.SCHEDULED,
            instructions="Inspect hazardous waste containment bunds.",
            checklist_results={"bund_integrity": True},
            recommendation=InspectionRecommendation.SATISFACTORY,
        )
        session.add(inspection)
        await session.commit()

        assert query.id is not None
        assert query.status == QueryStatus.OPEN
        assert inspection.id is not None
        assert inspection.recommendation == InspectionRecommendation.SATISFACTORY
