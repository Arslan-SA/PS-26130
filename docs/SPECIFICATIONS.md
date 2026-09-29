# UdyamSetu AI — Functional Specifications & System Requirements
**SIH26130: Industrial Facilitation & Compliance Platform**

## 1. Functional Scope

### 1.1 Actor Roles & Permissions (RBAC)
1. **INDUSTRY_USER**:
   - Register and manage legal entity and manufacturing/service business profiles.
   - Run AI Approval Navigator to discover all statutory clearances.
   - View visual Approval Dependency Graph with critical path analysis.
   - Upload KYC, land, environmental, and factory safety documents.
   - Run OCR Document Intelligence to inspect extracted fields and validation discrepancies.
   - Create, submit, track, and resubmit statutory applications.
   - Receive proactive Next-Action recommendations.
   - Monitor statutory compliance deadlines, recurring renewals, and statutory filings.
   - Discover and assess eligibility for state/central government incentives and subsidies.
   - Raise and track grievances against delays or unfair rejections.
   - Interact with the Grounded AI Government Assistant.

2. **DEPARTMENT_OFFICER**:
   - Review incoming applications partitioned by department (e.g., Pollution Control Board, Fire Dept, Labor Dept).
   - Scrutinize uploaded documents and verification flags.
   - Issue structured deficiency notes (queries) with document-level precision.
   - Schedule site inspections or assign inspectors.
   - Make statutory determinations: Approve, Reject, or Query.

3. **INSPECTOR**:
   - View assigned physical site inspections with scheduled dates and enterprise locations.
   - Submit geolocated inspection reports with checklists and photo evidence attachments.
   - Mark inspection recommendations (Satisfactory / Non-Compliant / Remediation Required).

4. **ADMIN**:
   - Maintain department master catalog, approval rules, and statutory fee tables.
   - Manage government scheme eligibility criteria.
   - View macro analytics: average processing SLA, pendency hotspots, departmental query rates.
   - Audit append-only system activity logs.

---

## 2. Core Industrial Approvals Catalog & Dependencies (Illustrative Benchmark)

| Approval Code | Clearance Name | Issuing Department | Prerequisite Approvals |
|---|---|---|---|
| `LAND_ALLOC` | Industrial Land Allotment / Possession | State Industrial Development Corp (SIDC) | None |
| `CTE_PCB` | Consent to Establish (CTE) | State Pollution Control Board (SPCB) | `LAND_ALLOC` |
| `FACTORY_PLAN`| Factory Building Plan Approval | Directorate of Industrial Safety & Health (DISH) | `LAND_ALLOC` |
| `FIRE_PROV` | Provisional Fire Safety NOC | State Fire & Emergency Services | `FACTORY_PLAN` |
| `POWER_CONN` | HT/LT Industrial Power Sanction | State Electricity Distribution Co | `CTE_PCB`, `FIRE_PROV` |
| `CTO_PCB` | Consent to Operate (CTO) | State Pollution Control Board (SPCB) | `CTE_PCB`, `POWER_CONN` |
| `FACTORY_LIC` | Factory License | Directorate of Industrial Safety & Health (DISH) | `CTO_PCB`, `FIRE_PROV` |
| `BOILER_REG` | Boiler Installation & Registration | State Inspectorate of Boilers | `FACTORY_LIC` (if steam/boilers used) |

---

## 3. Data Integrity & System Guardrails

1. **Deterministic Rule Engine vs Generative AI**:
   - Approval requirements are strictly evaluated via codified domain rules matching Industry Sector (e.g., Chemical, Textile, Food Processing), Pollution Category (Red, Orange, Green, White), Capital Investment bracket (Micro, Small, Medium, Large), and Location (Notified Industrial Area vs Eco-sensitive Zone).
   - LLMs explain and summarize results; they do not dictate statutory prerequisites.

2. **Validation Matrix for Documents**:
   - Verification of Document Type (Certificate of Incorporation, Land Deed, Project Report, Site Plan, Emissions Audit).
   - Expiry check: Document expiration date must be greater than current timestamp.
   - Entity Match: Extracted Legal Name, PAN, and GSTIN must match registered Business Profile data.
