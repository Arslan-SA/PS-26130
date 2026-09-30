"""
Integration tests for Business Onboarding, Profile CRUD, and Completeness REST APIs.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def industry_user_token():
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@apexprecision.com",
            hashed_password=get_password_hash("SecretPassword123!"),
            full_name="Rajesh Patil",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(
            {"sub": user.id, "role": user.role.value, "email": user.email}
        )
        return token, user.id


@pytest.mark.asyncio
async def test_business_onboard_api_success(industry_user_token):
    """Verify POST /api/v1/business/onboard successfully registers unit and computes CPCB."""
    token, _ = industry_user_token
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "business": {
                "legal_name": "Apex Precision Engineering Pvt Ltd",
                "trade_name": "Apex Precision",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "AAACB1234D",
                "gstin": "27AAACB1234D1Z5",
                "udyam_number": "UDYAM-MH-01-0012345",
                "msme_category": "SMALL",
            },
            "profile": {
                "nic_code": "28190",
                "manufacturing_activity": "Manufacture of pumps, valves, and precision mechanical parts",
                "state": "Maharashtra",
                "district": "Pune",
                "city": "Pune",
                "pincode": "411018",
                "industrial_area": "Bhosari MIDC",
                "total_employees": 35,
                "plant_machinery_investment": 25000000.0,
                "power_requirement_kw": 120.0,
                "contact_person": "Rajesh Patil",
                "contact_phone": "+919876543210",
                "contact_email": "rajesh@apexprecision.com",
            },
        }

        resp = await ac.post(
            "/api/v1/business/onboard",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["business"]["legal_name"] == "Apex Precision Engineering Pvt Ltd"
        assert data["business"]["pan"] == "AAACB1234D"
        assert data["business"]["profile"] is not None
        assert data["business"]["profile"]["pollution_category"] is not None
        assert len(data["next_steps"]) > 0


@pytest.mark.asyncio
async def test_business_onboard_invalid_pan_fails(industry_user_token):
    """Verify invalid PAN format fails statutory validation with 422."""
    token, _ = industry_user_token
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "business": {
                "legal_name": "Invalid Pan Corp",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "NOT_A_VALID_PAN",
            }
        }

        resp = await ac.post(
            "/api/v1/business/onboard",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_my_businesses_and_completeness(industry_user_token):
    """Verify fetching user businesses and getting completeness report."""
    token, _ = industry_user_token
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Onboard
        onboard_payload = {
            "business": {
                "legal_name": "Alpha Manufacturing Pvt Ltd",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "AAACB9876K",
            },
            "profile": {
                "nic_code": "28190",
                "manufacturing_activity": "Machining and turning",
                "state": "Maharashtra",
                "district": "Pune",
                "pincode": "411018",
                "contact_person": "Sunil Shinde",
                "contact_phone": "+919876543210",
            },
        }
        res_onboard = await ac.post(
            "/api/v1/business/onboard",
            json=onboard_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_onboard.status_code == 201
        biz_id = res_onboard.json()["business"]["id"]

        # 2. List user businesses
        res_list = await ac.get(
            "/api/v1/business/my-businesses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_list.status_code == 200
        biz_list = res_list.json()
        assert len(biz_list) == 1
        assert biz_list[0]["id"] == biz_id

        # 3. Get single business
        res_single = await ac.get(
            f"/api/v1/business/{biz_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_single.status_code == 200
        assert res_single.json()["legal_name"] == "Alpha Manufacturing Pvt Ltd"

        # 4. Get completeness report
        res_comp = await ac.get(
            f"/api/v1/business/{biz_id}/completeness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert comp_data["business_id"] == biz_id
        assert "total_score" in comp_data
        assert "sections" in comp_data


@pytest.mark.asyncio
async def test_update_profile_api(industry_user_token):
    """Verify PUT /api/v1/business/{business_id}/profile updates operational profile."""
    token, _ = industry_user_token
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        onboard_payload = {
            "business": {
                "legal_name": "Beta Tech Pvt Ltd",
                "entity_type": "PRIVATE_LIMITED",
                "pan": "BBBCB1111Z",
            }
        }
        res_onboard = await ac.post(
            "/api/v1/business/onboard",
            json=onboard_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        biz_id = res_onboard.json()["business"]["id"]

        # Update profile
        update_payload = {
            "manufacturing_activity": "Advanced Robotics Assembly",
            "pincode": "411019",
            "total_employees": 50,
        }
        res_update = await ac.put(
            f"/api/v1/business/{biz_id}/profile",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_update.status_code == 200
        updated_data = res_update.json()
        assert updated_data["manufacturing_activity"] == "Advanced Robotics Assembly"
        assert updated_data["total_employees"] == 50
        assert updated_data["profile_completeness"] > 0
