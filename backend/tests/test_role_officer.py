"""
Unit tests for Department Officer role context and queue access.
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
async def test_officer_role_access():
    """Verify department officer can access officer inbox summary."""
    async with AsyncSessionLocal() as session:
        officer = User(
            id="dept-off-001",
            email="officer.firesafety@gov.in",
            hashed_password="hash",
            full_name="Fire Safety Inspector-in-Charge",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="dept-fire-01",
            designation="Divisional Fire Officer",
            is_active=True,
        )
        session.add(officer)
        await session.commit()

    token = create_access_token({"sub": "dept-off-001", "role": "DEPARTMENT_OFFICER"})
    res = client.get(
        "/api/v1/officer/inbox-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "DEPARTMENT_OFFICER"
    assert data["department_id"] == "dept-fire-01"
    assert "queue_metrics" in data


@pytest.mark.asyncio
async def test_officer_route_denies_industry_user():
    """Verify industry user cannot access officer review inbox."""
    async with AsyncSessionLocal() as session:
        user = User(
            id="ind-user-002",
            email="promoter@factory.in",
            hashed_password="hash",
            full_name="Factory Owner",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": "ind-user-002", "role": "INDUSTRY_USER"})
    res = client.get(
        "/api/v1/officer/inbox-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
