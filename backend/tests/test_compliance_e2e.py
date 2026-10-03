"""
Compliance & Monitoring — Comprehensive Test Suite (Phase 7, Fragment 102).

Tests:
1. Compliance requirement model creation and catalog seeding
2. Compliance rule engine — requirement applicability evaluation
3. Deadline calculation and cycle label generation
4. Compliance record generation for a business
5. Filing submission and officer review lifecycle
6. Dashboard metrics computation
7. Alert generation (due soon, overdue, expiring)
8. Compliance status and category breakdown
9. Urgency scoring and prioritization queue
10. Renewal tracking from approved applications
"""

import asyncio
import pytest
import uuid
from datetime import date, datetime, timedelta, timezone

from httpx import AsyncClient, ASGITransport

# Ensure test database is configured before any app imports
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.core.database import engine, Base
from app.models.base import generate_uuid, utc_now
from app.models.user import User, UserRole
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.approval import Approval
from app.models.application import Application, ApplicationStatus
from app.models.compliance import (
    ComplianceRequirement,
    ComplianceRecord,
    ComplianceRecordStatus,
    ComplianceCategory,
    ComplianceFrequency,
    CompliancePriority,
)
from app.services.compliance_service import (
    calculate_next_due_date,
    calculate_warning_date,
    generate_cycle_label,
    evaluate_business_compliance_requirements,
    generate_compliance_records_for_business,
    get_compliance_alerts,
    get_compliance_dashboard,
    get_compliance_status,
    get_prioritized_compliance,
    submit_compliance_filing,
    review_compliance_filing,
    create_renewal_from_application,
    seed_compliance_requirements,
    _compute_urgency_score,
)
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    """Use a single event loop for the entire module to work with module-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Create all tables once for the module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Provide a clean async database session per test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def seed_data(db_session):
    """Seed test data: users, business, profile, approvals."""
    # Industry user
    industry_user = User(
        id=generate_uuid(),
        email=f"industry_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Industry Test User",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.INDUSTRY_USER,
        is_verified=True,
    )
    db_session.add(industry_user)

    # Officer user
    officer_user = User(
        id=generate_uuid(),
        email=f"officer_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Officer Test User",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.DEPARTMENT_OFFICER,
        is_verified=True,
        department_id=None,
    )
    db_session.add(officer_user)

    # Admin user
    admin_user = User(
        id=generate_uuid(),
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Admin Test User",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.ADMIN,
        is_verified=True,
    )
    db_session.add(admin_user)

    # Approvals (CTO_PCB, FACTORY_LIC, FIRE_PROV, etc.)
    approvals = {}
    for code, title, dept, sla, validity in [
        ("CTO_PCB", "Consent to Operate", "SPCB", 60, 60),
        ("FACTORY_LIC", "Factory License", "DISH", 30, 12),
        ("FIRE_PROV", "Fire Safety NOC", "FIRE", 15, 24),
        ("BOILER_REG", "Boiler Registration", "BOILER", 30, 12),
        ("POWER_CONN", "Power Connection Sanction", "DISCOM", 45, 24),
    ]:
        approval = Approval(
            id=generate_uuid(),
            code=code,
            title=title,
            department_code=dept,
            issuing_authority=f"State {dept}",
            sla_days=sla,
            validity_period_months=validity,
        )
        db_session.add(approval)
        approvals[code] = approval

    # Business
    business = Business(
        id=generate_uuid(),
        user_id=industry_user.id,
        legal_name="TestChem Industries Pvt Ltd",
        entity_type=EntityType.PRIVATE_LIMITED,
        msme_category=MSMECategory.MEDIUM,
        pan="ABCDE1234F",
        gstin="29ABCDE1234F1Z5",
    )
    db_session.add(business)

    # Business Profile — RED category, MEDIUM_SCALE
    profile = BusinessProfile(
        id=generate_uuid(),
        business_id=business.id,
        industry_scale=IndustryScale.MEDIUM_SCALE,
        pollution_category=PollutionCategory.RED,
        state="Maharashtra",
        district="Pune",
        manufacturing_activity="Chemical manufacturing",
    )
    db_session.add(profile)

    await db_session.flush()

    return {
        "industry_user": industry_user,
        "officer_user": officer_user,
        "admin_user": admin_user,
        "business": business,
        "profile": profile,
        "approvals": approvals,
    }


# ---------------------------------------------------------------------------
# Test 1: Compliance Requirement Model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compliance_requirement_model(db_session, seed_data):
    """Test creating a ComplianceRequirement directly."""
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="TEST_CTO_RENEWAL",
        title="Test CTO Renewal",
        description="Test compliance requirement",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.QUINQUENNIAL,
        frequency_months=60,
        priority=CompliancePriority.CRITICAL,
        warning_days=90,
        statutory_act="Water Act, 1974",
        penalty_amount_max=1000000.0,
        required_documents=["CTO_CERT", "EMISSIONS_REPORT"],
        applicable_pollution_categories=["RED", "ORANGE"],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    assert req.id is not None
    assert req.code == "TEST_CTO_RENEWAL"
    assert req.frequency == ComplianceFrequency.QUINQUENNIAL
    assert req.frequency_months == 60
    assert req.priority == CompliancePriority.CRITICAL
    assert req.penalty_amount_max == 1000000.0
    assert "RED" in req.applicable_pollution_categories


# ---------------------------------------------------------------------------
# Test 2: Compliance Record Model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compliance_record_model(db_session, seed_data):
    """Test creating a ComplianceRecord directly."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["FACTORY_LIC"].id,
        code="TEST_FACTORY_RENEWAL",
        title="Test Factory License Renewal",
        category=ComplianceCategory.FACTORY_OPERATIONS,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.CRITICAL,
        warning_days=60,
    )
    db_session.add(req)
    await db_session.flush()

    record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.UPCOMING,
        cycle_label="FY2026-27",
        due_date=date(2027, 3, 31),
        warning_date=date(2027, 1, 30),
    )
    db_session.add(record)
    await db_session.flush()

    assert record.id is not None
    assert record.status == ComplianceRecordStatus.UPCOMING
    assert record.cycle_label == "FY2026-27"
    assert record.due_date == date(2027, 3, 31)
    assert record.days_overdue == 0
    assert record.penalty_imposed == 0.0


# ---------------------------------------------------------------------------
# Test 3: Deadline Calculation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deadline_calculation():
    """Test next due date, warning date, and cycle label calculation."""
    base = date(2026, 4, 1)

    # Annual: +12 months
    next_annual = calculate_next_due_date(base, 12)
    assert next_annual == date(2027, 4, 1)

    # Quarterly: +3 months
    next_quarter = calculate_next_due_date(base, 3)
    assert next_quarter == date(2026, 7, 1)

    # Semi-annual: +6 months
    next_half = calculate_next_due_date(base, 6)
    assert next_half == date(2026, 10, 1)

    # 5-year: +60 months
    next_quint = calculate_next_due_date(base, 60)
    assert next_quint == date(2031, 4, 1)

    # Warning date: 30 days before
    warning = calculate_warning_date(date(2027, 3, 31), 30)
    assert warning == date(2027, 3, 1)

    # Edge case: month end (Jan 31 + 1 month = Feb 28/29)
    base_jan31 = date(2026, 1, 31)
    next_month = calculate_next_due_date(base_jan31, 1)
    assert next_month == date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Test 4: Cycle Label Generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_label_generation():
    """Test human-readable cycle label generation."""
    assert generate_cycle_label(date(2026, 6, 15), ComplianceFrequency.QUARTERLY) == "2026-Q2"
    assert generate_cycle_label(date(2026, 10, 1), ComplianceFrequency.HALF_YEARLY) == "2026-H2"
    assert generate_cycle_label(date(2027, 1, 15), ComplianceFrequency.ANNUAL) == "FY2026-27"
    assert generate_cycle_label(date(2026, 8, 1), ComplianceFrequency.MONTHLY) == "2026-08"


# ---------------------------------------------------------------------------
# Test 5: Compliance Rule Engine — Applicability Evaluation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compliance_rule_engine(db_session, seed_data):
    """Test that the rule engine correctly matches requirements to a business profile."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    # Create requirements with different filters
    # Req 1: Environmental, RED + ORANGE only → should match (business is RED)
    req_env = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="EVAL_ENV_RED_ORANGE",
        title="Env Compliance (Red/Orange)",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.HIGH,
        warning_days=30,
        applicable_pollution_categories=["RED", "ORANGE"],
        applicable_industry_scales=[],
    )
    db_session.add(req_env)

    # Req 2: Green/White only → should NOT match
    req_green = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="EVAL_ENV_GREEN_ONLY",
        title="Env Compliance (Green Only)",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.LOW,
        warning_days=15,
        applicable_pollution_categories=["GREEN", "WHITE"],
        applicable_industry_scales=[],
    )
    db_session.add(req_green)

    # Req 3: LARGE_SCALE + MEGA only → should NOT match (business is MEDIUM)
    req_large = ComplianceRequirement(
        approval_id=approvals["BOILER_REG"].id,
        code="EVAL_BOILER_LARGE",
        title="Boiler (Large Only)",
        category=ComplianceCategory.BOILER_PRESSURE,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.CRITICAL,
        warning_days=45,
        applicable_pollution_categories=[],
        applicable_industry_scales=["LARGE_SCALE", "MEGA"],
    )
    db_session.add(req_large)

    # Req 4: No filters → matches all
    req_all = ComplianceRequirement(
        approval_id=approvals["FACTORY_LIC"].id,
        code="EVAL_FACTORY_ALL",
        title="Factory Compliance (All)",
        category=ComplianceCategory.FACTORY_OPERATIONS,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.HIGH,
        warning_days=30,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req_all)

    await db_session.flush()

    applicable = await evaluate_business_compliance_requirements(db_session, business.id)
    applicable_codes = [r.code for r in applicable]

    assert "EVAL_ENV_RED_ORANGE" in applicable_codes
    assert "EVAL_FACTORY_ALL" in applicable_codes
    assert "EVAL_ENV_GREEN_ONLY" not in applicable_codes
    assert "EVAL_BOILER_LARGE" not in applicable_codes


# ---------------------------------------------------------------------------
# Test 6: Compliance Record Generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compliance_record_generation(db_session, seed_data):
    """Test automatic compliance record generation for a business."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    # Create a requirement that will match
    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="GEN_CTO_RENEW",
        title="CTO Renewal for Generation Test",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.HIGH,
        warning_days=30,
        applicable_pollution_categories=["RED"],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    records = await generate_compliance_records_for_business(
        db_session, business.id, cycles_ahead=1,
    )

    # Should have generated at least 1 record (for the new requirement)
    new_records = [r for r in records if r.requirement_id == req.id]
    assert len(new_records) >= 1

    record = new_records[0]
    assert record.business_id == business.id
    assert record.requirement_id == req.id
    assert record.cycle_label is not None
    assert record.due_date is not None
    assert record.warning_date is not None


# ---------------------------------------------------------------------------
# Test 7: Filing Submission & Review Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filing_lifecycle(db_session, seed_data):
    """Test the full compliance filing lifecycle: create → submit → review."""
    business = seed_data["business"]
    industry_user = seed_data["industry_user"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["FACTORY_LIC"].id,
        code="LIFECYCLE_FACTORY",
        title="Factory License for Lifecycle Test",
        category=ComplianceCategory.FACTORY_OPERATIONS,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.CRITICAL,
        warning_days=60,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    # Create record
    record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.DUE_SOON,
        cycle_label="FY2026-27",
        due_date=date.today() + timedelta(days=15),
        warning_date=date.today() - timedelta(days=5),
    )
    db_session.add(record)
    await db_session.flush()

    # Submit filing
    updated = await submit_compliance_filing(
        db_session,
        record.id,
        filing_data={"safety_audit_date": "2026-09-15", "violations": 0},
        evidence_document_ids=["doc-001", "doc-002"],
        remarks="All safety requirements met",
        user_id=industry_user.id,
    )
    assert updated.status == ComplianceRecordStatus.SUBMITTED
    assert updated.submitted_at is not None
    assert len(updated.evidence_document_ids) == 2

    # Review and approve
    approved = await review_compliance_filing(
        db_session,
        record.id,
        decision="APPROVED",
        officer_remarks="Compliant. License renewed.",
        new_valid_until=date(2027, 3, 31),
        penalty_imposed=0.0,
    )
    assert approved.status == ComplianceRecordStatus.APPROVED
    assert approved.approved_at is not None
    assert approved.new_valid_until == date(2027, 3, 31)
    assert approved.officer_remarks == "Compliant. License renewed."


# ---------------------------------------------------------------------------
# Test 8: Filing Rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filing_rejection(db_session, seed_data):
    """Test that a compliance filing can be rejected with penalty."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="REJECT_TEST_CTO",
        title="CTO for Rejection Test",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.HIGH,
        warning_days=30,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.OVERDUE,
        cycle_label="FY2025-26",
        due_date=date.today() - timedelta(days=30),
        days_overdue=30,
    )
    db_session.add(record)
    await db_session.flush()

    # Submit late
    await submit_compliance_filing(
        db_session, record.id,
        filing_data={"emissions_data": "incomplete"},
        evidence_document_ids=[],
        remarks="Late submission",
    )

    # Reject with penalty
    rejected = await review_compliance_filing(
        db_session, record.id,
        decision="REJECTED",
        officer_remarks="Insufficient emissions data. Resubmit within 15 days.",
        penalty_imposed=25000.0,
    )
    assert rejected.status == ComplianceRecordStatus.REJECTED
    assert rejected.penalty_imposed == 25000.0


# ---------------------------------------------------------------------------
# Test 9: Dashboard Metrics Computation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_metrics(db_session, seed_data):
    """Test compliance dashboard metrics aggregation."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="DASH_METRIC_REQ",
        title="Dashboard Metric Test Req",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.HIGH,
        warning_days=30,
        penalty_amount_max=50000.0,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    # Add mix of statuses
    for status_val, due_offset in [
        (ComplianceRecordStatus.APPROVED, -60),
        (ComplianceRecordStatus.DUE_SOON, 10),
        (ComplianceRecordStatus.OVERDUE, -5),
    ]:
        record = ComplianceRecord(
            business_id=business.id,
            requirement_id=req.id,
            status=status_val,
            cycle_label=f"cycle_{due_offset}",
            due_date=date.today() + timedelta(days=due_offset),
            days_overdue=max(0, -due_offset) if due_offset < 0 and status_val == ComplianceRecordStatus.OVERDUE else 0,
        )
        db_session.add(record)
    await db_session.flush()

    metrics = await get_compliance_dashboard(db_session, business.id)

    assert metrics.business_id == business.id
    assert metrics.total_obligations >= 3
    assert metrics.compliant_count >= 1
    assert metrics.due_soon_count >= 1
    assert metrics.overdue_count >= 1
    assert 0 <= metrics.compliance_rate_percent <= 100
    assert metrics.total_penalty_exposure >= 0


# ---------------------------------------------------------------------------
# Test 10: Alert Generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_alert_generation(db_session, seed_data):
    """Test compliance alert generation for due-soon and overdue items."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["FIRE_PROV"].id,
        code="ALERT_FIRE_TEST",
        title="Fire NOC Alert Test",
        category=ComplianceCategory.FIRE_SAFETY,
        frequency=ComplianceFrequency.BIENNIAL,
        frequency_months=24,
        priority=CompliancePriority.HIGH,
        warning_days=45,
        penalty_amount_max=500000.0,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    # Create overdue record
    overdue_record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.OVERDUE,
        cycle_label="2024-2026",
        due_date=date.today() - timedelta(days=10),
        days_overdue=10,
    )
    db_session.add(overdue_record)

    # Create due-soon record
    due_soon_record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.DUE_SOON,
        cycle_label="2026-2028",
        due_date=date.today() + timedelta(days=20),
        warning_date=date.today() - timedelta(days=5),
    )
    db_session.add(due_soon_record)
    await db_session.flush()

    alerts_response = await get_compliance_alerts(db_session, business.id)

    assert alerts_response.total >= 2
    alert_types = [a.alert_type for a in alerts_response.items]
    assert "OVERDUE" in alert_types
    assert "DUE_SOON" in alert_types

    # Verify overdue alert comes first (negative days_remaining)
    overdue_alerts = [a for a in alerts_response.items if a.alert_type == "OVERDUE"]
    if overdue_alerts:
        assert overdue_alerts[0].days_remaining < 0


# ---------------------------------------------------------------------------
# Test 11: Urgency Scoring & Prioritization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_urgency_scoring():
    """Test the composite urgency score computation."""
    # Overdue CRITICAL item should score highest
    score_overdue_critical = _compute_urgency_score(
        days_remaining=-10,
        priority=CompliancePriority.CRITICAL,
        penalty_max=1000000.0,
        status=ComplianceRecordStatus.OVERDUE,
    )

    # Upcoming LOW item should score lowest
    score_upcoming_low = _compute_urgency_score(
        days_remaining=180,
        priority=CompliancePriority.LOW,
        penalty_max=10000.0,
        status=ComplianceRecordStatus.UPCOMING,
    )

    assert score_overdue_critical > score_upcoming_low
    assert score_overdue_critical > 100  # Should be significantly high


@pytest.mark.asyncio
async def test_prioritized_queue(db_session, seed_data):
    """Test the prioritized compliance action queue."""
    business = seed_data["business"]

    priorities = await get_prioritized_compliance(db_session, business.id, limit=10)

    # Should have items (from previous test data)
    assert priorities.total >= 0
    # Verify ranking order
    if len(priorities.items) >= 2:
        assert priorities.items[0].rank == 1
        assert priorities.items[0].urgency_score >= priorities.items[1].urgency_score


# ---------------------------------------------------------------------------
# Test 12: Compliance Status & Category Breakdown
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compliance_status(db_session, seed_data):
    """Test comprehensive compliance status computation."""
    business = seed_data["business"]

    status = await get_compliance_status(db_session, business.id)

    assert status.business_id == business.id
    assert status.overall_health in ("HEALTHY", "AT_RISK", "NON_COMPLIANT")
    assert 0 <= status.overall_compliance_rate <= 100

    # Should have category breakdown entries
    if status.category_breakdown:
        for cat in status.category_breakdown:
            assert cat.total >= 0
            assert 0 <= cat.compliance_rate_percent <= 100


# ---------------------------------------------------------------------------
# Test 13: Renewal Tracking from Approved Application
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_renewal_from_application(db_session, seed_data):
    """Test automatic compliance renewal record creation from approved application."""
    business = seed_data["business"]
    industry_user = seed_data["industry_user"]
    approvals = seed_data["approvals"]
    cto = approvals["CTO_PCB"]

    # Create a matching compliance requirement
    req = ComplianceRequirement(
        approval_id=cto.id,
        code="RENEW_CTO_AUTO",
        title="Auto-CTO Renewal",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.QUINQUENNIAL,
        frequency_months=60,
        priority=CompliancePriority.CRITICAL,
        warning_days=90,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    # Create an approved application with validity
    application = Application(
        application_number=f"APP-{uuid.uuid4().hex[:8].upper()}",
        business_id=business.id,
        approval_id=cto.id,
        department_code="SPCB",
        applied_by_user_id=industry_user.id,
        status=ApplicationStatus.APPROVED,
        certificate_valid_until=date(2031, 9, 30),
        validity_years=5,
        approval_certificate_number="CTO/SPCB/2026/12345",
    )
    db_session.add(application)
    await db_session.flush()

    # Create renewal record
    renewal = await create_renewal_from_application(db_session, application)

    assert renewal is not None
    assert renewal.business_id == business.id
    assert renewal.requirement_id == req.id
    assert renewal.application_id == application.id
    assert renewal.due_date == date(2031, 9, 30)
    assert renewal.status in (
        ComplianceRecordStatus.UPCOMING,
        ComplianceRecordStatus.DUE_SOON,
    )


# ---------------------------------------------------------------------------
# Test 14: Business Rule Violations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_filing_submission(db_session, seed_data):
    """Test that submitting a filing for an already-approved record raises error."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="INVALID_SUBMIT_TEST",
        title="Invalid Submit Test",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.MEDIUM,
        warning_days=30,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.APPROVED,
        cycle_label="FY2025-26",
        due_date=date.today() - timedelta(days=100),
    )
    db_session.add(record)
    await db_session.flush()

    from app.core.exceptions import BusinessRuleViolationError
    with pytest.raises(BusinessRuleViolationError):
        await submit_compliance_filing(
            db_session, record.id,
            filing_data={},
            evidence_document_ids=[],
        )


@pytest.mark.asyncio
async def test_invalid_review_status(db_session, seed_data):
    """Test that reviewing a non-SUBMITTED record raises error."""
    business = seed_data["business"]
    approvals = seed_data["approvals"]

    req = ComplianceRequirement(
        approval_id=approvals["CTO_PCB"].id,
        code="INVALID_REVIEW_TEST",
        title="Invalid Review Test",
        category=ComplianceCategory.ENVIRONMENTAL,
        frequency=ComplianceFrequency.ANNUAL,
        frequency_months=12,
        priority=CompliancePriority.MEDIUM,
        warning_days=30,
        applicable_pollution_categories=[],
        applicable_industry_scales=[],
    )
    db_session.add(req)
    await db_session.flush()

    record = ComplianceRecord(
        business_id=business.id,
        requirement_id=req.id,
        status=ComplianceRecordStatus.UPCOMING,
        cycle_label="FY2027-28",
        due_date=date.today() + timedelta(days=200),
    )
    db_session.add(record)
    await db_session.flush()

    from app.core.exceptions import BusinessRuleViolationError
    with pytest.raises(BusinessRuleViolationError):
        await review_compliance_filing(
            db_session, record.id,
            decision="APPROVED",
        )
