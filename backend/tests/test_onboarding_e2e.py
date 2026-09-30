"""
End-to-End Test Suite for Industrial Onboarding, Multi-Role Governance, and Profile Validation (Fragment 40).
Tests complete user-to-enterprise lifecycles across Red, Green, and White industries.
"""

from datetime import date
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.business import EntityType, MSMECategory
from app.models.business_profile import PollutionCategory
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_users():
    """Create a suite of multi-role users for authorization testing."""
    async with AsyncSessionLocal() as session:
        industry_user = User(
            email="industrialist@bharatforge.example.com",
            hashed_password=get_password_hash("StrongPassword123!"),
            full_name="Vikram Kalyani",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        officer_user = User(
            email="officer.pcb@maharashtra.gov.in",
            hashed_password=get_password_hash("GovPassword123!"),
            full_name="Dr. S. K. Deshmukh",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="MPCB-REG-01",
            is_active=True,
            is_verified=True,
        )
        intruder_user = User(
            email="competitor@rivalcorp.example.com",
            hashed_password=get_password_hash("StrongPassword123!"),
            full_name="Rival Promoter",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add_all([industry_user, officer_user, intruder_user])
        await session.commit()
        await session.refresh(industry_user)
        await session.refresh(officer_user)
        await session.refresh(intruder_user)

        industry_token = create_access_token({"sub": industry_user.id, "role": industry_user.role.value})
        officer_token = create_access_token({"sub": officer_user.id, "role": officer_user.role.value})
        intruder_token = create_access_token({"sub": intruder_user.id, "role": intruder_user.role.value})

        return {
            "industry": (industry_token, industry_user.id),
            "officer": (officer_token, officer_user.id),
            "intruder": (intruder_token, intruder_user.id),
        }


@pytest.mark.asyncio
async def test_e2e_red_category_industrial_unit_onboarding(test_users):
    """
    Scenario 1: Full onboarding of a heavy chemical manufacturing unit (RED Category).
    Verifies automatic CPCB categorization, statutory validation, and recommendation steps.
    """
    token, _ = test_users["industry"]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        onboard_payload = {
            "business": {
                "legal_name": "Maharashtra Petrochemicals Private Limited",
                "trade_name": "MahaPetro",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "AABCM1234F",  # Company PAN with 'C'
                "gstin": "27AABCM1234F1Z1",  # 27 = Maharashtra
                "udyam_number": "UDYAM-MH-01-0099999",
                "cin": "U24100MH2021PTC365412",
                "msme_category": "MEDIUM",
                "incorporation_date": "2021-04-10",
                "website": "https://mahapetro.example.com",
            },
            "profile": {
                "nic_code": "20111",  # Basic chemical synthesis
                "manufacturing_activity": "Manufacture of basic organic chemicals and synthetic resins",
                "products_services": "Industrial solvents, polymer resins",
                "state": "Maharashtra",
                "district": "Raigad",
                "city": "Panvel",
                "pincode": "410206",
                "industrial_area": "Taloja MIDC Chemical Zone",
                "plot_number": "Plot C-48",
                "latitude": 19.05,
                "longitude": 73.12,
                "total_employees": 120,
                "plant_machinery_investment": 350000000.0,  # 35 Crore
                "land_area_sqm": 25000.0,
                "annual_turnover": 850000000.0,
                "power_requirement_kw": 1500.0,
                "water_requirement_kld": 250.0,
                "contact_person": "Vikram Kalyani",
                "contact_phone": "+919822001122",
                "contact_email": "regulatory@mahapetro.example.com",
            },
        }

        # 1. Submit Onboarding
        res = await ac.post(
            "/api/v1/business/onboard",
            json=onboard_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()
        biz_id = data["business"]["id"]

        # Verify CPCB classified as RED due to chemical sector
        assert data["business"]["profile"]["pollution_category"] == "RED"
        assert data["business"]["profile"]["profile_completeness"] >= 90
        assert data["business"]["profile"]["is_profile_complete"] is True

        # 2. Check Completeness Endpoint
        comp_res = await ac.get(
            f"/api/v1/business/{biz_id}/completeness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert comp_data["is_ready_for_approvals"] is True
        assert comp_data["total_score"] >= 90


@pytest.mark.asyncio
async def test_e2e_white_category_it_services_onboarding(test_users):
    """
    Scenario 2: Onboarding of an IT & Software development enterprise (WHITE Category).
    Exempt from pollution consent (CTE/CTO), fast-tracked compliance.
    """
    token, _ = test_users["industry"]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "business": {
                "legal_name": "CloudNine Infotech Private Limited",
                "trade_name": "CloudNine",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "AACCC5555L",
                "gstin": "27AACCC5555L1Z8",
                "msme_category": "MICRO",
            },
            "profile": {
                "nic_code": "62010",
                "manufacturing_activity": "Software development and cloud platform hosting",
                "state": "Maharashtra",
                "district": "Pune",
                "pincode": "411057",
                "industrial_area": "Hinjewadi Infotech Park Phase I",
                "total_employees": 15,
                "plant_machinery_investment": 5000000.0,
                "power_requirement_kw": 25.0,
                "contact_person": "Anita Roy",
                "contact_phone": "+919822334455",
            },
        }

        res = await ac.post(
            "/api/v1/business/onboard",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()

        # Verify auto-categorized as WHITE
        assert data["business"]["profile"]["pollution_category"] == "WHITE"


@pytest.mark.asyncio
async def test_e2e_authorization_boundaries_and_data_isolation(test_users):
    """
    Scenario 3: Verify isolation between rival industry users and role-based officer access.
    """
    ind_token, ind_uid = test_users["industry"]
    intruder_token, _ = test_users["intruder"]
    officer_token, _ = test_users["officer"]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Industry user onboards enterprise
        res = await ac.post(
            "/api/v1/business/onboard",
            json={
                "business": {
                    "legal_name": "Confidential Robotics Pvt Ltd",
                    "entity_type": "PRIVATE_LIMITED",
                    "pan": "AACCR7777K",
                }
            },
            headers={"Authorization": f"Bearer {ind_token}"},
        )
        biz_id = res.json()["business"]["id"]

        # Intruder attempts to view rival business -> 403 Forbidden
        intruder_res = await ac.get(
            f"/api/v1/business/{biz_id}",
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert intruder_res.status_code == 403

        # Intruder attempts to update rival business -> 403 Forbidden
        intruder_put = await ac.put(
            f"/api/v1/business/{biz_id}/profile",
            json={"manufacturing_activity": "Malicious Tampering"},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert intruder_put.status_code == 403

        # Department Officer can view enterprise profile for regulatory oversight
        officer_res = await ac.get(
            f"/api/v1/business/{biz_id}",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert officer_res.status_code == 200
        assert officer_res.json()["legal_name"] == "Confidential Robotics Pvt Ltd"


@pytest.mark.asyncio
async def test_e2e_statutory_validation_rejections(test_users):
    """
    Scenario 4: Verify rejection of invalid statutory data with clear RFC 7807 error details.
    """
    token, _ = test_users["industry"]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Entity type vs PAN 4th character mismatch (Private Limited expects 'C', but given individual 'P')
        res_pan = await ac.post(
            "/api/v1/business/onboard",
            json={
                "business": {
                    "legal_name": "Mismatch Corp Pvt Ltd",
                    "entity_type": "PRIVATE_LIMITED",
                    "pan": "AAAPB1234D",  # 'P' instead of 'C'
                }
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_pan.status_code == 422
        assert "expects 'C'" in res_pan.json()["error"]["message"]

        # 2. Invalid Pincode (starts with 0)
        res_pin = await ac.post(
            "/api/v1/business/onboard",
            json={
                "business": {
                    "legal_name": "Valid Name Pvt Ltd",
                    "entity_type": "PRIVATE_LIMITED",
                    "pan": "AAACB1234D",
                },
                "profile": {
                    "pincode": "011001",
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_pin.status_code == 422
        assert "PIN Code" in res_pin.json()["error"]["message"]
