"""
Statutory Approval Checklist and Document Prerequisite Catalog (Fragment 48).
Provides standardized lists of statutory forms, required engineering documents,
prior clearances, and on-site inspection parameters per clearance code.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ChecklistItem:
    """Individual statutory requirement or document checklist entry."""
    item_id: str
    title: str
    category: str  # "FORM" | "DOCUMENT" | "PREREQUISITE" | "INSPECTION"
    description: str
    is_mandatory: bool
    template_url: Optional[str] = None


@dataclass(frozen=True)
class ApprovalChecklist:
    """Complete statutory dossier checklist for a clearance code."""
    approval_code: str
    approval_title: str
    issuing_authority: str
    statutory_act: str
    items: List[ChecklistItem]


STATUTORY_CHECKLISTS: Dict[str, ApprovalChecklist] = {
    "CTE_PCB": ApprovalChecklist(
        approval_code="CTE_PCB",
        approval_title="Consent to Establish (CTE) under Water & Air Acts",
        issuing_authority="State Pollution Control Board",
        statutory_act="Water Act 1974 & Air Act 1981",
        items=[
            ChecklistItem(
                item_id="CTE_F1",
                title="Form I & Form II Application",
                category="FORM",
                description="Statutory combined consent application under Section 25 of Water Act and Section 21 of Air Act.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_D1",
                title="Land Possession / Registered Lease Deed",
                category="DOCUMENT",
                description="Proof of clear land title, registered lease, or industrial development corporation (MIDC/GIDC) allotment letter.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_D2",
                title="Detailed Project Report (DPR) & Capital Investment Certificate",
                category="DOCUMENT",
                description="Chartered Accountant certified capital investment schedule covering land, civil structures, and plant & machinery.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_D3",
                title="Manufacturing Process Flowchart & Material Balance",
                category="DOCUMENT",
                description="Comprehensive schematic illustrating raw material inputs, chemical reactions, intermediate products, and final outputs.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_D4",
                title="Effluent Treatment Plant (ETP) / STP Engineering Scheme",
                category="DOCUMENT",
                description="Detailed hydraulic flow design, sizing, chemical dosing specs, and zero liquid discharge (ZLD) feasibility.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_D5",
                title="Air Pollution Control Devices (APCD) Schematic",
                category="DOCUMENT",
                description="Bag filters, wet scrubbers, cyclone separators, and chimney/stack height calculation with dispersion modeling.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_P1",
                title="Local Authority Land Use / Zoning NOC",
                category="PREREQUISITE",
                description="Confirmation that industrial operations are permitted within the designated master plan zone.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTE_I1",
                title="Baseline Pre-Construction Site Inspection",
                category="INSPECTION",
                description="Verification that zero civil construction or machinery installation has commenced prior to CTE grant.",
                is_mandatory=True,
            ),
        ],
    ),
    "CTO_PCB": ApprovalChecklist(
        approval_code="CTO_PCB",
        approval_title="Consent to Operate (CTO) under Water & Air Acts",
        issuing_authority="State Pollution Control Board",
        statutory_act="Water Act 1974 & Air Act 1981",
        items=[
            ChecklistItem(
                item_id="CTO_F1",
                title="Combined Consent to Operate Application",
                category="FORM",
                description="Statutory operational consent application with production capacity specifications.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTO_D1",
                title="Valid Consent to Establish (CTE) Copy",
                category="DOCUMENT",
                description="Copy of prior CTE order with point-wise compliance report against all stipulated environmental conditions.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTO_D2",
                title="ETP & APCD Installation As-Built Drawings & Photographs",
                category="DOCUMENT",
                description="Geo-tagged photographs and commissioning certificates of pollution control equipment.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTO_D3",
                title="Continuous Emission & Effluent Monitoring System (OCEMS) Link",
                category="DOCUMENT",
                description="Proof of live telemetry integration connecting stack/discharge sensors to CPCB/SPCB monitoring servers.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTO_P1",
                title="Valid CTE in Hand",
                category="PREREQUISITE",
                description="CTO cannot be applied without an existing, unexpired Consent to Establish.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CTO_I1",
                title="Pre-Commissioning Verification & Effluent Sampling Inspection",
                category="INSPECTION",
                description="State board engineer physical verification of pollution systems, boundary green belt, and trial run parameters.",
                is_mandatory=True,
            ),
        ],
    ),
    "FIRE_NOC": ApprovalChecklist(
        approval_code="FIRE_NOC",
        approval_title="Provisional Fire Safety Approval & Fire NOC",
        issuing_authority="State Fire and Emergency Services",
        statutory_act="State Fire Prevention and Life Safety Measures Act",
        items=[
            ChecklistItem(
                item_id="FIRE_F1",
                title="Fire Clearance Application Form A",
                category="FORM",
                description="Application for provisional building plan approval for fire protection and life safety.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FIRE_D1",
                title="Architectural Site Layout & Floor Plans with Fire Infrastructure",
                category="DOCUMENT",
                description="AutoCAD / PDF layout certified by licensed architect showing fire exits, refuge areas, staircase widths, and hydrants.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FIRE_D2",
                title="Static Underground & Overhead Fire Water Tank Scheme",
                category="DOCUMENT",
                description="Dedicated water storage capacity calculation based on National Building Code (NBC) Part IV hazard classification.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FIRE_D3",
                title="Automatic Sprinkler & Heat/Smoke Detection Layout",
                category="DOCUMENT",
                description="Engineering drawings of optical smoke detectors, manual call points (MCP), and fire alarm control panel (FACP).",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FIRE_I1",
                title="On-Site Fire Safety Infrastructure Drill & Flow Test",
                category="INSPECTION",
                description="Divisional fire officer physical test of pump pressure, hydrant discharge, and secondary generator switchover.",
                is_mandatory=True,
            ),
        ],
    ),
    "FACTORY_LIC": ApprovalChecklist(
        approval_code="FACTORY_LIC",
        approval_title="Factory License & Factory Plan Approval",
        issuing_authority="Directorate of Industrial Safety and Health (DISH)",
        statutory_act="Factories Act, 1948",
        items=[
            ChecklistItem(
                item_id="FACT_F1",
                title="Form No. 1 - Factory Plan Approval Application",
                category="FORM",
                description="Detailed factory layout approval application under Section 6 of Factories Act 1948.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_F2",
                title="Form No. 2 - Factory Registration & License Grant",
                category="FORM",
                description="Statutory license application specifying maximum daily worker capacity and installed power horsepower.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_D1",
                title="Structural Stability Certificate by Chartered Engineer",
                category="DOCUMENT",
                description="Certified structural stability report confirming shed and foundation load-bearing parameters under live operations.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_D2",
                title="Machinery Layout & Electrical Safety Single Line Diagram (SLD)",
                category="DOCUMENT",
                description="Clear minimum distance between machines, emergency stop actuators, and electrical earthing layout.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_D3",
                title="Worker Welfare Facilities Plan (Ventilation, Toilets, First Aid)",
                category="DOCUMENT",
                description="Compliance with Chapter III & IV: drinking water points, adequate ventilation, canteen facilities, and crèche provisions.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_P1",
                title="Prior Fire Safety NOC",
                category="PREREQUISITE",
                description="DISH requires a valid Fire Safety NOC before issuing factory license.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="FACT_I1",
                title="Joint Safety & Health Inspectorate Audit",
                category="INSPECTION",
                description="Physical audit of moving machine guards, ventilation rates, noise levels, and statutory registers.",
                is_mandatory=True,
            ),
        ],
    ),
    "POWER_HT": ApprovalChecklist(
        approval_code="POWER_HT",
        approval_title="High Tension (HT) Industrial Power Sanction & CEI Inspection",
        issuing_authority="Power Distribution Company & Chief Electrical Inspectorate",
        statutory_act="Electricity Act, 2003",
        items=[
            ChecklistItem(
                item_id="PWR_F1",
                title="A-1 High Tension Load Application",
                category="FORM",
                description="Official requisition for industrial contract demand exceeding 50 kVA/kW.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="PWR_D1",
                title="Substation Layout & Single Line Diagram (SLD)",
                category="DOCUMENT",
                description="Certified SLD of 11kV/33kV indoor/outdoor substation, vacuum circuit breakers (VCB), and transformer ratings.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="PWR_D2",
                title="Earthing Pit Test Certificates",
                category="DOCUMENT",
                description="Resistance measurement records by licensed electrical contractor (<= 1 ohm for substation neutral).",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="PWR_I1",
                title="Chief Electrical Inspectorate (CEI) Statutory Energization Inspection",
                category="INSPECTION",
                description="Mandatory CEI testing of relay settings, insulation resistance, and clearances prior to charging power line.",
                is_mandatory=True,
            ),
        ],
    ),
    "CGWA_GW": ApprovalChecklist(
        approval_code="CGWA_GW",
        approval_title="Ground Water Abstraction & Tube-well NOC",
        issuing_authority="Central Ground Water Authority",
        statutory_act="Environment (Protection) Act, 1986",
        items=[
            ChecklistItem(
                item_id="CGWA_F1",
                title="Form for Industrial Ground Water Abstraction",
                category="FORM",
                description="Online application submitted through Bharat-NOC portal with geocoded bore-well coordinates.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CGWA_D1",
                title="Comprehensive Hydrogeological Assessment Report",
                category="DOCUMENT",
                description="Study conducted by accredited hydrogeologist assessing aquifer status, cone of depression, and recharge balance.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CGWA_D2",
                title="Rainwater Harvesting & Artificial Recharge Proposal",
                category="DOCUMENT",
                description="Recharge capacity design balancing minimum 100% of abstraction quantity via rooftop runoff percolation pits.",
                is_mandatory=True,
            ),
            ChecklistItem(
                item_id="CGWA_D3",
                title="Digital Water Flow Meter Installation Scheme",
                category="DOCUMENT",
                description="Specifications for ultrasonic / electromagnetic water flow meters with telemetry loggers on all extraction points.",
                is_mandatory=True,
            ),
        ],
    ),
}


def get_approval_checklist(approval_code: str) -> Optional[ApprovalChecklist]:
    """Retrieve the statutory checklist for an approval code."""
    return STATUTORY_CHECKLISTS.get(approval_code)
