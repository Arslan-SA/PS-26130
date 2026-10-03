"""
Compliance Service Engine (Phase 7, Fragments 93, 95–99).

Implements:
- Fragment 93: Compliance rule engine — determines which compliance requirements
  apply to a business based on its profile (sector, pollution category, scale).
- Fragment 95: Deadline calculation — computes due dates, warning dates, and
  generates future compliance cycles.
- Fragment 96: Renewal tracking — automatically creates renewal records from
  approved applications with validity periods.
- Fragment 97: Compliance alerts — generates prioritized alert notifications
  for upcoming, overdue, and expiring obligations.
- Fragment 98: Compliance status — computes aggregate compliance health per
  business, broken down by regulatory category.
- Fragment 99: Compliance prioritization — ranks compliance items by urgency
  using a composite score of deadline proximity, severity, and penalty exposure.
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, BusinessRuleViolationError
from app.models.application import Application, ApplicationStatus
from app.models.approval import Approval
from app.models.business import Business
from app.models.business_profile import BusinessProfile
from app.models.compliance import (
    ComplianceCategory,
    ComplianceFrequency,
    CompliancePriority,
    ComplianceRecord,
    ComplianceRecordStatus,
    ComplianceRequirement,
)
from app.schemas.compliance import (
    ComplianceAlert,
    ComplianceAlertListResponse,
    ComplianceDashboardMetrics,
    CompliancePrioritizedItem,
    CompliancePrioritizedListResponse,
    ComplianceRecordRead,
    ComplianceRecordSummary,
    ComplianceStatusResponse,
    ComplianceStatusSummary,
)

logger = logging.getLogger("udyamsetu.compliance")


# ---------------------------------------------------------------------------
# Utility: Timezone-safe datetime helper (reused pattern from application_service)
# ---------------------------------------------------------------------------

def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime to UTC for consistent arithmetic."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _today() -> date:
    """Return current UTC date."""
    return datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# Seed Data: Compliance Requirement Catalog (Fragment 93)
# ---------------------------------------------------------------------------

COMPLIANCE_CATALOG: List[Dict[str, Any]] = [
    {
        "code": "CTO_RENEWAL",
        "title": "Consent to Operate (CTO) Renewal",
        "description": "Periodic renewal of Consent to Operate from State Pollution Control Board. "
                       "Required for continued industrial operations emitting pollutants.",
        "category": ComplianceCategory.ENVIRONMENTAL,
        "frequency": ComplianceFrequency.QUINQUENNIAL,
        "frequency_months": 60,
        "priority": CompliancePriority.CRITICAL,
        "warning_days": 90,
        "statutory_act": "Water (Prevention and Control of Pollution) Act, 1974; Air Act, 1981",
        "penalty_description": "Shutdown order, prosecution under Water/Air Act, penalty up to ₹10,00,000",
        "penalty_amount_max": 1000000.0,
        "required_documents": ["CTO_CERTIFICATE", "EMISSIONS_REPORT", "ETP_RECORDS"],
        "applicable_pollution_categories": ["RED", "ORANGE", "GREEN"],
        "applicable_industry_scales": [],  # All scales
        "approval_code": "CTO_PCB",
    },
    {
        "code": "HW_RETURNS_ANNUAL",
        "title": "Annual Hazardous Waste Returns",
        "description": "Mandatory annual filing of hazardous waste generation, storage, and "
                       "disposal records to SPCB/CPCB.",
        "category": ComplianceCategory.ENVIRONMENTAL,
        "frequency": ComplianceFrequency.ANNUAL,
        "frequency_months": 12,
        "priority": CompliancePriority.HIGH,
        "warning_days": 30,
        "statutory_act": "Hazardous Waste Management Rules, 2016",
        "penalty_description": "Show-cause notice, penalty up to ₹5,00,000",
        "penalty_amount_max": 500000.0,
        "required_documents": ["HAZARDOUS_WASTE_MANIFEST", "DISPOSAL_CERTIFICATE"],
        "applicable_pollution_categories": ["RED", "ORANGE"],
        "applicable_industry_scales": [],
        "approval_code": "CTO_PCB",
    },
    {
        "code": "FACTORY_LIC_RENEWAL",
        "title": "Factory License Renewal",
        "description": "Annual renewal of factory license under the Factories Act, 1948. "
                       "Required for all registered factories.",
        "category": ComplianceCategory.FACTORY_OPERATIONS,
        "frequency": ComplianceFrequency.ANNUAL,
        "frequency_months": 12,
        "priority": CompliancePriority.CRITICAL,
        "warning_days": 60,
        "statutory_act": "Factories Act, 1948",
        "penalty_description": "Factory closure order, prosecution, penalty up to ₹2,00,000",
        "penalty_amount_max": 200000.0,
        "required_documents": ["FACTORY_LICENSE", "SAFETY_AUDIT_REPORT", "WORKFORCE_REGISTER"],
        "applicable_pollution_categories": [],
        "applicable_industry_scales": [],
        "approval_code": "FACTORY_LIC",
    },
    {
        "code": "FIRE_NOC_RENEWAL",
        "title": "Fire Safety NOC Renewal",
        "description": "Periodic renewal of Fire Safety No Objection Certificate. "
                       "Required after building modifications or as per renewal schedule.",
        "category": ComplianceCategory.FIRE_SAFETY,
        "frequency": ComplianceFrequency.BIENNIAL,
        "frequency_months": 24,
        "priority": CompliancePriority.HIGH,
        "warning_days": 45,
        "statutory_act": "National Building Code; State Fire Prevention Acts",
        "penalty_description": "Operations halt, penalty, criminal liability in case of fire incident",
        "penalty_amount_max": 500000.0,
        "required_documents": ["FIRE_NOC", "FIRE_SAFETY_AUDIT", "EQUIPMENT_INSPECTION"],
        "applicable_pollution_categories": [],
        "applicable_industry_scales": [],
        "approval_code": "FIRE_PROV",
    },
    {
        "code": "BOILER_INSP_ANNUAL",
        "title": "Annual Boiler Inspection Certificate",
        "description": "Mandatory annual boiler fitness inspection and certification "
                       "by state Inspectorate of Boilers.",
        "category": ComplianceCategory.BOILER_PRESSURE,
        "frequency": ComplianceFrequency.ANNUAL,
        "frequency_months": 12,
        "priority": CompliancePriority.CRITICAL,
        "warning_days": 45,
        "statutory_act": "Indian Boilers Act, 1923",
        "penalty_description": "Boiler sealed, criminal prosecution, penalty up to ₹1,00,000",
        "penalty_amount_max": 100000.0,
        "required_documents": ["BOILER_CERTIFICATE", "INSPECTION_REPORT"],
        "applicable_pollution_categories": [],
        "applicable_industry_scales": ["MEDIUM_SCALE", "LARGE_SCALE", "MEGA"],
        "approval_code": "BOILER_REG",
    },
    {
        "code": "LABOR_RETURNS_HALF",
        "title": "Half-Yearly Labour Returns",
        "description": "Statutory returns under various labour laws including minimum wages, "
                       "EPF, ESI, and contract labour regulations.",
        "category": ComplianceCategory.LABOR,
        "frequency": ComplianceFrequency.HALF_YEARLY,
        "frequency_months": 6,
        "priority": CompliancePriority.MEDIUM,
        "warning_days": 15,
        "statutory_act": "Minimum Wages Act; EPF Act; ESI Act",
        "penalty_description": "Penalty up to ₹50,000 per violation",
        "penalty_amount_max": 50000.0,
        "required_documents": ["WAGE_REGISTER", "EPF_RETURNS", "ESI_RETURNS"],
        "applicable_pollution_categories": [],
        "applicable_industry_scales": [],
        "approval_code": "FACTORY_LIC",
    },
    {
        "code": "ENV_AUDIT_ANNUAL",
        "title": "Annual Environmental Audit Report",
        "description": "Mandatory environmental compliance audit report submission "
                       "to SPCB for Red and Orange category industries.",
        "category": ComplianceCategory.ENVIRONMENTAL,
        "frequency": ComplianceFrequency.ANNUAL,
        "frequency_months": 12,
        "priority": CompliancePriority.HIGH,
        "warning_days": 30,
        "statutory_act": "Environment Protection Act, 1986",
        "penalty_description": "Show-cause, penalty up to ₹1,00,000, CTO revocation risk",
        "penalty_amount_max": 100000.0,
        "required_documents": ["ENVIRONMENTAL_AUDIT_REPORT", "EMISSIONS_DATA"],
        "applicable_pollution_categories": ["RED", "ORANGE"],
        "applicable_industry_scales": [],
        "approval_code": "CTO_PCB",
    },
    {
        "code": "ELEC_SAFETY_AUDIT",
        "title": "Electrical Safety Audit",
        "description": "Periodic electrical installation safety audit as required by "
                       "state electricity regulatory commission.",
        "category": ComplianceCategory.ELECTRICAL,
        "frequency": ComplianceFrequency.BIENNIAL,
        "frequency_months": 24,
        "priority": CompliancePriority.MEDIUM,
        "warning_days": 30,
        "statutory_act": "Indian Electricity Act, 2003; CEA Safety Regulations",
        "penalty_description": "Power disconnection risk, penalty up to ₹1,00,000",
        "penalty_amount_max": 100000.0,
        "required_documents": ["ELECTRICAL_AUDIT_REPORT", "POWER_SANCTION_LETTER"],
        "applicable_pollution_categories": [],
        "applicable_industry_scales": ["MEDIUM_SCALE", "LARGE_SCALE", "MEGA"],
        "approval_code": "POWER_CONN",
    },
]


# ---------------------------------------------------------------------------
# Fragment 93: Compliance Rule Engine
# ---------------------------------------------------------------------------

async def seed_compliance_requirements(db: AsyncSession) -> List[ComplianceRequirement]:
    """
    Seed the compliance requirements catalog from COMPLIANCE_CATALOG.
    Skips entries that already exist (idempotent). Links each requirement
    to its parent approval catalog entry.
    """
    created = []
    for entry in COMPLIANCE_CATALOG:
        # Check if already seeded
        stmt = select(ComplianceRequirement).where(
            ComplianceRequirement.code == entry["code"]
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            continue

        # Resolve parent approval
        approval_code = entry.pop("approval_code", None)
        approval_id = None
        if approval_code:
            stmt_approval = select(Approval).where(Approval.code == approval_code)
            result_approval = await db.execute(stmt_approval)
            approval = result_approval.scalar_one_or_none()
            if approval:
                approval_id = approval.id

        if not approval_id:
            # Create a placeholder approval if none exists
            stmt_any = select(Approval).limit(1)
            result_any = await db.execute(stmt_any)
            any_approval = result_any.scalar_one_or_none()
            if any_approval:
                approval_id = any_approval.id
            else:
                logger.warning(f"No approvals exist to link compliance requirement {entry['code']}")
                continue

        req = ComplianceRequirement(
            approval_id=approval_id,
            code=entry["code"],
            title=entry["title"],
            description=entry.get("description"),
            category=entry["category"],
            frequency=entry["frequency"],
            frequency_months=entry["frequency_months"],
            priority=entry["priority"],
            warning_days=entry["warning_days"],
            statutory_act=entry.get("statutory_act"),
            penalty_description=entry.get("penalty_description"),
            penalty_amount_max=entry.get("penalty_amount_max", 0.0),
            required_documents=entry.get("required_documents", []),
            applicable_pollution_categories=entry.get("applicable_pollution_categories", []),
            applicable_industry_scales=entry.get("applicable_industry_scales", []),
            is_mandatory=entry.get("is_mandatory", True),
        )
        db.add(req)
        created.append(req)

    if created:
        await db.flush()
        logger.info(f"Seeded {len(created)} compliance requirements")

    return created


async def evaluate_business_compliance_requirements(
    db: AsyncSession,
    business_id: str,
) -> List[ComplianceRequirement]:
    """
    Fragment 93: Determine which compliance requirements apply to a specific
    business based on its profile (pollution category, industry scale).
    Returns all applicable ComplianceRequirement entries.
    """
    # Fetch business profile
    stmt_profile = select(BusinessProfile).where(
        BusinessProfile.business_id == business_id
    )
    result = await db.execute(stmt_profile)
    profile = result.scalar_one_or_none()

    pollution_cat = profile.pollution_category.value if profile and profile.pollution_category else None
    industry_scale = profile.industry_scale.value if profile and profile.industry_scale else None

    # Fetch all active compliance requirements
    stmt = select(ComplianceRequirement).where(ComplianceRequirement.is_active == True)
    result = await db.execute(stmt)
    all_requirements = list(result.scalars().all())

    applicable = []
    for req in all_requirements:
        # Check pollution category filter
        if req.applicable_pollution_categories:
            if not pollution_cat or pollution_cat not in req.applicable_pollution_categories:
                continue

        # Check industry scale filter
        if req.applicable_industry_scales:
            if not industry_scale or industry_scale not in req.applicable_industry_scales:
                continue

        applicable.append(req)

    return applicable


# ---------------------------------------------------------------------------
# Fragment 95: Deadline Calculation
# ---------------------------------------------------------------------------

def calculate_next_due_date(
    base_date: date,
    frequency_months: int,
) -> date:
    """
    Calculate the next compliance due date from a base date by adding
    the frequency interval in months.
    """
    year = base_date.year
    month = base_date.month + frequency_months

    while month > 12:
        month -= 12
        year += 1

    # Clamp day to valid range for target month
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(base_date.day, max_day)

    return date(year, month, day)


def calculate_warning_date(due_date: date, warning_days: int) -> date:
    """Calculate the warning/alert trigger date before a deadline."""
    return due_date - timedelta(days=warning_days)


def generate_cycle_label(due_date: date, frequency: ComplianceFrequency) -> str:
    """Generate a human-readable cycle label from the due date and frequency."""
    if frequency == ComplianceFrequency.MONTHLY:
        return f"{due_date.year}-{due_date.month:02d}"
    elif frequency == ComplianceFrequency.QUARTERLY:
        quarter = (due_date.month - 1) // 3 + 1
        return f"{due_date.year}-Q{quarter}"
    elif frequency == ComplianceFrequency.HALF_YEARLY:
        half = "H1" if due_date.month <= 6 else "H2"
        return f"{due_date.year}-{half}"
    elif frequency == ComplianceFrequency.ANNUAL:
        fy_start = due_date.year if due_date.month >= 4 else due_date.year - 1
        return f"FY{fy_start}-{(fy_start + 1) % 100:02d}"
    elif frequency == ComplianceFrequency.BIENNIAL:
        return f"{due_date.year}-{due_date.year + 2}"
    elif frequency == ComplianceFrequency.QUINQUENNIAL:
        return f"{due_date.year}-{due_date.year + 5}"
    else:
        return f"{due_date.isoformat()}"


async def generate_compliance_records_for_business(
    db: AsyncSession,
    business_id: str,
    base_date: Optional[date] = None,
    cycles_ahead: int = 1,
) -> List[ComplianceRecord]:
    """
    Generate compliance record entries for a business.
    Creates future obligation cycles based on applicable requirements.
    """
    if base_date is None:
        base_date = _today()

    applicable_reqs = await evaluate_business_compliance_requirements(db, business_id)
    created_records = []

    for req in applicable_reqs:
        # Check if records already exist for this business + requirement
        stmt = select(ComplianceRecord).where(
            and_(
                ComplianceRecord.business_id == business_id,
                ComplianceRecord.requirement_id == req.id,
                ComplianceRecord.status.in_([
                    ComplianceRecordStatus.UPCOMING,
                    ComplianceRecordStatus.DUE_SOON,
                    ComplianceRecordStatus.IN_PROGRESS,
                    ComplianceRecordStatus.SUBMITTED,
                ]),
            )
        )
        result = await db.execute(stmt)
        existing = list(result.scalars().all())

        if len(existing) >= cycles_ahead:
            continue

        # Generate upcoming cycles
        current_due = base_date
        for cycle_idx in range(cycles_ahead - len(existing)):
            if cycle_idx > 0 or not existing:
                due = calculate_next_due_date(current_due, req.frequency_months)
            else:
                due = calculate_next_due_date(base_date, req.frequency_months)

            cycle_label = generate_cycle_label(due, req.frequency)
            warning = calculate_warning_date(due, req.warning_days)

            # Determine initial status
            today = _today()
            if due < today:
                status = ComplianceRecordStatus.OVERDUE
            elif warning <= today:
                status = ComplianceRecordStatus.DUE_SOON
            else:
                status = ComplianceRecordStatus.UPCOMING

            record = ComplianceRecord(
                business_id=business_id,
                requirement_id=req.id,
                status=status,
                cycle_label=cycle_label,
                due_date=due,
                warning_date=warning,
                days_overdue=max(0, (today - due).days) if due < today else 0,
            )
            db.add(record)
            created_records.append(record)
            current_due = due

    if created_records:
        await db.flush()
        logger.info(
            f"Generated {len(created_records)} compliance records for business {business_id}"
        )

    return created_records


# ---------------------------------------------------------------------------
# Fragment 96: Renewal Tracking
# ---------------------------------------------------------------------------

async def create_renewal_from_application(
    db: AsyncSession,
    application: Application,
) -> Optional[ComplianceRecord]:
    """
    Automatically create a compliance renewal record when an application
    is approved and has a validity period. Links the compliance cycle
    back to the parent statutory clearance.
    """
    if application.status != ApplicationStatus.APPROVED:
        return None
    if not application.certificate_valid_until:
        return None

    # Find matching compliance requirement for this approval
    stmt = select(ComplianceRequirement).where(
        ComplianceRequirement.approval_id == application.approval_id,
        ComplianceRequirement.is_active == True,
    )
    result = await db.execute(stmt)
    requirements = list(result.scalars().all())

    if not requirements:
        return None

    req = requirements[0]  # Use primary requirement

    due_date = application.certificate_valid_until
    warning_date = calculate_warning_date(due_date, req.warning_days)
    cycle_label = generate_cycle_label(due_date, req.frequency)

    today = _today()
    if due_date < today:
        status = ComplianceRecordStatus.OVERDUE
    elif warning_date <= today:
        status = ComplianceRecordStatus.DUE_SOON
    else:
        status = ComplianceRecordStatus.UPCOMING

    record = ComplianceRecord(
        business_id=application.business_id,
        requirement_id=req.id,
        application_id=application.id,
        status=status,
        cycle_label=cycle_label,
        due_date=due_date,
        warning_date=warning_date,
        days_overdue=max(0, (today - due_date).days) if due_date < today else 0,
    )
    db.add(record)
    await db.flush()

    logger.info(
        f"Created renewal compliance record for application {application.application_number}, "
        f"due {due_date}"
    )
    return record


# ---------------------------------------------------------------------------
# Fragment 97: Compliance Alerts
# ---------------------------------------------------------------------------

async def get_compliance_alerts(
    db: AsyncSession,
    business_id: str,
) -> ComplianceAlertListResponse:
    """
    Generate real-time compliance alerts for a business.
    Surfaces OVERDUE, DUE_SOON, and EXPIRING obligations.
    """
    today = _today()

    # Fetch all non-terminal compliance records for this business
    stmt = select(ComplianceRecord).where(
        and_(
            ComplianceRecord.business_id == business_id,
            ComplianceRecord.is_active == True,
            ComplianceRecord.status.in_([
                ComplianceRecordStatus.UPCOMING,
                ComplianceRecordStatus.DUE_SOON,
                ComplianceRecordStatus.OVERDUE,
                ComplianceRecordStatus.IN_PROGRESS,
                ComplianceRecordStatus.SUBMITTED,
                ComplianceRecordStatus.EXPIRED,
            ]),
        )
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    # Fetch business name
    stmt_biz = select(Business).where(Business.id == business_id)
    result_biz = await db.execute(stmt_biz)
    business = result_biz.scalar_one_or_none()
    biz_name = business.legal_name if business else None

    alerts: List[ComplianceAlert] = []
    critical_count = 0
    high_count = 0

    for record in records:
        req = record.requirement
        if not req:
            continue

        days_remaining = (record.due_date - today).days

        # Determine alert type
        if record.status == ComplianceRecordStatus.OVERDUE or days_remaining < 0:
            alert_type = "OVERDUE"
            message = (
                f"⚠️ OVERDUE: {req.title} was due on {record.due_date.isoformat()}. "
                f"{abs(days_remaining)} days past deadline. "
                f"Penalty exposure: ₹{req.penalty_amount_max:,.0f}"
            )
        elif record.status == ComplianceRecordStatus.EXPIRED:
            alert_type = "EXPIRING"
            message = (
                f"🔴 EXPIRED: {req.title} has expired. Immediate renewal required."
            )
        elif record.status == ComplianceRecordStatus.DUE_SOON or (
            record.warning_date and today >= record.warning_date
        ):
            alert_type = "DUE_SOON"
            message = (
                f"🟡 DUE SOON: {req.title} is due in {days_remaining} days "
                f"({record.due_date.isoformat()}). Prepare filing documents."
            )
        elif days_remaining <= 7:
            alert_type = "PENALTY_RISK"
            message = (
                f"🔴 PENALTY RISK: {req.title} due in {days_remaining} days. "
                f"Late submission may incur penalties up to ₹{req.penalty_amount_max:,.0f}."
            )
        else:
            continue  # No alert needed for well-ahead items

        alert = ComplianceAlert(
            id=str(uuid.uuid4()),
            record_id=record.id,
            requirement_code=req.code,
            requirement_title=req.title,
            category=req.category,
            priority=req.priority,
            alert_type=alert_type,
            message=message,
            due_date=record.due_date,
            days_remaining=days_remaining,
            penalty_exposure=req.penalty_amount_max,
            business_id=business_id,
            business_name=biz_name,
        )
        alerts.append(alert)

        if req.priority == CompliancePriority.CRITICAL:
            critical_count += 1
        elif req.priority == CompliancePriority.HIGH:
            high_count += 1

    # Sort: overdue first, then by days_remaining ascending
    alerts.sort(key=lambda a: (a.days_remaining, -a.penalty_exposure))

    return ComplianceAlertListResponse(
        total=len(alerts),
        critical_count=critical_count,
        high_count=high_count,
        items=alerts,
    )


# ---------------------------------------------------------------------------
# Fragment 98: Compliance Status
# ---------------------------------------------------------------------------

async def get_compliance_status(
    db: AsyncSession,
    business_id: str,
) -> ComplianceStatusResponse:
    """
    Compute comprehensive compliance status for a business entity.
    Provides overall health rating and per-category breakdown.
    """
    today = _today()

    # First update statuses based on current dates
    await _refresh_compliance_statuses(db, business_id)

    # Fetch all records
    stmt = select(ComplianceRecord).where(
        and_(
            ComplianceRecord.business_id == business_id,
            ComplianceRecord.is_active == True,
        )
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    # Build category breakdown
    category_map: Dict[ComplianceCategory, Dict[str, int]] = {}
    for record in records:
        req = record.requirement
        if not req:
            continue

        cat = req.category
        if cat not in category_map:
            category_map[cat] = {
                "total": 0, "compliant": 0, "due_soon": 0,
                "overdue": 0, "expired": 0,
            }

        category_map[cat]["total"] += 1
        if record.status in (ComplianceRecordStatus.APPROVED, ComplianceRecordStatus.EXEMPTED):
            category_map[cat]["compliant"] += 1
        elif record.status == ComplianceRecordStatus.DUE_SOON:
            category_map[cat]["due_soon"] += 1
        elif record.status == ComplianceRecordStatus.OVERDUE:
            category_map[cat]["overdue"] += 1
        elif record.status == ComplianceRecordStatus.EXPIRED:
            category_map[cat]["expired"] += 1

    category_breakdown = []
    for cat, counts in category_map.items():
        total = counts["total"]
        compliance_rate = (counts["compliant"] / total * 100) if total > 0 else 0.0
        category_breakdown.append(ComplianceStatusSummary(
            category=cat,
            total=total,
            compliant=counts["compliant"],
            due_soon=counts["due_soon"],
            overdue=counts["overdue"],
            expired=counts["expired"],
            compliance_rate_percent=round(compliance_rate, 1),
        ))

    # Overall metrics
    total_records = len(records)
    compliant_total = sum(
        1 for r in records
        if r.status in (ComplianceRecordStatus.APPROVED, ComplianceRecordStatus.EXEMPTED)
    )
    overdue_total = sum(1 for r in records if r.status == ComplianceRecordStatus.OVERDUE)
    expired_total = sum(1 for r in records if r.status == ComplianceRecordStatus.EXPIRED)

    overall_rate = (compliant_total / total_records * 100) if total_records > 0 else 100.0

    if overdue_total > 0 or expired_total > 0:
        overall_health = "NON_COMPLIANT"
    elif overall_rate < 80:
        overall_health = "AT_RISK"
    else:
        overall_health = "HEALTHY"

    # Recent and upcoming deadlines
    recent = sorted(
        [r for r in records if r.due_date <= today],
        key=lambda r: r.due_date,
        reverse=True,
    )[:5]

    upcoming = sorted(
        [r for r in records if r.due_date > today],
        key=lambda r: r.due_date,
    )[:5]

    def to_summary(record: ComplianceRecord) -> ComplianceRecordSummary:
        req = record.requirement
        return ComplianceRecordSummary(
            id=record.id,
            business_id=record.business_id,
            requirement_id=record.requirement_id,
            status=record.status,
            cycle_label=record.cycle_label,
            due_date=record.due_date,
            days_overdue=record.days_overdue,
            requirement_code=req.code if req else None,
            requirement_title=req.title if req else None,
            requirement_category=req.category if req else None,
            requirement_priority=req.priority if req else None,
            penalty_imposed=record.penalty_imposed,
            created_at=_ensure_utc(record.created_at) or datetime.now(timezone.utc),
        )

    return ComplianceStatusResponse(
        business_id=business_id,
        overall_compliance_rate=round(overall_rate, 1),
        overall_health=overall_health,
        category_breakdown=category_breakdown,
        recent_deadlines=[to_summary(r) for r in recent],
        upcoming_deadlines=[to_summary(r) for r in upcoming],
    )


async def _refresh_compliance_statuses(
    db: AsyncSession,
    business_id: str,
) -> None:
    """
    Update compliance record statuses based on current date.
    Transitions UPCOMING → DUE_SOON when within warning window,
    and DUE_SOON → OVERDUE when past deadline.
    """
    today = _today()

    stmt = select(ComplianceRecord).where(
        and_(
            ComplianceRecord.business_id == business_id,
            ComplianceRecord.is_active == True,
            ComplianceRecord.status.in_([
                ComplianceRecordStatus.UPCOMING,
                ComplianceRecordStatus.DUE_SOON,
            ]),
        )
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    for record in records:
        if record.due_date < today:
            record.status = ComplianceRecordStatus.OVERDUE
            record.days_overdue = (today - record.due_date).days
        elif record.warning_date and today >= record.warning_date:
            record.status = ComplianceRecordStatus.DUE_SOON
        # else: remains UPCOMING

    await db.flush()


# ---------------------------------------------------------------------------
# Fragment 99: Compliance Prioritization
# ---------------------------------------------------------------------------

def _compute_urgency_score(
    days_remaining: int,
    priority: CompliancePriority,
    penalty_max: float,
    status: ComplianceRecordStatus,
) -> float:
    """
    Compute a composite urgency score for prioritization.
    Higher scores = more urgent action needed.

    Factors:
    - Days to deadline (inverse relationship)
    - Priority severity (CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1)
    - Penalty exposure (normalized)
    - Status escalation bonus
    """
    priority_weights = {
        CompliancePriority.CRITICAL: 4.0,
        CompliancePriority.HIGH: 3.0,
        CompliancePriority.MEDIUM: 2.0,
        CompliancePriority.LOW: 1.0,
    }

    status_bonus = {
        ComplianceRecordStatus.OVERDUE: 50.0,
        ComplianceRecordStatus.EXPIRED: 45.0,
        ComplianceRecordStatus.DUE_SOON: 20.0,
        ComplianceRecordStatus.IN_PROGRESS: 5.0,
        ComplianceRecordStatus.SUBMITTED: 2.0,
    }

    # Base: inverse of days remaining (capped to prevent extreme values)
    if days_remaining <= 0:
        time_score = 100.0 + abs(days_remaining) * 2
    elif days_remaining <= 7:
        time_score = 80.0
    elif days_remaining <= 30:
        time_score = 50.0
    elif days_remaining <= 90:
        time_score = 20.0
    else:
        time_score = 5.0

    pw = priority_weights.get(priority, 1.0)
    sb = status_bonus.get(status, 0.0)
    penalty_score = min(penalty_max / 100000.0, 10.0)  # Normalize to 0-10

    return round(time_score * pw + sb + penalty_score, 2)


def _recommended_action(
    status: ComplianceRecordStatus,
    days_remaining: int,
) -> str:
    """Generate a recommended action string based on status and urgency."""
    if status == ComplianceRecordStatus.OVERDUE:
        return "URGENT: File immediately to minimize penalties. Contact department for late submission guidance."
    elif status == ComplianceRecordStatus.EXPIRED:
        return "CRITICAL: Initiate renewal application immediately. Operations may be at risk."
    elif status == ComplianceRecordStatus.DUE_SOON and days_remaining <= 7:
        return "HIGH PRIORITY: Deadline imminent. Complete and submit filing within this week."
    elif status == ComplianceRecordStatus.DUE_SOON:
        return "Prepare filing documents and evidence. Submit before deadline to avoid penalties."
    elif status == ComplianceRecordStatus.IN_PROGRESS:
        return "Continue preparing filing. Ensure all required documents are collected."
    elif status == ComplianceRecordStatus.SUBMITTED:
        return "Filing submitted. Monitor for department response or approval."
    elif status == ComplianceRecordStatus.UPCOMING:
        if days_remaining <= 30:
            return "Start preparing documents for upcoming compliance filing."
        return "No immediate action required. Filing is scheduled for future cycle."
    return "Review compliance obligation status."


async def get_prioritized_compliance(
    db: AsyncSession,
    business_id: str,
    limit: int = 20,
) -> CompliancePrioritizedListResponse:
    """
    Return a prioritized action queue of compliance items for a business,
    ranked by urgency score. Used to drive the "What to do next" widget.
    """
    today = _today()

    await _refresh_compliance_statuses(db, business_id)

    stmt = select(ComplianceRecord).where(
        and_(
            ComplianceRecord.business_id == business_id,
            ComplianceRecord.is_active == True,
            ComplianceRecord.status.in_([
                ComplianceRecordStatus.OVERDUE,
                ComplianceRecordStatus.EXPIRED,
                ComplianceRecordStatus.DUE_SOON,
                ComplianceRecordStatus.UPCOMING,
                ComplianceRecordStatus.IN_PROGRESS,
                ComplianceRecordStatus.SUBMITTED,
            ]),
        )
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    items: List[Tuple[float, CompliancePrioritizedItem]] = []
    for record in records:
        req = record.requirement
        if not req:
            continue

        days_remaining = (record.due_date - today).days
        urgency = _compute_urgency_score(
            days_remaining, req.priority, req.penalty_amount_max, record.status
        )
        action = _recommended_action(record.status, days_remaining)

        item = CompliancePrioritizedItem(
            rank=0,  # Will be assigned after sorting
            record_id=record.id,
            requirement_code=req.code,
            requirement_title=req.title,
            category=req.category,
            priority=req.priority,
            status=record.status,
            due_date=record.due_date,
            days_remaining=days_remaining,
            penalty_exposure=req.penalty_amount_max,
            urgency_score=urgency,
            recommended_action=action,
            business_id=business_id,
        )
        items.append((urgency, item))

    # Sort by urgency descending
    items.sort(key=lambda x: x[0], reverse=True)

    # Assign ranks and limit
    ranked = []
    for idx, (score, item) in enumerate(items[:limit]):
        item.rank = idx + 1
        ranked.append(item)

    return CompliancePrioritizedListResponse(
        total=len(ranked),
        items=ranked,
    )


# ---------------------------------------------------------------------------
# Fragment 94 (partial): Compliance Dashboard Metrics
# ---------------------------------------------------------------------------

async def get_compliance_dashboard(
    db: AsyncSession,
    business_id: str,
) -> ComplianceDashboardMetrics:
    """
    Compute aggregate compliance dashboard metrics for a business entity.
    """
    today = _today()
    await _refresh_compliance_statuses(db, business_id)

    stmt = select(ComplianceRecord).where(
        and_(
            ComplianceRecord.business_id == business_id,
            ComplianceRecord.is_active == True,
        )
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    total = len(records)
    compliant = sum(
        1 for r in records
        if r.status in (ComplianceRecordStatus.APPROVED, ComplianceRecordStatus.EXEMPTED)
    )
    due_soon = sum(1 for r in records if r.status == ComplianceRecordStatus.DUE_SOON)
    overdue = sum(1 for r in records if r.status == ComplianceRecordStatus.OVERDUE)
    in_progress = sum(1 for r in records if r.status == ComplianceRecordStatus.IN_PROGRESS)
    submitted = sum(1 for r in records if r.status == ComplianceRecordStatus.SUBMITTED)
    exempted = sum(1 for r in records if r.status == ComplianceRecordStatus.EXEMPTED)
    expired = sum(1 for r in records if r.status == ComplianceRecordStatus.EXPIRED)

    compliance_rate = (compliant / total * 100) if total > 0 else 100.0

    total_penalty_exposure = sum(
        r.requirement.penalty_amount_max
        for r in records
        if r.requirement and r.status in (
            ComplianceRecordStatus.OVERDUE, ComplianceRecordStatus.EXPIRED
        )
    )
    total_penalties_imposed = sum(r.penalty_imposed for r in records)

    # Next deadline
    upcoming_records = sorted(
        [r for r in records if r.due_date >= today and r.status not in (
            ComplianceRecordStatus.APPROVED, ComplianceRecordStatus.EXEMPTED
        )],
        key=lambda r: r.due_date,
    )
    next_deadline = upcoming_records[0].due_date if upcoming_records else None

    # Most critical item
    critical_items = [
        r for r in records
        if r.requirement and r.requirement.priority == CompliancePriority.CRITICAL
        and r.status in (ComplianceRecordStatus.OVERDUE, ComplianceRecordStatus.DUE_SOON)
    ]
    most_critical = critical_items[0].requirement.title if critical_items else None

    return ComplianceDashboardMetrics(
        business_id=business_id,
        total_obligations=total,
        compliant_count=compliant,
        due_soon_count=due_soon,
        overdue_count=overdue,
        in_progress_count=in_progress,
        submitted_count=submitted,
        exempted_count=exempted,
        expired_count=expired,
        compliance_rate_percent=round(compliance_rate, 1),
        total_penalty_exposure=total_penalty_exposure,
        total_penalties_imposed=total_penalties_imposed,
        next_deadline=next_deadline,
        most_critical_item=most_critical,
    )


# ---------------------------------------------------------------------------
# CRUD Helpers for Compliance Records (Fragment 100 support)
# ---------------------------------------------------------------------------

async def get_compliance_records(
    db: AsyncSession,
    business_id: str,
    status_filter: Optional[ComplianceRecordStatus] = None,
    category_filter: Optional[ComplianceCategory] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ComplianceRecord], int]:
    """Fetch filtered compliance records for a business."""
    conditions = [
        ComplianceRecord.business_id == business_id,
        ComplianceRecord.is_active == True,
    ]
    if status_filter:
        conditions.append(ComplianceRecord.status == status_filter)

    stmt = select(ComplianceRecord).where(and_(*conditions))

    # Apply category filter via relationship
    if category_filter:
        stmt = stmt.join(ComplianceRequirement).where(
            ComplianceRequirement.category == category_filter
        )

    # Count
    count_stmt = select(func.count()).select_from(
        stmt.subquery()
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with pagination
    stmt = stmt.order_by(ComplianceRecord.due_date.asc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    return records, total


async def get_compliance_record_by_id(
    db: AsyncSession,
    record_id: str,
) -> ComplianceRecord:
    """Fetch a single compliance record by ID."""
    stmt = select(ComplianceRecord).where(ComplianceRecord.id == record_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundError(f"Compliance record {record_id} not found")
    return record


async def submit_compliance_filing(
    db: AsyncSession,
    record_id: str,
    filing_data: Dict[str, Any],
    evidence_document_ids: List[str],
    remarks: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ComplianceRecord:
    """Submit a compliance filing for a record."""
    record = await get_compliance_record_by_id(db, record_id)

    if record.status not in (
        ComplianceRecordStatus.UPCOMING,
        ComplianceRecordStatus.DUE_SOON,
        ComplianceRecordStatus.OVERDUE,
        ComplianceRecordStatus.IN_PROGRESS,
    ):
        raise BusinessRuleViolationError(
            f"Cannot submit filing for record in status '{record.status.value}'"
        )

    record.status = ComplianceRecordStatus.SUBMITTED
    record.filing_data = filing_data
    record.evidence_document_ids = evidence_document_ids
    record.remarks = remarks
    record.submitted_at = datetime.now(timezone.utc)
    record.responsible_user_id = user_id

    # Calculate overdue days at submission time
    today = _today()
    if record.due_date < today:
        record.days_overdue = (today - record.due_date).days

    await db.flush()
    logger.info(f"Compliance filing submitted for record {record_id}")
    return record


async def review_compliance_filing(
    db: AsyncSession,
    record_id: str,
    decision: str,
    officer_remarks: Optional[str] = None,
    new_valid_until: Optional[date] = None,
    penalty_imposed: float = 0.0,
) -> ComplianceRecord:
    """Officer reviews a submitted compliance filing."""
    record = await get_compliance_record_by_id(db, record_id)

    if record.status != ComplianceRecordStatus.SUBMITTED:
        raise BusinessRuleViolationError(
            f"Can only review records in SUBMITTED status, got '{record.status.value}'"
        )

    if decision == "APPROVED":
        record.status = ComplianceRecordStatus.APPROVED
        record.approved_at = datetime.now(timezone.utc)
        record.new_valid_until = new_valid_until
    elif decision == "REJECTED":
        record.status = ComplianceRecordStatus.REJECTED
    else:
        raise BusinessRuleViolationError(f"Invalid decision: {decision}")

    record.officer_remarks = officer_remarks
    record.penalty_imposed = penalty_imposed

    await db.flush()
    logger.info(f"Compliance record {record_id} reviewed: {decision}")
    return record


async def get_all_compliance_requirements(
    db: AsyncSession,
) -> List[ComplianceRequirement]:
    """Fetch all active compliance requirements."""
    stmt = select(ComplianceRequirement).where(
        ComplianceRequirement.is_active == True
    ).order_by(ComplianceRequirement.code)
    result = await db.execute(stmt)
    return list(result.scalars().all())
