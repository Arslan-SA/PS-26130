"""
Government Schemes, Subsidies & AI/Rule Matching Engine (Phase 8, Fragments 105–106).

Provides:
- Scheme seed catalog with Central & State industrial incentive schemes.
- Deterministic & parametric eligibility scoring engine.
- Criterion-by-criterion explanation and audit breakdown.
- Document Vault gap analysis (checking uploaded vs required documents).
- Application and bookmark tracking.
"""

from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import generate_uuid, utc_now
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.document import Document
from app.models.scheme import (
    ApplicationMode,
    GovernmentScheme,
    SchemeApplication,
    SchemeApplicationStatus,
    SchemeEligibilityRule,
    SchemeLevel,
    SchemeType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed Data Definitions (Fragment 105)
# ---------------------------------------------------------------------------

SEED_SCHEMES_DATA: List[Dict[str, Any]] = [
    {
        "code": "SCHEME_PMEGP",
        "name": "Prime Minister's Employment Generation Programme (PMEGP)",
        "short_name": "PMEGP",
        "ministry": "Ministry of Micro, Small & Medium Enterprises (MSME)",
        "nodal_agency": "Khadi and Village Industries Commission (KVIC) & State DIC",
        "scheme_type": SchemeType.CAPITAL_SUBSIDY,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "New micro-enterprises in manufacturing and service sectors",
        "benefit_description": (
            "Credit-linked capital subsidy up to 35% of project cost for setting up new micro-manufacturing units "
            "(maximum project cost ₹50 Lakhs; max subsidy ₹17.5 Lakhs in rural areas, ₹12.5 Lakhs in urban areas)."
        ),
        "max_subsidy_amount": 1750000.0,
        "subsidy_percentage": 35.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://www.kviconline.gov.in/pmegpep/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "PROJECT_REPORT",
            "BANK_STATEMENT",
            "IDENTITY_PROOF",
        ],
        "tags": ["MSME", "MICRO", "SUBSIDY", "NEW_UNIT", "CAPITAL"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Udyam Registration",
                "instruction": "Ensure active Udyam Registration certificate is linked with Aadhaar.",
            },
            {
                "step": 2,
                "title": "Detailed Project Report (DPR)",
                "instruction": "Prepare a chartered-engineer verified project report detailing plant, machinery, and working capital needs under ₹50 Lakhs.",
            },
            {
                "step": 3,
                "title": "Online Portal Filing",
                "instruction": "Register and submit Form PMEGP-1 on the KVIC national portal with bank preference.",
            },
            {
                "step": 4,
                "title": "Task Force Scrutiny & Bank Sanction",
                "instruction": "District Task Force Committee interviews candidate and forwards proposal to the financing bank for credit sanction.",
            },
            {
                "step": 5,
                "title": "EDP Training & Subsidy Disbursement",
                "instruction": "Complete mandatory Entrepreneurship Development Programme (EDP) training to trigger margin money credit to escrow.",
            },
        ],
        "rule": {
            "min_investment": None,
            "max_investment": 5000000.0,  # Max 50 Lakhs
            "min_turnover": None,
            "max_turnover": 50000000.0,  # Max 5 Cr
            "allowed_msme_categories": ["MICRO"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "ONE_PERSON_COMPANY",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE"],
            "allowed_states": [],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": 1,
            "max_firm_age_years": 3,
            "min_score_threshold": 60.0,
        },
    },
    {
        "code": "SCHEME_CGTMSE",
        "name": "Credit Guarantee Scheme for Micro and Small Enterprises (CGTMSE)",
        "short_name": "CGTMSE",
        "ministry": "Ministry of MSME & SIDBI",
        "nodal_agency": "Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
        "scheme_type": SchemeType.CREDIT_GUARANTEE,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Micro and Small enterprises seeking term loans & working capital without collateral",
        "benefit_description": (
            "Collateral-free credit facility up to ₹500 Lakhs (₹5 Crores) with government guarantee cover ranging from "
            "75% to 85% of sanctioned facility, removing the requirement of third-party guarantees or mortgage assets."
        ),
        "max_subsidy_amount": 50000000.0,
        "subsidy_percentage": 85.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://www.cgtmse.in/",
        "application_mode": ApplicationMode.HYBRID,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "PROJECT_REPORT",
            "BANK_STATEMENT",
            "GST_CERTIFICATE",
            "ITR_RETURN",
        ],
        "tags": ["MSME", "COLLATERAL_FREE", "CREDIT_GUARANTEE", "WORKING_CAPITAL"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Credit Assessment",
                "instruction": "Determine credit requirement for plant, machinery, or working capital up to ₹5 Crores.",
            },
            {
                "step": 2,
                "title": "Member Lending Institution (MLI) Selection",
                "instruction": "Approach any scheduled commercial bank or approved NBFC enrolled under CGTMSE.",
            },
            {
                "step": 3,
                "title": "Application with CGTMSE Cover Request",
                "instruction": "Submit statutory business financials, GST returns, and project proposal with formal guarantee cover request.",
            },
            {
                "step": 4,
                "title": "Bank Guarantee Enrollment",
                "instruction": "The lending institution directly pays guarantee fee and enrolls credit facility in the CGTMSE portal.",
            },
        ],
        "rule": {
            "min_investment": None,
            "max_investment": 100000000.0,  # Max 10 Cr (Micro & Small)
            "min_turnover": None,
            "max_turnover": 500000000.0,  # Max 50 Cr
            "allowed_msme_categories": ["MICRO", "SMALL"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "PUBLIC_LIMITED",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE", "RED"],
            "allowed_states": [],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": None,
            "max_firm_age_years": None,
            "min_score_threshold": 60.0,
        },
    },
    {
        "code": "SCHEME_MUDRA_TARUN",
        "name": "Pradhan Mantri MUDRA Yojana (Tarun Scheme)",
        "short_name": "PM MUDRA (Tarun)",
        "ministry": "Ministry of Finance",
        "nodal_agency": "Micro Units Development & Refinance Agency Ltd. (MUDRA)",
        "scheme_type": SchemeType.INTEREST_SUBVENTION,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Growing micro-enterprises and artisan units needing capital expansion",
        "benefit_description": (
            "Collateral-free business loans between ₹5 Lakhs and ₹20 Lakhs with concessional interest subvention "
            "for procurement of plant equipment, modernization, and business scale-up."
        ),
        "max_subsidy_amount": 2000000.0,
        "subsidy_percentage": None,
        "interest_subsidy_rate": 2.5,
        "official_portal_url": "https://www.mudra.org.in/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "BANK_STATEMENT",
            "IDENTITY_PROOF",
            "GST_CERTIFICATE",
        ],
        "tags": ["MICRO", "LOAN", "INTEREST_SUBVENTION", "FINANCE"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Business Viability & Quotations",
                "instruction": "Obtain competitive machinery quotations and calculate 12-month projected cashflows.",
            },
            {
                "step": 2,
                "title": "UdyamMitra Application",
                "instruction": "Apply online at udyammitra.in under the Tarun category (₹10L - ₹20L bracket).",
            },
            {
                "step": 3,
                "title": "Sanction & MUDRA Card",
                "instruction": "Bank sanctions term loan and issues Mudra Debit Card for working capital overdraft drawdown.",
            },
        ],
        "rule": {
            "min_investment": None,
            "max_investment": 10000000.0,  # Up to 1 Cr
            "min_turnover": None,
            "max_turnover": 50000000.0,  # Up to 5 Cr
            "allowed_msme_categories": ["MICRO"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "ONE_PERSON_COMPANY",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE"],
            "allowed_states": [],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": None,
            "max_firm_age_years": None,
            "min_score_threshold": 55.0,
        },
    },
    {
        "code": "SCHEME_PLI_MANUFACTURING",
        "name": "Production Linked Incentive (PLI) Scheme for Advanced Manufacturing",
        "short_name": "PLI Scheme",
        "ministry": "Ministry of Commerce & Industry / DPIIT",
        "nodal_agency": "Industrial Project Monitoring Agency (IFCI & SIDBI)",
        "scheme_type": SchemeType.PRODUCTION_LINKED_INCENTIVE,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Medium and Large manufacturing enterprises expanding domestic manufacturing capacities",
        "benefit_description": (
            "Direct cash incentive of 4% to 6% on incremental sales (over base year) of goods manufactured in India "
            "for 5 consecutive fiscal years, up to ₹25 Crores annually."
        ),
        "max_subsidy_amount": 250000000.0,  # ₹25 Cr
        "subsidy_percentage": 6.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://www.dpiit.gov.in/production-linked-incentive-scheme",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "GST_CERTIFICATE",
            "CA_NETWORTH",
            "PROJECT_REPORT",
            "BOARD_RESOLUTION",
            "AUDITED_FINANCIALS",
        ],
        "tags": ["LARGE", "MEDIUM", "SUNRISE", "MANUFACTURING", "PLI", "EXPORT"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Sector & Threshold Verification",
                "instruction": "Confirm minimum committed cumulative incremental investment of ₹2.5 Crores.",
            },
            {
                "step": 2,
                "title": "RFP Portal Registration",
                "instruction": "Submit pre-qualification application on the DPIIT PLI portal during the open window.",
            },
            {
                "step": 3,
                "title": "Empowered Committee Approval",
                "instruction": "Empowered Group of Secretaries (EGoS) evaluates domestic value addition and sanctions baseline.",
            },
            {
                "step": 4,
                "title": "Quarterly Incentive Claim",
                "instruction": "Submit quarterly statutory auditor verified sales certificates to receive direct benefit transfer.",
            },
        ],
        "rule": {
            "min_investment": 25000000.0,  # Min ₹2.5 Cr investment
            "max_investment": None,
            "min_turnover": 50000000.0,  # Min ₹5 Cr turnover
            "max_turnover": None,
            "allowed_msme_categories": ["MEDIUM", "LARGE"],
            "allowed_entity_types": ["PRIVATE_LIMITED", "PUBLIC_LIMITED"],
            "allowed_sectors_nic": ["20", "21", "26", "27", "28", "29", "30"],  # Chemicals, Pharma, Electronics, Auto
            "allowed_pollution_categories": ["GREEN", "ORANGE", "RED"],
            "allowed_states": [],
            "requires_udyam": False,
            "requires_women_ownership": False,
            "min_employees": 20,
            "max_firm_age_years": None,
            "min_score_threshold": 55.0,
        },
    },
    {
        "code": "SCHEME_ZED_CERTIFICATION",
        "name": "MSME Sustainable (ZED - Zero Defect Zero Effect) Certification Scheme",
        "short_name": "ZED Certification Subsidy",
        "ministry": "Ministry of Micro, Small & Medium Enterprises (MSME)",
        "nodal_agency": "Quality Council of India (QCI)",
        "scheme_type": SchemeType.QUALITY_CERTIFICATION,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Manufacturing MSMEs adopting eco-friendly and high-quality production benchmarks",
        "benefit_description": (
            "Direct reimbursement subsidy up to 80% on Bronze/Silver/Gold ZED certification cost (max ₹8 Lakhs), "
            "plus up to ₹5 Lakhs for consulting/handholding support and ₹3 Lakhs for zero-waste technology adoption."
        ),
        "max_subsidy_amount": 800000.0,
        "subsidy_percentage": 80.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://zed.msme.gov.in/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "POLLUTION_NOC",
            "GST_CERTIFICATE",
        ],
        "tags": ["MSME", "SUSTAINABILITY", "QUALITY", "ZED", "GREEN", "CERTIFICATION"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "ZED Pledge & Self-Assessment",
                "instruction": "Take the digital ZED pledge and complete the online self-assessment parameters.",
            },
            {
                "step": 2,
                "title": "Select Certification Level",
                "instruction": "Choose target benchmark: Bronze, Silver, or Gold certification tier.",
            },
            {
                "step": 3,
                "title": "QCI Desktop & On-site Assessment",
                "instruction": "Accredited assessment agency audits manufacturing unit process, safety, and pollution controls.",
            },
            {
                "step": 4,
                "title": "Subsidy Reimbursement",
                "instruction": "Upon certification award, 80% of testing and audit fees are credited back to the enterprise bank account.",
            },
        ],
        "rule": {
            "min_investment": None,
            "max_investment": 500000000.0,  # MSMEs up to 50 Cr
            "min_turnover": None,
            "max_turnover": 2500000000.0,
            "allowed_msme_categories": ["MICRO", "SMALL", "MEDIUM"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "ONE_PERSON_COMPANY",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE"],
            "allowed_states": [],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": None,
            "max_firm_age_years": None,
            "min_score_threshold": 50.0,
        },
    },
    {
        "code": "SCHEME_CLCSS_TECH",
        "name": "Credit Linked Capital Subsidy Scheme (CLCSS) for Technology Upgradation",
        "short_name": "CLCSS Tech Upgradation",
        "ministry": "Ministry of Micro, Small & Medium Enterprises (MSME)",
        "nodal_agency": "Small Industries Development Bank of India (SIDBI)",
        "scheme_type": SchemeType.TECHNOLOGY_UPGRADATION,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Micro and Small industrial manufacturing units inducting modern plant & machinery",
        "benefit_description": (
            "15% upfront capital subsidy on institutional finance up to ₹1 Crore (maximum subsidy ₹15 Lakhs) for "
            "replacing obsolete manufacturing technologies with validated energy-efficient machinery."
        ),
        "max_subsidy_amount": 1500000.0,
        "subsidy_percentage": 15.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://clcss.dcmsme.gov.in/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "PROJECT_REPORT",
            "BANK_STATEMENT",
            "CA_NETWORTH",
            "GST_CERTIFICATE",
        ],
        "tags": ["MSME", "TECHNOLOGY", "MODERNIZATION", "CAPITAL_SUBSIDY"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Approved Technology Identification",
                "instruction": "Select modernized machinery listed in the Ministry approved technology sub-sectors list.",
            },
            {
                "step": 2,
                "title": "Term Loan Application",
                "instruction": "Apply for term loan at a scheduled bank specifying CLCSS subsidy route.",
            },
            {
                "step": 3,
                "title": "Online Subsidy Tracking System (MSIS)",
                "instruction": "Lending branch uploads project invoice details on the online CLCSS portal for nodal approval.",
            },
            {
                "step": 4,
                "title": "Term Deposit Lien Release",
                "instruction": "Subsidy is kept in fixed deposit for 3 years, after which it liquidates against the principal debt.",
            },
        ],
        "rule": {
            "min_investment": 100000.0,
            "max_investment": 100000000.0,  # Micro & Small
            "min_turnover": None,
            "max_turnover": 500000000.0,
            "allowed_msme_categories": ["MICRO", "SMALL"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE", "RED"],
            "allowed_states": [],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": None,
            "max_firm_age_years": None,
            "min_score_threshold": 55.0,
        },
    },
    {
        "code": "SCHEME_STATE_CAPITAL_SUBSIDY",
        "name": "State Industrial Policy Capital Investment Subsidy (Maharashtra)",
        "short_name": "State Industrial Capital Subsidy",
        "ministry": "Industries, Energy & Labour Department, Government of Maharashtra",
        "nodal_agency": "Directorate of Industries & MIDC",
        "scheme_type": SchemeType.CAPITAL_SUBSIDY,
        "level": SchemeLevel.STATE,
        "state": "Maharashtra",
        "target_beneficiary": "Industrial units investing in designated MIDC industrial parks & Talukas (B, C, D, D+)",
        "benefit_description": (
            "Up to 25% capital subsidy on eligible fixed capital assets (land, building, plant & machinery) "
            "up to ₹50 Lakhs, plus 100% stamp duty exemption on industrial land lease agreements."
        ),
        "max_subsidy_amount": 5000000.0,
        "subsidy_percentage": 25.0,
        "interest_subsidy_rate": 5.0,
        "official_portal_url": "https://maitri.mahaonline.gov.in/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "UDYAM_CERTIFICATE",
            "LAND_LEASE",
            "PROJECT_REPORT",
            "GST_CERTIFICATE",
            "POLLUTION_NOC",
        ],
        "tags": ["STATE_POLICY", "MAHARASHTRA", "MIDC", "CAPITAL_SUBSIDY", "STAMP_DUTY"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Industrial Location Categorization",
                "instruction": "Verify unit falls inside developing industrial area (Taluka Category B, C, D, or D+).",
            },
            {
                "step": 2,
                "title": "Eligibility Certificate (EC)",
                "instruction": "Apply for Eligibility Certificate on MAITRI Single Window portal within 6 months of commencement.",
            },
            {
                "step": 3,
                "title": "Joint Inspection",
                "instruction": "District Industries Centre (DIC) inspects plant assets and verifies fixed capital expenditure bills.",
            },
            {
                "step": 4,
                "title": "Direct Treasury Credit",
                "instruction": "Annual installment disbursement directly to industrial unit bank account.",
            },
        ],
        "rule": {
            "min_investment": 500000.0,
            "max_investment": 500000000.0,
            "min_turnover": None,
            "max_turnover": None,
            "allowed_msme_categories": ["MICRO", "SMALL", "MEDIUM"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "PUBLIC_LIMITED",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["WHITE", "GREEN", "ORANGE", "RED"],
            "allowed_states": ["Maharashtra"],
            "requires_udyam": True,
            "requires_women_ownership": False,
            "min_employees": 5,
            "max_firm_age_years": 5,
            "min_score_threshold": 55.0,
        },
    },
    {
        "code": "SCHEME_GREEN_EFFLUENT_SUBSIDY",
        "name": "Pollution Abatement & Effluent Treatment Infrastructure Subsidy",
        "short_name": "Green Industry Abatement Incentive",
        "ministry": "Ministry of Environment, Forest and Climate Change (MoEFCC)",
        "nodal_agency": "Central Pollution Control Board (CPCB) & State SPCB",
        "scheme_type": SchemeType.GREEN_INCENTIVE,
        "level": SchemeLevel.CENTRAL,
        "state": None,
        "target_beneficiary": "Industrial units in Orange and Red categories installing ETP, CETP, or Zero Liquid Discharge (ZLD)",
        "benefit_description": (
            "50% capital reimbursement subsidy (maximum ₹75 Lakhs) for procurement and installation of Effluent Treatment Plants "
            "(ETP), online continuous effluent monitoring systems (OCEMS), and solar rooftop systems."
        ),
        "max_subsidy_amount": 7500000.0,
        "subsidy_percentage": 50.0,
        "interest_subsidy_rate": None,
        "official_portal_url": "https://cpcb.nic.in/",
        "application_mode": ApplicationMode.ONLINE,
        "required_document_codes": [
            "PAN_CARD",
            "POLLUTION_NOC",
            "PROJECT_REPORT",
            "SITE_PLAN",
            "GST_CERTIFICATE",
        ],
        "tags": ["GREEN", "POLLUTION", "ETP", "ZLD", "CPCB", "RENEWABLE"],
        "guidance_steps": [
            {
                "step": 1,
                "title": "Consent to Establish (CTE) & Design Vetting",
                "instruction": "Submit engineering layout for ETP/OCEMS to State Pollution Control Board for engineering approval.",
            },
            {
                "step": 2,
                "title": "Equipment Procurement & Commissioning",
                "instruction": "Install certified effluent treatment hardware and connect telemetry feed to CPCB central servers.",
            },
            {
                "step": 3,
                "title": "Performance Audit",
                "instruction": "SPCB regional laboratory samples treated discharge to certify zero-liquid discharge or compliant BOD/COD limits.",
            },
            {
                "step": 4,
                "title": "Subsidy Sanction",
                "instruction": "MoEFCC sanctions 50% capital outlay directly to the industrial enterprise.",
            },
        ],
        "rule": {
            "min_investment": 1000000.0,  # Min 10 Lakhs
            "max_investment": None,
            "min_turnover": None,
            "max_turnover": None,
            "allowed_msme_categories": ["MICRO", "SMALL", "MEDIUM", "LARGE"],
            "allowed_entity_types": [
                "PROPRIETORSHIP",
                "PARTNERSHIP",
                "LLP",
                "PRIVATE_LIMITED",
                "PUBLIC_LIMITED",
            ],
            "allowed_sectors_nic": [],
            "allowed_pollution_categories": ["ORANGE", "RED"],  # Specifically for polluting industries
            "allowed_states": [],
            "requires_udyam": False,
            "requires_women_ownership": False,
            "min_employees": None,
            "max_firm_age_years": None,
            "min_score_threshold": 55.0,
        },
    },
]


# ---------------------------------------------------------------------------
# Database Seeding Service
# ---------------------------------------------------------------------------

async def seed_government_schemes(db: AsyncSession) -> int:
    """
    Seed initial Government Schemes and Eligibility Rules into database.
    Idempotent: updates existing schemes if already present by code.
    Returns count of schemes seeded/updated.
    """
    seeded_count = 0

    for item in SEED_SCHEMES_DATA:
        stmt = select(GovernmentScheme).where(GovernmentScheme.code == item["code"])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        rule_data = item.get("rule", {})

        if not existing:
            scheme = GovernmentScheme(
                id=generate_uuid(),
                code=item["code"],
                name=item["name"],
                short_name=item["short_name"],
                ministry=item["ministry"],
                nodal_agency=item["nodal_agency"],
                scheme_type=item["scheme_type"],
                level=item["level"],
                state=item.get("state"),
                target_beneficiary=item["target_beneficiary"],
                benefit_description=item["benefit_description"],
                max_subsidy_amount=item.get("max_subsidy_amount"),
                subsidy_percentage=item.get("subsidy_percentage"),
                interest_subsidy_rate=item.get("interest_subsidy_rate"),
                official_portal_url=item.get("official_portal_url"),
                application_mode=item["application_mode"],
                guidance_steps=item.get("guidance_steps", []),
                required_document_codes=item.get("required_document_codes", []),
                tags=item.get("tags", []),
            )
            db.add(scheme)
            await db.flush()

            rule = SchemeEligibilityRule(
                id=generate_uuid(),
                scheme_id=scheme.id,
                min_investment=rule_data.get("min_investment"),
                max_investment=rule_data.get("max_investment"),
                min_turnover=rule_data.get("min_turnover"),
                max_turnover=rule_data.get("max_turnover"),
                allowed_msme_categories=rule_data.get("allowed_msme_categories", []),
                allowed_entity_types=rule_data.get("allowed_entity_types", []),
                allowed_sectors_nic=rule_data.get("allowed_sectors_nic", []),
                allowed_pollution_categories=rule_data.get("allowed_pollution_categories", []),
                allowed_states=rule_data.get("allowed_states", []),
                requires_udyam=rule_data.get("requires_udyam", False),
                requires_women_ownership=rule_data.get("requires_women_ownership", False),
                min_employees=rule_data.get("min_employees"),
                max_firm_age_years=rule_data.get("max_firm_age_years"),
                min_score_threshold=rule_data.get("min_score_threshold", 50.0),
            )
            db.add(rule)
            seeded_count += 1
        else:
            # Update attributes
            existing.name = item["name"]
            existing.short_name = item["short_name"]
            existing.ministry = item["ministry"]
            existing.nodal_agency = item["nodal_agency"]
            existing.scheme_type = item["scheme_type"]
            existing.level = item["level"]
            existing.state = item.get("state")
            existing.target_beneficiary = item["target_beneficiary"]
            existing.benefit_description = item["benefit_description"]
            existing.max_subsidy_amount = item.get("max_subsidy_amount")
            existing.subsidy_percentage = item.get("subsidy_percentage")
            existing.interest_subsidy_rate = item.get("interest_subsidy_rate")
            existing.official_portal_url = item.get("official_portal_url")
            existing.application_mode = item["application_mode"]
            existing.guidance_steps = item.get("guidance_steps", [])
            existing.required_document_codes = item.get("required_document_codes", [])
            existing.tags = item.get("tags", [])

            # Update rule if exists
            stmt_rule = select(SchemeEligibilityRule).where(SchemeEligibilityRule.scheme_id == existing.id)
            res_rule = await db.execute(stmt_rule)
            rule = res_rule.scalar_one_or_none()
            if rule:
                rule.min_investment = rule_data.get("min_investment")
                rule.max_investment = rule_data.get("max_investment")
                rule.min_turnover = rule_data.get("min_turnover")
                rule.max_turnover = rule_data.get("max_turnover")
                rule.allowed_msme_categories = rule_data.get("allowed_msme_categories", [])
                rule.allowed_entity_types = rule_data.get("allowed_entity_types", [])
                rule.allowed_sectors_nic = rule_data.get("allowed_sectors_nic", [])
                rule.allowed_pollution_categories = rule_data.get("allowed_pollution_categories", [])
                rule.allowed_states = rule_data.get("allowed_states", [])
                rule.requires_udyam = rule_data.get("requires_udyam", False)
                rule.requires_women_ownership = rule_data.get("requires_women_ownership", False)
                rule.min_employees = rule_data.get("min_employees")
                rule.max_firm_age_years = rule_data.get("max_firm_age_years")
                rule.min_score_threshold = rule_data.get("min_score_threshold", 50.0)
            seeded_count += 1

    await db.commit()
    logger.info("Successfully seeded %d government schemes", seeded_count)
    return seeded_count


# ---------------------------------------------------------------------------
# Eligibility Matching Engine (Fragment 106)
# ---------------------------------------------------------------------------

class CriterionResult:
    """Individual criterion evaluation report."""
    def __init__(
        self,
        name: str,
        status: str,  # "PASS" | "FAIL" | "WARNING" | "NOT_APPLICABLE"
        score_weight: float,
        earned_score: float,
        required_val: str,
        actual_val: str,
        explanation: str,
        is_hard_criterion: bool = True,
    ):
        self.name = name
        self.status = status
        self.score_weight = score_weight
        self.earned_score = earned_score
        self.required_val = required_val
        self.actual_val = actual_val
        self.explanation = explanation
        self.is_hard_criterion = is_hard_criterion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "score_weight": self.score_weight,
            "earned_score": self.earned_score,
            "required_val": self.required_val,
            "actual_val": self.actual_val,
            "explanation": self.explanation,
            "is_hard_criterion": self.is_hard_criterion,
        }


def evaluate_scheme_eligibility(
    scheme: GovernmentScheme,
    business: Business,
    profile: Optional[BusinessProfile] = None,
) -> Dict[str, Any]:
    """
    Evaluates a business entity & profile against a specific scheme's rules.
    Returns:
    - match_score: float (0.0 to 100.0)
    - is_eligible: bool
    - criteria_breakdown: List of CriterionResult dictionaries
    - matching_criteria: List of names of criteria that passed
    - unmet_criteria: List of names of criteria that failed
    - recommendations: List of helpful advice strings
    - estimated_subsidy_amount: Estimated cash subsidy in INR
    """
    rule = scheme.rule
    if not rule:
        # Default pass if no explicit rule defined
        return {
            "scheme_id": scheme.id,
            "scheme_code": scheme.code,
            "match_score": 100.0,
            "is_eligible": True,
            "criteria_breakdown": [],
            "matching_criteria": ["All General Criteria"],
            "unmet_criteria": [],
            "recommendations": ["Directly eligible to apply on portal."],
            "estimated_subsidy_amount": scheme.max_subsidy_amount,
        }

    criteria: List[CriterionResult] = []
    total_weights = 0.0
    earned_weights = 0.0
    hard_criterion_failed = False

    # 1. MSME Classification (Weight: 25)
    weight_msme = 25.0
    total_weights += weight_msme
    user_msme = business.msme_category.value if business.msme_category else "MICRO"
    if rule.allowed_msme_categories:
        if user_msme in rule.allowed_msme_categories:
            criteria.append(CriterionResult(
                name="MSME Classification",
                status="PASS",
                score_weight=weight_msme,
                earned_score=weight_msme,
                required_val=", ".join(rule.allowed_msme_categories),
                actual_val=user_msme,
                explanation=f"Business is categorized as {user_msme}, which meets scheme requirements.",
                is_hard_criterion=True,
            ))
            earned_weights += weight_msme
        else:
            criteria.append(CriterionResult(
                name="MSME Classification",
                status="FAIL",
                score_weight=weight_msme,
                earned_score=0.0,
                required_val=", ".join(rule.allowed_msme_categories),
                actual_val=user_msme,
                explanation=f"Scheme strictly requires {', '.join(rule.allowed_msme_categories)} (unit is {user_msme}).",
                is_hard_criterion=True,
            ))
            hard_criterion_failed = True
    else:
        criteria.append(CriterionResult(
            name="MSME Classification",
            status="NOT_APPLICABLE",
            score_weight=weight_msme,
            earned_score=weight_msme,
            required_val="Any MSME Category",
            actual_val=user_msme,
            explanation="No restriction on MSME size.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_msme

    # 2. Plant & Machinery Investment (Weight: 20)
    weight_inv = 20.0
    total_weights += weight_inv
    actual_inv = (profile.plant_machinery_investment if profile and profile.plant_machinery_investment is not None else 0.0)
    inv_pass = True
    inv_exp = []
    if rule.min_investment is not None and actual_inv < rule.min_investment:
        inv_pass = False
        inv_exp.append(f"Min required ₹{rule.min_investment:,.0f} (actual ₹{actual_inv:,.0f})")
    if rule.max_investment is not None and actual_inv > rule.max_investment:
        inv_pass = False
        inv_exp.append(f"Max limit ₹{rule.max_investment:,.0f} (actual ₹{actual_inv:,.0f})")

    min_inv_str = f"₹{rule.min_investment:,.0f}" if rule.min_investment is not None else "₹0"
    max_inv_str = f"₹{rule.max_investment:,.0f}" if rule.max_investment is not None else "No Cap"
    req_inv_str = f"{min_inv_str} – {max_inv_str}" if (rule.min_investment is not None or rule.max_investment is not None) else "No Limit"
    if inv_pass:
        criteria.append(CriterionResult(
            name="Investment in Plant & Machinery",
            status="PASS",
            score_weight=weight_inv,
            earned_score=weight_inv,
            required_val=req_inv_str,
            actual_val=f"₹{actual_inv:,.0f}",
            explanation=f"Investment ₹{actual_inv:,.0f} is within permitted range.",
            is_hard_criterion=True,
        ))
        earned_weights += weight_inv
    else:
        criteria.append(CriterionResult(
            name="Investment in Plant & Machinery",
            status="FAIL",
            score_weight=weight_inv,
            earned_score=0.0,
            required_val=req_inv_str,
            actual_val=f"₹{actual_inv:,.0f}",
            explanation=f"Investment out of bounds: {'; '.join(inv_exp)}.",
            is_hard_criterion=True,
        ))
        hard_criterion_failed = True

    # 3. Annual Turnover (Weight: 15)
    weight_to = 15.0
    total_weights += weight_to
    actual_turnover = (profile.annual_turnover if profile and profile.annual_turnover is not None else 0.0)
    to_pass = True
    to_exp = []
    if rule.min_turnover is not None and actual_turnover < rule.min_turnover:
        to_pass = False
        to_exp.append(f"Min turnover ₹{rule.min_turnover:,.0f}")
    if rule.max_turnover is not None and actual_turnover > rule.max_turnover:
        to_pass = False
        to_exp.append(f"Max turnover cap ₹{rule.max_turnover:,.0f}")

    min_to_str = f"₹{rule.min_turnover:,.0f}" if rule.min_turnover is not None else "₹0"
    max_to_str = f"₹{rule.max_turnover:,.0f}" if rule.max_turnover is not None else "No Cap"
    req_to_str = f"{min_to_str} – {max_to_str}" if (rule.min_turnover is not None or rule.max_turnover is not None) else "No Limit"
    if to_pass:
        criteria.append(CriterionResult(
            name="Annual Turnover",
            status="PASS",
            score_weight=weight_to,
            earned_score=weight_to,
            required_val=req_to_str,
            actual_val=f"₹{actual_turnover:,.0f}",
            explanation=f"Annual turnover ₹{actual_turnover:,.0f} satisfies scheme criteria.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_to
    else:
        criteria.append(CriterionResult(
            name="Annual Turnover",
            status="FAIL",
            score_weight=weight_to,
            earned_score=0.0,
            required_val=req_to_str,
            actual_val=f"₹{actual_turnover:,.0f}",
            explanation=f"Turnover threshold not satisfied: {'; '.join(to_exp)}.",
            is_hard_criterion=False,
        ))

    # 4. Legal Entity Constitution (Weight: 10)
    weight_entity = 10.0
    total_weights += weight_entity
    actual_entity = business.entity_type.value if business.entity_type else "PRIVATE_LIMITED"
    if rule.allowed_entity_types:
        if actual_entity in rule.allowed_entity_types:
            criteria.append(CriterionResult(
                name="Entity Constitution",
                status="PASS",
                score_weight=weight_entity,
                earned_score=weight_entity,
                required_val=", ".join(rule.allowed_entity_types),
                actual_val=actual_entity,
                explanation=f"{actual_entity} constitution is recognized by scheme.",
                is_hard_criterion=True,
            ))
            earned_weights += weight_entity
        else:
            criteria.append(CriterionResult(
                name="Entity Constitution",
                status="FAIL",
                score_weight=weight_entity,
                earned_score=0.0,
                required_val=", ".join(rule.allowed_entity_types),
                actual_val=actual_entity,
                explanation=f"Entity type {actual_entity} not accepted for this scheme.",
                is_hard_criterion=True,
            ))
            hard_criterion_failed = True
    else:
        criteria.append(CriterionResult(
            name="Entity Constitution",
            status="NOT_APPLICABLE",
            score_weight=weight_entity,
            earned_score=weight_entity,
            required_val="Any",
            actual_val=actual_entity,
            explanation="Open to all legal constitutions.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_entity

    # 5. Environmental / Pollution Category (Weight: 10)
    weight_env = 10.0
    total_weights += weight_env
    actual_pollution = profile.pollution_category.value if profile and profile.pollution_category else "GREEN"
    if rule.allowed_pollution_categories:
        if actual_pollution in rule.allowed_pollution_categories:
            criteria.append(CriterionResult(
                name="CPCB Environmental Classification",
                status="PASS",
                score_weight=weight_env,
                earned_score=weight_env,
                required_val=", ".join(rule.allowed_pollution_categories),
                actual_val=actual_pollution,
                explanation=f"Pollution category {actual_pollution} is eligible.",
                is_hard_criterion=True,
            ))
            earned_weights += weight_env
        else:
            criteria.append(CriterionResult(
                name="CPCB Environmental Classification",
                status="FAIL",
                score_weight=weight_env,
                earned_score=0.0,
                required_val=", ".join(rule.allowed_pollution_categories),
                actual_val=actual_pollution,
                explanation=f"Scheme specifically targeted to {', '.join(rule.allowed_pollution_categories)} (unit is {actual_pollution}).",
                is_hard_criterion=True,
            ))
            hard_criterion_failed = True
    else:
        criteria.append(CriterionResult(
            name="CPCB Environmental Classification",
            status="NOT_APPLICABLE",
            score_weight=weight_env,
            earned_score=weight_env,
            required_val="Any",
            actual_val=actual_pollution,
            explanation="No pollution category restriction.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_env

    # 6. Industrial Sector / NIC Code (Weight: 10)
    weight_nic = 10.0
    total_weights += weight_nic
    actual_nic = profile.nic_code if profile and profile.nic_code else ""
    if rule.allowed_sectors_nic:
        nic_match = False
        for allowed in rule.allowed_sectors_nic:
            if actual_nic.startswith(allowed):
                nic_match = True
                break
        if nic_match:
            criteria.append(CriterionResult(
                name="Industrial Sector / NIC Match",
                status="PASS",
                score_weight=weight_nic,
                earned_score=weight_nic,
                required_val=", ".join(rule.allowed_sectors_nic),
                actual_val=actual_nic or "General",
                explanation=f"NIC activity code {actual_nic} falls under targeted priority sectors.",
                is_hard_criterion=False,
            ))
            earned_weights += weight_nic
        else:
            criteria.append(CriterionResult(
                name="Industrial Sector / NIC Match",
                status="WARNING",
                score_weight=weight_nic,
                earned_score=3.0,  # Partial credit
                required_val=", ".join(rule.allowed_sectors_nic),
                actual_val=actual_nic or "Unspecified",
                explanation=f"Scheme prioritizes sunrise sectors ({', '.join(rule.allowed_sectors_nic)}).",
                is_hard_criterion=False,
            ))
            earned_weights += 3.0
    else:
        criteria.append(CriterionResult(
            name="Industrial Sector / NIC Match",
            status="PASS",
            score_weight=weight_nic,
            earned_score=weight_nic,
            required_val="All Manufacturing & Service",
            actual_val=actual_nic or "All Sectors",
            explanation="No sectoral restrictions.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_nic

    # 7. Udyam Registration (Weight: 10)
    weight_udyam = 10.0
    total_weights += weight_udyam
    has_udyam = bool(business.udyam_number and len(business.udyam_number.strip()) > 0)
    if rule.requires_udyam:
        if has_udyam:
            criteria.append(CriterionResult(
                name="Udyam Registration Status",
                status="PASS",
                score_weight=weight_udyam,
                earned_score=weight_udyam,
                required_val="Mandatory Udyam Number",
                actual_val=business.udyam_number or "Present",
                explanation=f"Valid Udyam Registration ({business.udyam_number}) recorded.",
                is_hard_criterion=True,
            ))
            earned_weights += weight_udyam
        else:
            criteria.append(CriterionResult(
                name="Udyam Registration Status",
                status="FAIL",
                score_weight=weight_udyam,
                earned_score=0.0,
                required_val="Mandatory Udyam Number",
                actual_val="Missing",
                explanation="Scheme requires active Udyam Registration Number.",
                is_hard_criterion=True,
            ))
            hard_criterion_failed = True
    else:
        criteria.append(CriterionResult(
            name="Udyam Registration Status",
            status="NOT_APPLICABLE",
            score_weight=weight_udyam,
            earned_score=weight_udyam,
            required_val="Optional",
            actual_val=business.udyam_number or "Not registered",
            explanation="Udyam registration not strictly required.",
            is_hard_criterion=False,
        ))
        earned_weights += weight_udyam

    # Calculate overall match score (0–100%)
    raw_match_score = (earned_weights / total_weights) * 100.0 if total_weights > 0 else 100.0
    match_score = round(raw_match_score, 1)

    # Eligible only if no hard criteria failed and score >= min_score_threshold
    is_eligible = (not hard_criterion_failed) and (match_score >= rule.min_score_threshold)

    # Separate matching vs unmet criteria
    matching_criteria = [c.name for c in criteria if c.status in ("PASS", "NOT_APPLICABLE")]
    unmet_criteria = [c.name for c in criteria if c.status in ("FAIL", "WARNING")]

    # Actionable recommendations
    recommendations = []
    if rule.requires_udyam and not has_udyam:
        recommendations.append("Apply for free instant Udyam Registration at udyamregistration.gov.in to qualify.")
    if rule.allowed_pollution_categories and actual_pollution not in rule.allowed_pollution_categories:
        recommendations.append(f"Requires CPCB {', '.join(rule.allowed_pollution_categories)} categorization.")
    if inv_pass is False and rule.max_investment:
        recommendations.append(f"Consider filing under smaller unit branch or Phase-1 investment within ₹{rule.max_investment:,.0f}.")
    if not recommendations:
        recommendations.append("Full eligibility confirmed. Proceed to generate proposal & document checklist.")

    # Estimated subsidy calculation
    estimated_subsidy: Optional[float] = None
    if scheme.subsidy_percentage and actual_inv > 0:
        calculated = (scheme.subsidy_percentage / 100.0) * actual_inv
        if scheme.max_subsidy_amount:
            estimated_subsidy = min(calculated, scheme.max_subsidy_amount)
        else:
            estimated_subsidy = calculated
    elif scheme.max_subsidy_amount:
        estimated_subsidy = scheme.max_subsidy_amount

    return {
        "scheme_id": scheme.id,
        "scheme_code": scheme.code,
        "scheme_name": scheme.name,
        "short_name": scheme.short_name,
        "ministry": scheme.ministry,
        "nodal_agency": scheme.nodal_agency,
        "scheme_type": scheme.scheme_type.value,
        "level": scheme.level.value,
        "match_score": match_score,
        "is_eligible": is_eligible,
        "max_subsidy_amount": scheme.max_subsidy_amount,
        "subsidy_percentage": scheme.subsidy_percentage,
        "interest_subsidy_rate": scheme.interest_subsidy_rate,
        "estimated_subsidy_amount": round(estimated_subsidy, 2) if estimated_subsidy else None,
        "criteria_breakdown": [c.to_dict() for c in criteria],
        "matching_criteria": matching_criteria,
        "unmet_criteria": unmet_criteria,
        "recommendations": recommendations,
        "official_portal_url": scheme.official_portal_url,
        "tags": scheme.tags,
        "required_document_codes": scheme.required_document_codes,
        "guidance_steps": scheme.guidance_steps,
    }


# ---------------------------------------------------------------------------
# Document Gap Analysis (Fragment 110)
# ---------------------------------------------------------------------------

DOC_TYPE_ALIASES: Dict[str, str] = {
    "UDYAM_CERTIFICATE": "UDYAM_REGISTRATION",
    "PROJECT_REPORT": "PROJECT_REPORT_DPR",
    "SITE_PLAN": "SITE_PLAN_LAYOUT",
    "POLLUTION_NOC": "ENVIRONMENTAL_MANAGEMENT_PLAN",
    "LAND_LEASE": "LAND_DEED_OR_LEASE",
}


async def analyze_scheme_document_gaps(
    db: AsyncSession,
    scheme: GovernmentScheme,
    business_id: str,
) -> Dict[str, Any]:
    """
    Cross-references a scheme's required documents against the business's Document Vault.
    Returns:
    - total_required: int
    - total_available: int
    - readiness_percentage: float
    - documents: List of required document items with upload status
    """
    stmt = select(Document).where(Document.business_id == business_id)
    result = await db.execute(stmt)
    business_docs = result.scalars().all()

    # Map by doc type string
    available_doc_types = {d.document_type.value: d for d in business_docs}

    doc_checklist = []
    available_count = 0

    for code in scheme.required_document_codes:
        canonical_code = DOC_TYPE_ALIASES.get(code, code)
        doc_entry = available_doc_types.get(code) or available_doc_types.get(canonical_code)
        is_available = doc_entry is not None
        if is_available:
            available_count += 1

        is_verified = (
            doc_entry.verification_status.value == "VERIFIED"
            if (doc_entry and hasattr(doc_entry.verification_status, "value"))
            else False
        )

        doc_checklist.append({
            "code": code,
            "title": code.replace("_", " ").title(),
            "is_available": is_available,
            "document_id": doc_entry.id if doc_entry else None,
            "file_name": doc_entry.file_name if doc_entry else None,
            "verification_status": (
                doc_entry.verification_status.value
                if (doc_entry and hasattr(doc_entry.verification_status, "value"))
                else None
            ),
            "is_verified": is_verified,
        })

    total_req = len(scheme.required_document_codes)
    readiness_pct = round((available_count / total_req * 100.0), 1) if total_req > 0 else 100.0

    return {
        "scheme_id": scheme.id,
        "scheme_code": scheme.code,
        "total_required": total_req,
        "total_available": available_count,
        "missing_count": total_req - available_count,
        "readiness_percentage": readiness_pct,
        "documents": doc_checklist,
    }


# ---------------------------------------------------------------------------
# Business Scheme Recommendation Engine (Fragment 106 & 107)
# ---------------------------------------------------------------------------

async def get_recommended_schemes_for_business(
    db: AsyncSession,
    business_id: str,
    scheme_type_filter: Optional[str] = None,
    min_score: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Evaluates all active government schemes against the business and returns
    ranked list ordered by is_eligible (desc), match_score (desc), and max_subsidy (desc).
    """
    stmt_biz = (
        select(Business)
        .options(selectinload(Business.profile))
        .where(Business.id == business_id)
    )
    res_biz = await db.execute(stmt_biz)
    business = res_biz.scalar_one_or_none()
    if not business:
        raise ValueError(f"Business with ID {business_id} not found.")

    profile = business.profile

    # Fetch all active schemes with their rules
    stmt_schemes = (
        select(GovernmentScheme)
        .options(selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.is_active == True)
    )
    if scheme_type_filter:
        stmt_schemes = stmt_schemes.where(GovernmentScheme.scheme_type == scheme_type_filter)

    res_schemes = await db.execute(stmt_schemes)
    schemes = res_schemes.scalars().all()

    evaluated_schemes = []
    for s in schemes:
        evaluation = evaluate_scheme_eligibility(s, business, profile)
        if evaluation["match_score"] >= min_score:
            evaluated_schemes.append(evaluation)

    # Sort: Eligible first, then highest match score, then highest subsidy
    evaluated_schemes.sort(
        key=lambda x: (
            1 if x["is_eligible"] else 0,
            x["match_score"],
            x["max_subsidy_amount"] or 0.0,
        ),
        reverse=True,
    )

    return evaluated_schemes


# ---------------------------------------------------------------------------
# Scheme Application & Bookmark Management (Fragment 111)
# ---------------------------------------------------------------------------

async def bookmark_or_apply_scheme(
    db: AsyncSession,
    business_id: str,
    scheme_id: str,
    status: SchemeApplicationStatus = SchemeApplicationStatus.BOOKMARKED,
    notes: Optional[str] = None,
    application_reference_number: Optional[str] = None,
) -> SchemeApplication:
    """
    Bookmarks or tracks a scheme application for an enterprise.
    """
    # Verify business
    stmt_biz = select(Business).options(selectinload(Business.profile)).where(Business.id == business_id)
    res_biz = await db.execute(stmt_biz)
    business = res_biz.scalar_one_or_none()
    if not business:
        raise ValueError("Business not found.")

    # Verify scheme
    stmt_scheme = (
        select(GovernmentScheme)
        .options(selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.id == scheme_id)
    )
    res_scheme = await db.execute(stmt_scheme)
    scheme = res_scheme.scalar_one_or_none()
    if not scheme:
        raise ValueError("Scheme not found.")

    # Check existing application
    stmt_app = select(SchemeApplication).where(
        SchemeApplication.business_id == business_id,
        SchemeApplication.scheme_id == scheme_id,
    )
    res_app = await db.execute(stmt_app)
    existing_app = res_app.scalar_one_or_none()

    # Calculate match score
    evaluation = evaluate_scheme_eligibility(scheme, business, business.profile)

    if existing_app:
        existing_app.status = status
        existing_app.match_score = evaluation["match_score"]
        if notes:
            existing_app.notes = notes
        if application_reference_number:
            existing_app.application_reference_number = application_reference_number
        if status == SchemeApplicationStatus.APPLIED and not existing_app.applied_date:
            existing_app.applied_date = date.today()
        await db.commit()
        await db.refresh(existing_app)
        return existing_app

    app_record = SchemeApplication(
        id=generate_uuid(),
        business_id=business_id,
        scheme_id=scheme_id,
        status=status,
        match_score=evaluation["match_score"],
        applied_date=date.today() if status == SchemeApplicationStatus.APPLIED else None,
        application_reference_number=application_reference_number,
        notes=notes,
        missing_documents=evaluation["unmet_criteria"],
    )
    db.add(app_record)
    await db.commit()
    await db.refresh(app_record)
    return app_record


async def get_business_scheme_applications(
    db: AsyncSession,
    business_id: str,
) -> List[SchemeApplication]:
    """List all scheme bookmarks and applications for a business."""
    stmt = (
        select(SchemeApplication)
        .options(selectinload(SchemeApplication.scheme))
        .where(SchemeApplication.business_id == business_id)
        .order_by(SchemeApplication.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
