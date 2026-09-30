"""
Unit tests for Inspector role scope and assigned inspection queues.
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
async def test_inspector_role_access():
    """Verify field inspector can access inspection schedule summary."""
    async with AsyncSessionLocal() as session:
        inspector = User(
            id="insp-001",
            email="inspector.dish@gov.in",
            hashed_password="hash",
            full_name="Factory Safety Inspector",
            role=UserRole.INSPECTOR,
            department_id="dept-dish-01",
            designation="Boiler & Plant Inspector",
            is_active=True,
        )
        session.add(inspector)
        await session.commit()

    token = create_access_token({"sub": "insp-001", "role": "INSPECTOR"})
    res = client.get(
        "/api/v1/inspector/schedule-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "INSPECTOR"
    assert data["inspector_id"] == "insp-001"
    assert "inspection_metrics" in data


@pytest.mark.asyncio
async def test_inspector_route_denies_industry_user():
    """Verify industry user cannot access inspector schedule."""
    async with AsyncSessionLocal() as session:
        user = User(
            id="ind-user-003",
            email="founder@startup.io",
            hashed_password="hash",
            full_name="Tech MSME Founder",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": "ind-user-003", "role": "INDUSTRY_USER"})
    res = client.get(
        "/api/v1/inspector/schedule-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
