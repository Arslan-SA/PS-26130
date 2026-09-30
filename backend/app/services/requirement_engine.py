"""
Statutory Requirement Discovery & Synchronization Engine (Fragment 45).
Orchestrates automated clearance identification, database reconciliation, fee summation,
and commissioning stage mapping for industrial enterprises.
"""

import logging
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.models.business import Business
from app.models.business_profile import BusinessProfile
from app.models.department import Department, JurisdictionLevel
from app.services.approval_rules import evaluate_approval_rules

logger = logging.getLogger("udyamsetu.requirement_engine")

# Canonical regulatory department master catalog
DEFAULT_DEPARTMENTS = [
    {
        "code": "SPCB",
        "name": "State Pollution Control Board",
        "jurisdiction_level": JurisdictionLevel.STATE,
        "standard_sla_days": 45,
        "description": "Environmental regulator enforcing Air & Water Pollution Prevention Acts.",
    },
    {
        "code": "FIRE",
        "name": "State Fire & Emergency Services",
        "jurisdiction_level": JurisdictionLevel.STATE,
        "standard_sla_days": 21,
        "description": "Fire safety prevention, inspection, and provisional/final NOC issuance.",
    },
    {
        "code": "DISH",
        "name": "Directorate of Industrial Safety & Health",
        "jurisdiction_level": JurisdictionLevel.STATE,
        "standard_sla_days": 30,
        "description": "Statutory labor welfare and factory safety inspectorate under Factories Act.",
    },
    {
        "code": "DISCOM",
        "name": "State Electricity Distribution Company",
        "jurisdiction_level": JurisdictionLevel.STATE,
        "standard_sla_days": 30,
        "description": "Electric utility providing HT/LT power connections and substation approvals.",
    },
    {
        "code": "CGWA",
        "name": "Central Ground Water Authority",
        "jurisdiction_level": JurisdictionLevel.CENTRAL,
        "standard_sla_days": 45,
        "description": "Central statutory authority regulating ground water abstraction in critical zones.",
    },
]

# Canonical approval catalog items matching statutory rules
DEFAULT_APPROVALS = [
    {
        "code": "CTE_PCB",
        "title": "Consent to Establish (CTE) under Water & Air Acts",
        "department_code": "SPCB",
        "issuing_authority": "State Pollution Control Board",
        "statutory_act": "Water Act 1974 & Air Act 1981",
        "validity_period_months": 60,
        "is_mandatory": True,
        "sla_days": 45,
        "estimated_fee_base": 25000.0,
        "description": "Mandatory prior environmental clearance before industrial construction.",
    },
    {
        "code": "CTO_PCB",
        "title": "Consent to Operate (CTO) under Water & Air Acts",
        "department_code": "SPCB",
        "issuing_authority": "State Pollution Control Board",
        "statutory_act": "Water Act 1974 & Air Act 1981",
        "validity_period_months": 60,
        "is_mandatory": True,
        "sla_days": 30,
        "estimated_fee_base": 20000.0,
        "description": "Mandatory prior to trial run or commercial operations to verify pollution control devices.",
    },
    {
        "code": "FIRE_NOC",
        "title": "Provisional Fire Safety Approval & Fire NOC",
        "department_code": "FIRE",
        "issuing_authority": "State Fire and Emergency Services",
        "statutory_act": "State Fire Prevention and Life Safety Measures Act",
        "validity_period_months": 12,
        "is_mandatory": True,
        "sla_days": 21,
        "estimated_fee_base": 15000.0,
        "description": "Fire prevention and life safety scheme approval before building plan sanction.",
    },
    {
        "code": "POWER_HT",
        "title": "High Tension (HT) Industrial Power Sanction & CEI Inspection",
        "department_code": "DISCOM",
        "issuing_authority": "Power Distribution Company & Chief Electrical Inspectorate",
        "statutory_act": "Electricity Act, 2003",
        "validity_period_months": None,
        "is_mandatory": True,
        "sla_days": 30,
        "estimated_fee_base": 25000.0,
        "description": "High tension load sanction, transformer testing, and line energization clearance.",
    },
    {
        "code": "FACTORY_LIC",
        "title": "Factory License & Factory Plan Approval",
        "department_code": "DISH",
        "issuing_authority": "Directorate of Industrial Safety and Health (DISH)",
        "statutory_act": "Factories Act, 1948",
        "validity_period_months": 120,
        "is_mandatory": True,
        "sla_days": 30,
        "estimated_fee_base": 10000.0,
        "description": "Factory plan approval and operating license under Section 6 & 7 of Factories Act.",
    },
    {
        "code": "CGWA_GW",
        "title": "Ground Water Abstraction & Tube-well NOC",
        "department_code": "CGWA",
        "issuing_authority": "Central Ground Water Authority",
        "statutory_act": "Environment (Protection) Act, 1986",
        "validity_period_months": 36,
        "is_mandatory": True,
        "sla_days": 45,
        "estimated_fee_base": 20000.0,
        "description": "Statutory permission for tube-well digging and ground water abstraction.",
    },
]


class RequirementEngineService:
    """Service orchestrating requirement discovery, DB reconciliation, and summary calculations."""

    @staticmethod
    async def seed_default_catalog(session: AsyncSession) -> None:
        """Seed default Department and Approval records if missing."""
        # 1. Seed departments
        for d in DEFAULT_DEPARTMENTS:
            stmt = select(Department).where(Department.code == d["code"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                dept = Department(**d)
                session.add(dept)

        # 2. Seed approvals
        for a in DEFAULT_APPROVALS:
            stmt = select(Approval).where(Approval.code == a["code"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                approval = Approval(**a)
                session.add(approval)

        await session.commit()

    @staticmethod
    async def generate_requirements_for_business(
        session: AsyncSession, business_id: str
    ) -> List[ApprovalRequirement]:
        """
        Evaluate business profile and reconcile database requirements idempotently.
        Preserves existing user progress while applying updated fees, SLAs, and newly triggered clearances.
        """
        await RequirementEngineService.seed_default_catalog(session)

        # Fetch Business and Profile
        stmt_biz = select(Business).where(Business.id == business_id)
        business = (await session.execute(stmt_biz)).scalar_one_or_none()
        if not business:
            raise ValueError(f"Business with ID {business_id} does not exist.")

        stmt_prof = select(BusinessProfile).where(BusinessProfile.business_id == business_id)
        profile = (await session.execute(stmt_prof)).scalar_one_or_none()
        if not profile:
            raise ValueError(f"No business profile found for business ID {business_id}.")

        # 1. Evaluate statutory rules
        rule_evaluations = evaluate_approval_rules(profile)
        triggered_codes = {r.approval_code: r for r in rule_evaluations}

        # 2. Fetch existing requirements
        stmt_req = select(ApprovalRequirement).where(ApprovalRequirement.business_id == business_id)
        existing_reqs = (await session.execute(stmt_req)).scalars().all()
        existing_by_approval_id: Dict[str, ApprovalRequirement] = {
            req.approval_id: req for req in existing_reqs
        }

        # 3. Fetch all catalog approvals for code resolution
        stmt_app = select(Approval)
        all_approvals = (await session.execute(stmt_app)).scalars().all()
        approvals_by_code = {a.code: a for a in all_approvals}

        result_requirements: List[ApprovalRequirement] = []

        # 4. Reconcile or create requirements for triggered rules
        for code, eval_res in triggered_codes.items():
            catalog_item = approvals_by_code.get(code)
            if not catalog_item:
                logger.warning("Approval code '%s' triggered but not in catalog.", code)
                continue

            existing = existing_by_approval_id.get(catalog_item.id)
            if existing:
                # Update dynamic calculated fields without overwriting user progress
                existing.estimated_fee = eval_res.estimated_fee
                existing.sla_deadline_days = eval_res.sla_days
                existing.trigger_reason = eval_res.trigger_reason
                existing.priority = eval_res.priority
                existing.stage = eval_res.stage
                existing.is_mandatory = eval_res.is_mandatory
                if existing.status == RequirementStatus.EXEMPTED:
                    existing.status = RequirementStatus.NOT_STARTED
                result_requirements.append(existing)
            else:
                # Create brand new requirement
                new_req = ApprovalRequirement(
                    business_id=business_id,
                    approval_id=catalog_item.id,
                    status=RequirementStatus.NOT_STARTED,
                    stage=eval_res.stage,
                    priority=eval_res.priority,
                    is_mandatory=eval_res.is_mandatory,
                    trigger_reason=eval_res.trigger_reason,
                    estimated_fee=eval_res.estimated_fee,
                    sla_deadline_days=eval_res.sla_days,
                )
                session.add(new_req)
                result_requirements.append(new_req)

        # 5. Handle untriggered requirements that previously existed (mark EXEMPTED)
        triggered_approval_ids = {
            approvals_by_code[code].id
            for code in triggered_codes
            if code in approvals_by_code
        }
        for approval_id, req in existing_by_approval_id.items():
            if approval_id not in triggered_approval_ids:
                if req.status == RequirementStatus.NOT_STARTED:
                    req.status = RequirementStatus.EXEMPTED
                    req.is_mandatory = False
                    req.trigger_reason = "No longer required due to updated profile classification."
                result_requirements.append(req)

        await session.commit()
        return result_requirements

    @staticmethod
    async def get_business_clearance_summary(
        session: AsyncSession, business_id: str
    ) -> Dict[str, Any]:
        """
        Compute consolidated clearance summary, fee aggregation, stage grouping,
        and statutory critical path turnaround metrics.
        """
        stmt = (
            select(ApprovalRequirement, Approval)
            .join(Approval, ApprovalRequirement.approval_id == Approval.id)
            .where(ApprovalRequirement.business_id == business_id)
        )
        rows = (await session.execute(stmt)).all()

        active_requirements = [
            req for req, _ in rows if req.status != RequirementStatus.EXEMPTED
        ]

        total_fee = sum(req.estimated_fee for req in active_requirements)
        mandatory_count = sum(1 for req in active_requirements if req.is_mandatory)

        # Group by stage
        by_stage: Dict[str, int] = {
            RequirementStage.PRE_ESTABLISHMENT.value: 0,
            RequirementStage.PRE_COMMISSIONING.value: 0,
            RequirementStage.POST_COMMISSIONING.value: 0,
            RequirementStage.REGULAR_OPERATIONS.value: 0,
        }
        for req in active_requirements:
            by_stage[req.stage.value] = by_stage.get(req.stage.value, 0) + 1

        # Group by department
        by_department: Dict[str, int] = {}
        for req, approval in rows:
            if req.status != RequirementStatus.EXEMPTED:
                dept = approval.department_code
                by_department[dept] = by_department.get(dept, 0) + 1

        # Status summary
        status_breakdown: Dict[str, int] = {}
        for req in active_requirements:
            st = req.status.value
            status_breakdown[st] = status_breakdown.get(st, 0) + 1

        # Longest critical path for pre-establishment phase
        pre_est_slas = [
            req.sla_deadline_days
            for req in active_requirements
            if req.stage == RequirementStage.PRE_ESTABLISHMENT and req.is_mandatory
        ]
        max_pre_est_days = max(pre_est_slas) if pre_est_slas else 0

        return {
            "business_id": business_id,
            "total_requirements": len(active_requirements),
            "mandatory_requirements": mandatory_count,
            "total_estimated_fee": total_fee,
            "pre_establishment_critical_days": max_pre_est_days,
            "by_stage": by_stage,
            "by_department": by_department,
            "status_breakdown": status_breakdown,
        }
