"""
Government Schemes, Subsidies & AI/Rule Matching Engine — Comprehensive Test Suite (Phase 8, Fragment 112).

Tests:
1. Scheme database seeding & catalog integrity (Fragment 105)
2. Scheme domain model, eligibility rules & JSON structures (Fragments 103–104)
3. Micro-enterprise eligibility evaluation (PMEGP, Mudra, CGTMSE, ZED)
4. Large-enterprise eligibility evaluation (PLI pass, PMEGP fail)
5. Strict Udyam registration requirement enforcement
6. CPCB environmental / pollution category matching
7. State jurisdiction rule matching (Maharashtra State policy)
8. Document Vault gap analysis & readiness score (Fragment 110)
9. Ranked business recommendations engine (Fragment 106)
10. Scheme application tracking & milestone lifecycle (Fragment 111)
11. Scheme catalog API with search and type filters (Fragment 107)
12. Scheme detail API
13. Business scheme recommendations API
14. Scheme evaluation & document gap analysis API
15. Scheme application tracking API endpoints
"""

import asyncio
import os
import uuid
import pytest
from datetime import date

from httpx import AsyncClient, ASGITransport

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.base import generate_uuid
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.document import Document, DocumentType, DocumentVerificationStatus
from app.models.scheme import (
    ApplicationMode,
    GovernmentScheme,
    SchemeApplication,
    SchemeApplicationStatus,
    SchemeEligibilityRule,
    SchemeLevel,
    SchemeType,
)
from app.models.user import User, UserRole
from app.services import scheme_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def seed_test_data(db_session):
    """Seed test users and businesses for test scenarios."""
    # 1. Micro Entrepreneur
    user_micro = User(
        id=generate_uuid(),
        email=f"micro_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Micro Entrepreneur",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.INDUSTRY_USER,
        is_verified=True,
    )
    db_session.add(user_micro)

    # 2. Large Industrialist
    user_large = User(
        id=generate_uuid(),
        email=f"large_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Large Enterprise CEO",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.INDUSTRY_USER,
        is_verified=True,
    )
    db_session.add(user_large)

    # 3. Admin User
    admin_user = User(
        id=generate_uuid(),
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Admin Officer",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.ADMIN,
        is_verified=True,
    )
    db_session.add(admin_user)

    await db_session.flush()

    # Micro Business: Agro & Food Processing, Micro scale, Green category, Maharashtra
    biz_micro = Business(
        id=generate_uuid(),
        user_id=user_micro.id,
        legal_name="Sahyadri Organic Agro Foods Pvt Ltd",
        entity_type=EntityType.PRIVATE_LIMITED,
        msme_category=MSMECategory.MICRO,
        pan="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
        udyam_number="UDYAM-MH-12-0099887",
        is_verified=True,
    )
    db_session.add(biz_micro)
    await db_session.flush()

    prof_micro = BusinessProfile(
        business_id=biz_micro.id,
        nic_code="1079",  # Food products
        manufacturing_activity="Manufacture of organic dehydrated food products",
        industry_scale=IndustryScale.SMALL_SCALE,
        pollution_category=PollutionCategory.GREEN,
        state="Maharashtra",
        district="Pune",
        city="Pune",
        pincode="411001",
        total_employees=12,
        plant_machinery_investment=2500000.0,  # ₹25 Lakhs
        annual_turnover=8000000.0,            # ₹80 Lakhs
        profile_completeness=100,
        is_profile_complete=True,
    )
    db_session.add(prof_micro)

    # Large Business: Heavy Auto & Electronic Components, Large scale, Orange category, Karnataka
    biz_large = Business(
        id=generate_uuid(),
        user_id=user_large.id,
        legal_name="Apex Precision Motors & Tech Ltd",
        entity_type=EntityType.PUBLIC_LIMITED,
        msme_category=MSMECategory.LARGE,
        pan="XYZAB5678C",
        gstin="29XYZAB5678C1Z2",
        udyam_number=None,  # No udyam
        is_verified=True,
    )
    db_session.add(biz_large)
    await db_session.flush()

    prof_large = BusinessProfile(
        business_id=biz_large.id,
        nic_code="2910",  # Motor vehicles
        manufacturing_activity="Advanced Electric Vehicle powertrain manufacturing",
        industry_scale=IndustryScale.LARGE_SCALE,
        pollution_category=PollutionCategory.ORANGE,
        state="Karnataka",
        district="Bengaluru",
        city="Bengaluru",
        pincode="560001",
        total_employees=350,
        plant_machinery_investment=600000000.0,  # ₹60 Crores
        annual_turnover=2800000000.0,            # ₹280 Crores
        profile_completeness=100,
        is_profile_complete=True,
    )
    db_session.add(prof_large)

    await db_session.commit()

    return {
        "user_micro": user_micro,
        "biz_micro": biz_micro,
        "prof_micro": prof_micro,
        "user_large": user_large,
        "biz_large": biz_large,
        "prof_large": prof_large,
        "admin_user": admin_user,
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_government_schemes_catalog(db_session):
    """Test Fragment 105: Verify seed data populates Central & State schemes."""
    count = await scheme_service.seed_government_schemes(db_session)
    assert count >= 8

    # Verify PMEGP exists
    pmegp = await db_session.get(GovernmentScheme, (await db_session.execute(
        scheme_service.select(GovernmentScheme).where(GovernmentScheme.code == "SCHEME_PMEGP")
    )).scalar_one().id)
    assert pmegp is not None
    assert pmegp.short_name == "PMEGP"
    assert pmegp.scheme_type == SchemeType.CAPITAL_SUBSIDY
    assert pmegp.level == SchemeLevel.CENTRAL
    assert pmegp.max_subsidy_amount == 1750000.0
    assert len(pmegp.guidance_steps) >= 4
    assert "PAN_CARD" in pmegp.required_document_codes

    # Verify rule relationship
    assert pmegp.rule is not None
    assert "MICRO" in pmegp.rule.allowed_msme_categories
    assert pmegp.rule.requires_udyam is True


@pytest.mark.asyncio
async def test_scheme_model_integrity_and_serialization(db_session):
    """Test Fragment 103 & 104: Domain models, attributes, to_dict."""
    scheme = GovernmentScheme(
        id=generate_uuid(),
        code="SCHEME_CUSTOM_TEST",
        name="Custom Test Industry Scheme",
        short_name="CTIS",
        ministry="Ministry of Testing",
        nodal_agency="Test Agency",
        scheme_type=SchemeType.INTEREST_SUBVENTION,
        level=SchemeLevel.STATE,
        state="Maharashtra",
        target_beneficiary="Test Units",
        benefit_description="3% interest subvention for 3 years",
        max_subsidy_amount=500000.0,
        subsidy_percentage=None,
        interest_subsidy_rate=3.0,
        official_portal_url="https://test.gov.in",
        application_mode=ApplicationMode.ONLINE,
        guidance_steps=[{"step": 1, "title": "Submit Form", "instruction": "Fill form online"}],
        required_document_codes=["PAN_CARD", "BANK_STATEMENT"],
        tags=["TEST", "INTEREST"],
    )
    db_session.add(scheme)
    await db_session.flush()

    rule = SchemeEligibilityRule(
        id=generate_uuid(),
        scheme_id=scheme.id,
        min_investment=100000.0,
        max_investment=10000000.0,
        allowed_msme_categories=["MICRO", "SMALL"],
        allowed_entity_types=["PRIVATE_LIMITED", "LLP"],
        allowed_sectors_nic=[],
        allowed_pollution_categories=["GREEN"],
        allowed_states=["Maharashtra"],
        requires_udyam=True,
    )
    scheme.rule = rule
    db_session.add(rule)
    await db_session.flush()

    serialized = scheme.to_dict()
    assert serialized["code"] == "SCHEME_CUSTOM_TEST"
    assert serialized["scheme_type"] == "INTEREST_SUBVENTION"
    assert serialized["level"] == "STATE"
    assert "rule" in serialized
    assert serialized["rule"]["min_investment"] == 100000.0
    await db_session.commit()


@pytest.mark.asyncio
async def test_micro_enterprise_eligibility_evaluation(db_session, seed_test_data):
    """Test Fragment 106: Micro enterprise evaluation against PMEGP and PLI."""
    await scheme_service.seed_government_schemes(db_session)

    biz_micro = seed_test_data["biz_micro"]
    prof_micro = seed_test_data["prof_micro"]

    # Fetch PMEGP
    res_pmegp = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_pmegp.scalar_one()

    eval_pmegp = scheme_service.evaluate_scheme_eligibility(pmegp, biz_micro, prof_micro)
    assert eval_pmegp["is_eligible"] is True
    assert eval_pmegp["match_score"] >= 80.0
    assert "MSME Classification" in eval_pmegp["matching_criteria"]
    assert "Udyam Registration Status" in eval_pmegp["matching_criteria"]
    assert eval_pmegp["estimated_subsidy_amount"] > 0

    # Fetch PLI (Medium/Large only, min investment 2.5 Cr)
    res_pli = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_PLI_MANUFACTURING")
    )
    pli = res_pli.scalar_one()

    eval_pli = scheme_service.evaluate_scheme_eligibility(pli, biz_micro, prof_micro)
    assert eval_pli["is_eligible"] is False
    assert "MSME Classification" in eval_pli["unmet_criteria"]


@pytest.mark.asyncio
async def test_large_enterprise_eligibility_evaluation(db_session, seed_test_data):
    """Test Fragment 106: Large enterprise satisfies PLI and fails PMEGP."""
    await scheme_service.seed_government_schemes(db_session)

    biz_large = seed_test_data["biz_large"]
    prof_large = seed_test_data["prof_large"]

    # Evaluate PLI
    res_pli = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_PLI_MANUFACTURING")
    )
    pli = res_pli.scalar_one()

    eval_pli = scheme_service.evaluate_scheme_eligibility(pli, biz_large, prof_large)
    assert eval_pli["is_eligible"] is True
    assert eval_pli["match_score"] >= 75.0

    # Evaluate PMEGP (Must fail because large scale and > 50 Lakhs)
    res_pmegp = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_pmegp.scalar_one()

    eval_pmegp = scheme_service.evaluate_scheme_eligibility(pmegp, biz_large, prof_large)
    assert eval_pmegp["is_eligible"] is False
    assert "MSME Classification" in eval_pmegp["unmet_criteria"]
    assert "Investment in Plant & Machinery" in eval_pmegp["unmet_criteria"]


@pytest.mark.asyncio
async def test_udyam_requirement_enforcement(db_session, seed_test_data):
    """Test Fragment 106: Unit missing Udyam fails hard criterion on Udyam-mandatory schemes."""
    await scheme_service.seed_government_schemes(db_session)

    biz_no_udyam = Business(
        id=generate_uuid(),
        user_id=seed_test_data["user_micro"].id,
        legal_name="Unregistered Craft Unit",
        entity_type=EntityType.PROPRIETORSHIP,
        msme_category=MSMECategory.MICRO,
        pan="BBBBB2222B",
        udyam_number=None,  # No udyam number
    )
    db_session.add(biz_no_udyam)
    await db_session.flush()

    prof = BusinessProfile(
        business_id=biz_no_udyam.id,
        plant_machinery_investment=500000.0,
        annual_turnover=1500000.0,
        pollution_category=PollutionCategory.GREEN,
    )
    db_session.add(prof)
    await db_session.commit()

    res_pmegp = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_pmegp.scalar_one()

    evaluation = scheme_service.evaluate_scheme_eligibility(pmegp, biz_no_udyam, prof)
    assert evaluation["is_eligible"] is False
    assert "Udyam Registration Status" in evaluation["unmet_criteria"]
    # Check recommendation advises Udyam registration
    assert any("udyamregistration.gov.in" in rec for rec in evaluation["recommendations"])


@pytest.mark.asyncio
async def test_pollution_category_matching(db_session, seed_test_data):
    """Test Fragment 106: Environmental pollution category filter matching."""
    await scheme_service.seed_government_schemes(db_session)

    # Red category polluting unit
    biz_chem = Business(
        id=generate_uuid(),
        user_id=seed_test_data["user_micro"].id,
        legal_name="Specialty Solvents Chemical Corp",
        entity_type=EntityType.PRIVATE_LIMITED,
        msme_category=MSMECategory.SMALL,
        pan="CHEMC1234D",
        udyam_number="UDYAM-MH-12-0055443",
    )
    db_session.add(biz_chem)
    await db_session.flush()

    prof_chem = BusinessProfile(
        business_id=biz_chem.id,
        plant_machinery_investment=20000000.0,  # 2 Cr
        annual_turnover=50000000.0,
        pollution_category=PollutionCategory.RED,  # RED category
        state="Maharashtra",
    )
    db_session.add(prof_chem)
    await db_session.commit()

    # 1. ZED scheme allows White/Green/Orange -> Must FAIL for RED
    res_zed = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_ZED_CERTIFICATION")
    )
    zed = res_zed.scalar_one()
    eval_zed = scheme_service.evaluate_scheme_eligibility(zed, biz_chem, prof_chem)
    assert eval_zed["is_eligible"] is False
    assert "CPCB Environmental Classification" in eval_zed["unmet_criteria"]

    # 2. Green Abatement subsidy explicitly targets Orange and Red -> Must PASS
    res_green = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_GREEN_EFFLUENT_SUBSIDY")
    )
    green = res_green.scalar_one()
    eval_green = scheme_service.evaluate_scheme_eligibility(green, biz_chem, prof_chem)
    assert eval_green["is_eligible"] is True
    assert "CPCB Environmental Classification" in eval_green["matching_criteria"]


@pytest.mark.asyncio
async def test_state_jurisdiction_matching(db_session, seed_test_data):
    """Test Fragment 106: State policy schemes match only units in that state."""
    await scheme_service.seed_government_schemes(db_session)

    res_maha = await db_session.execute(
        scheme_service.select(GovernmentScheme)
        .options(scheme_service.selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.code == "SCHEME_STATE_CAPITAL_SUBSIDY")
    )
    maha_scheme = res_maha.scalar_one()

    # Unit in Maharashtra (prof_micro) -> PASS
    eval_mh = scheme_service.evaluate_scheme_eligibility(
        maha_scheme, seed_test_data["biz_micro"], seed_test_data["prof_micro"]
    )
    assert eval_mh["is_eligible"] is True

    # Unit in Karnataka (prof_large) -> FAIL
    eval_ka = scheme_service.evaluate_scheme_eligibility(
        maha_scheme, seed_test_data["biz_large"], seed_test_data["prof_large"]
    )
    assert eval_ka["is_eligible"] is False


@pytest.mark.asyncio
async def test_document_gap_analysis(db_session, seed_test_data):
    """Test Fragment 110: Cross-referencing scheme required documents with Document Vault."""
    biz = seed_test_data["biz_micro"]

    # Add 2 documents to business vault (PAN_CARD, UDYAM_REGISTRATION)
    doc_pan = Document(
        id=generate_uuid(),
        business_id=biz.id,
        file_name="pan_card.pdf",
        storage_path="/storage/documents/pan_card.pdf",
        file_size_bytes=1048576,
        mime_type="application/pdf",
        sha256_checksum="a" * 64,
        document_type=DocumentType.PAN_CARD,
        verification_status=DocumentVerificationStatus.VERIFIED,
    )
    doc_udyam = Document(
        id=generate_uuid(),
        business_id=biz.id,
        file_name="udyam_cert.pdf",
        storage_path="/storage/documents/udyam_cert.pdf",
        file_size_bytes=524288,
        mime_type="application/pdf",
        sha256_checksum="b" * 64,
        document_type=DocumentType.UDYAM_REGISTRATION,
        verification_status=DocumentVerificationStatus.PENDING,
    )
    db_session.add(doc_pan)
    db_session.add(doc_udyam)
    await db_session.commit()

    # Test against PMEGP which requires 5 docs
    res_pmegp = await db_session.execute(
        scheme_service.select(GovernmentScheme).where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_pmegp.scalar_one()

    gap_report = await scheme_service.analyze_scheme_document_gaps(db_session, pmegp, biz.id)
    assert gap_report["total_required"] == 5
    assert gap_report["total_available"] == 2
    assert gap_report["missing_count"] == 3
    assert gap_report["readiness_percentage"] == 40.0

    # Check individual checklist items
    pan_item = next(d for d in gap_report["documents"] if d["code"] == "PAN_CARD")
    assert pan_item["is_available"] is True
    assert pan_item["is_verified"] is True

    report_item = next(d for d in gap_report["documents"] if d["code"] == "PROJECT_REPORT")
    assert report_item["is_available"] is False


@pytest.mark.asyncio
async def test_business_recommendations_ranking(db_session, seed_test_data):
    """Test Fragment 106 & 107: Multi-scheme evaluation and ranking."""
    await scheme_service.seed_government_schemes(db_session)
    biz = seed_test_data["biz_micro"]

    recommendations = await scheme_service.get_recommended_schemes_for_business(db_session, biz.id)
    assert len(recommendations) >= 5

    # Verify sorting: Eligible schemes first
    for i in range(len(recommendations) - 1):
        curr = recommendations[i]
        nxt = recommendations[i + 1]
        if curr["is_eligible"] == nxt["is_eligible"]:
            assert curr["match_score"] >= nxt["match_score"]
        else:
            assert curr["is_eligible"] is True and nxt["is_eligible"] is False


@pytest.mark.asyncio
async def test_scheme_application_lifecycle(db_session, seed_test_data):
    """Test Fragment 111: Application tracking milestone lifecycle."""
    await scheme_service.seed_government_schemes(db_session)
    biz = seed_test_data["biz_micro"]

    res_pmegp = await db_session.execute(
        scheme_service.select(GovernmentScheme).where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_pmegp.scalar_one()

    # 1. Bookmark
    app_record = await scheme_service.bookmark_or_apply_scheme(
        db=db_session,
        business_id=biz.id,
        scheme_id=pmegp.id,
        status=SchemeApplicationStatus.BOOKMARKED,
        notes="Evaluating for new organic processing line",
    )
    assert app_record.status == SchemeApplicationStatus.BOOKMARKED
    assert app_record.match_score >= 80.0

    # 2. Advance to APPLIED
    app_updated = await scheme_service.bookmark_or_apply_scheme(
        db=db_session,
        business_id=biz.id,
        scheme_id=pmegp.id,
        status=SchemeApplicationStatus.APPLIED,
        application_reference_number="KVIC/2026/PMEGP/44321",
    )
    assert app_updated.status == SchemeApplicationStatus.APPLIED
    assert app_updated.applied_date == date.today()
    assert app_updated.application_reference_number == "KVIC/2026/PMEGP/44321"

    # 3. Retrieve business applications
    all_apps = await scheme_service.get_business_scheme_applications(db_session, biz.id)
    assert len(all_apps) == 1
    assert all_apps[0].scheme.code == "SCHEME_PMEGP"


# ---------------------------------------------------------------------------
# API Endpoint Tests (Fragment 107)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_scheme_catalog(seed_test_data):
    """Test GET /api/v1/schemes/catalog with filters."""
    admin = seed_test_data["admin_user"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Generate token
        from app.core.security import create_access_token
        token = create_access_token({"sub": admin.id, "email": admin.email, "role": admin.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Seed schemes
        res_seed = await ac.post("/api/v1/schemes/admin/seed", headers=headers)
        assert res_seed.status_code == 200

        # 2. List all
        res_catalog = await ac.get("/api/v1/schemes/catalog", headers=headers)
        assert res_catalog.status_code == 200
        catalog = res_catalog.json()
        assert len(catalog) >= 8

        # 3. Filter by type
        res_filtered = await ac.get("/api/v1/schemes/catalog?scheme_type=CAPITAL_SUBSIDY", headers=headers)
        assert res_filtered.status_code == 200
        for item in res_filtered.json():
            assert item["scheme_type"] == "CAPITAL_SUBSIDY"

        # 4. Search query
        res_search = await ac.get("/api/v1/schemes/catalog?search=Mudra", headers=headers)
        assert res_search.status_code == 200
        assert len(res_search.json()) >= 1
        assert "Mudra" in res_search.json()[0]["name"] or "MUDRA" in res_search.json()[0]["short_name"]


@pytest.mark.asyncio
async def test_api_business_recommendations(seed_test_data):
    """Test GET /api/v1/schemes/recommendations/{business_id}."""
    user = seed_test_data["user_micro"]
    biz = seed_test_data["biz_micro"]

    from app.core.security import create_access_token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/schemes/recommendations/{biz.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["business_id"] == biz.id
        assert data["total_schemes_evaluated"] >= 8
        assert data["total_eligible_schemes"] >= 3
        assert data["total_subsidy_potential_inr"] > 0
        assert len(data["schemes"]) >= 8


@pytest.mark.asyncio
async def test_api_single_scheme_evaluate_and_gap(seed_test_data, db_session):
    """Test GET /api/v1/schemes/{scheme_id}/evaluate/{business_id}."""
    user = seed_test_data["user_micro"]
    biz = seed_test_data["biz_micro"]

    # Get PMEGP id
    res_p = await db_session.execute(
        scheme_service.select(GovernmentScheme).where(GovernmentScheme.code == "SCHEME_PMEGP")
    )
    pmegp = res_p.scalar_one()

    from app.core.security import create_access_token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/schemes/{pmegp.id}/evaluate/{biz.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["scheme_code"] == "SCHEME_PMEGP"
        assert data["is_eligible"] is True
        assert "document_readiness" in data
        assert data["document_readiness"]["total_required"] >= 4


@pytest.mark.asyncio
async def test_api_scheme_application_workflow(seed_test_data, db_session):
    """Test POST, GET, PATCH /api/v1/schemes/applications."""
    user = seed_test_data["user_micro"]
    biz = seed_test_data["biz_micro"]

    res_cgtmse = await db_session.execute(
        scheme_service.select(GovernmentScheme).where(GovernmentScheme.code == "SCHEME_CGTMSE")
    )
    cgtmse = res_cgtmse.scalar_one()

    from app.core.security import create_access_token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create tracking entry
        create_payload = {
            "business_id": biz.id,
            "scheme_id": cgtmse.id,
            "status": "PREPARING",
            "notes": "Bank loan application submitted to SBI SME Branch",
        }
        res_post = await ac.post("/api/v1/schemes/applications", json=create_payload, headers=headers)
        assert res_post.status_code == 200
        app_data = res_post.json()
        assert app_data["status"] == "PREPARING"
        app_id = app_data["id"]

        # 2. List applications
        res_get = await ac.get(f"/api/v1/schemes/applications/{biz.id}", headers=headers)
        assert res_get.status_code == 200
        apps_list = res_get.json()
        assert len(apps_list) >= 1

        # 3. Patch application milestone
        patch_payload = {
            "status": "SANCTIONED",
            "sanctioned_amount": 15000000.0,
            "application_reference_number": "CGTMSE/SBI/2026/9981",
        }
        res_patch = await ac.patch(f"/api/v1/schemes/applications/{app_id}", json=patch_payload, headers=headers)
        assert res_patch.status_code == 200
        updated = res_patch.json()
        assert updated["status"] == "SANCTIONED"
        assert updated["sanctioned_amount"] == 15000000.0
        assert updated["application_reference_number"] == "CGTMSE/SBI/2026/9981"
