# UdyamSetu AI — Architecture Blueprint
**Intelligent Industrial Approval & Compliance Platform (SIH26130)**

## 1. System Overview & Philosophy

UdyamSetu AI addresses the friction faced by enterprises and MSMEs when navigating India's industrial regulatory landscape. Rather than being merely a transactional form-submission portal, UdyamSetu AI acts as an **intelligent guidance and orchestration layer**.

### Core Philosophy
1. **Deterministic Rules Over Hallucination**: Legally binding determinations (approvals needed, statutory fees, prerequisite orders, compliance deadlines) are governed by a deterministic rule engine. LLMs are used for summarization, contextual guidance, deficiency rephrasing, and natural language explanation.
2. **Proactive Next-Action Recommendation**: Every stage of an enterprise's lifecycle provides a single, unambiguous "Next Best Action" (e.g., "Submit Fire NOC application before approaching State Pollution Board").
3. **Document Intelligence With Human-in-the-Loop**: Automated OCR extraction, expiry verification, and PAN/GSTIN/Entity name consistency checking serve as advisory checks; final scrutiny remains with human officers and industry applicants.
4. **Modular Monolith**: Code is cleanly partitioned into domain modules (auth, businesses, approvals, applications, documents, compliance, schemes, inspections, grievances, analytics, ai) within a unified codebase for optimal hackathon velocity, zero microservice network latency, and clean future microservice extraction paths.

---

## 2. Monorepo Architecture

```
PS-26130/
├── frontend/                 # Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide icons
│   ├── src/
│   │   ├── app/              # Routes (landing, auth, dashboard, approvals, documents, etc.)
│   │   ├── components/       # UI building blocks (cards, tables, modals, graphs)
│   │   ├── lib/              # API clients, auth helpers, types
│   │   └── hooks/            # Custom React hooks
├── backend/                  # FastAPI 0.110+ async application
│   ├── app/
│   │   ├── api/              # API routers partitioned by version & domain
│   │   ├── core/             # Configuration, database session, security, exceptions, logging
│   │   ├── models/           # SQLAlchemy ORM models (UUID PKs, audit mixins)
│   │   ├── schemas/          # Pydantic v2 validation & response contracts
│   │   ├── services/         # Domain business logic & state machines
│   │   ├── rules/            # Deterministic rule evaluation engines
│   │   ├── ocr/              # Document text extraction & pattern matching
│   │   ├── ai/               # RAG, LLM integrations, embeddings, prompt management
│   │   └── seed/             # Curated demo data generators
│   ├── alembic/              # Database migration version scripts
│   └── tests/                # Pytest integration & unit test suite
├── docs/                     # Specifications, architecture, progress tracker
├── docker/                   # Dockerfiles for multi-stage production builds
└── docker-compose.yml        # Multi-container orchestration (App, DB, Vector, Redis)
```

---

## 3. Subsystem Domain Contracts

| Domain | Key Entity / Responsibility | Primary Invariant / Rule |
|---|---|---|
| **Auth & RBAC** | `User`, `Role` (Industry, Officer, Inspector, Admin) | JWT bearer auth; officers strictly scoped to department |
| **Business Profile** | `Business`, `BusinessProfile` | Drives all deterministic rule matching (Sector, State, Investment, Scale) |
| **Approval Engine** | `Approval`, `ApprovalRequirement`, `ApprovalDependency` | Directed Acyclic Graph (DAG) for prerequisite ordering |
| **Document Pipeline** | `Document`, `DocumentValidation` | Pre-submission verification (PAN/GST/Identity matches, expiry check) |
| **Application Lifecycle**| `Application`, `ApplicationStatusHistory` | Append-only status audit log; strict state transition guardrails |
| **Compliance Management**| `ComplianceRequirement`, `ComplianceRecord` | Scheduled recurrence; SLA risk scoring and early warning alerts |
| **Government Schemes**| `GovernmentScheme`, `SchemeEligibilityRule` | Matching algorithm with explainable criteria breakdowns |
| **Inspections** | `Inspection` | Assigned field officer visit logs, checklist scores, geolocated reports |
| **Grievance Redressal** | `Grievance` | Time-bound escalations with SLA tracking |
| **AI / RAG** | `KnowledgeDocument`, `AIConversation` | Grounded search over verified regulatory guidelines only |

---

## 4. Technology Selection Matrix

- **Backend**: Python 3.11+, FastAPI (high performance async REST, OpenAPI self-documentation, Pydantic v2 data validation).
- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS (enterprise government styling with clear visual hierarchy, accessible contrast, and zero clutter).
- **Persistence**: PostgreSQL 15+ with `pgvector` extension for semantic vector similarity; SQLite+aiosqlite seamless fallback for local zero-dependency testing.
- **Cache & Task Queue**: Redis for fast session invalidation, rate limiting, and background workers.
- **AI & Grounding**: LLM provider interface (Google Gemini / OpenAI compatible) with local cosine vector retrieval over indexed industrial policies.
