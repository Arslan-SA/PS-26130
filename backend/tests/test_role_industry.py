"""
Unit tests for Industry role scope and dashboard overview.
"""

import pytest
from fastapi.testclient import TestClient
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.user import User, UserRole

client = TestClient(app)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_industry_role_access():
    """Verify that an industry user can access /industry/dashboard-summary."""
    async with AsyncSessionLocal() as session:
        user = User(
            id="ind-user-001",
            email="promoter@solarpower.in",
            hashed_password="hash",
            full_name="Solar Industrialist",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": "ind-user-001", "role": "INDUSTRY_USER"})
    res = client.get(
        "/api/v1/industry/dashboard-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "INDUSTRY_USER"
    assert "workspace" in data
    assert "next_action" in data


@pytest.mark.asyncio
async def test_industry_route_denies_officer():
    """Verify that department officer cannot access industry workspace route."""
    async with AsyncSessionLocal() as session:
        officer = User(
            id="officer-001",
            email="officer@spcb.gov.in",
            hashed_password="hash",
            full_name="PCB Officer",
            role=UserRole.DEPARTMENT_OFFICER,
            is_active=True,
        )
        session.add(officer)
        await session.commit()

    token = create_access_token({"sub": "officer-001", "role": "DEPARTMENT_OFFICER"})
    res = client.get(
        "/api/v1/industry/dashboard-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
