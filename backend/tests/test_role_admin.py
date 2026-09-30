"""
Unit tests for Admin role scope and user governance endpoints.
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
async def test_admin_system_overview_and_user_list():
    """Verify admin can view system overview and list all users."""
    async with AsyncSessionLocal() as session:
        admin = User(
            id="adm-001",
            email="superadmin@gov.in",
            hashed_password="hash",
            full_name="Portal Master Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user = User(
            id="ind-004",
            email="factory@steel.in",
            hashed_password="hash",
            full_name="Factory Unit",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add_all([admin, user])
        await session.commit()

    token = create_access_token({"sub": "adm-001", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # System overview
    ov_res = client.get("/api/v1/admin/system-overview", headers=headers)
    assert ov_res.status_code == 200
    ov_data = ov_res.json()
    assert ov_data["total_registered_users"] >= 2

    # User listing
    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 200
    users_data = users_res.json()
    assert len(users_data) >= 2


@pytest.mark.asyncio
async def test_admin_can_toggle_user_status():
    """Verify admin can activate or deactivate a user account."""
    async with AsyncSessionLocal() as session:
        admin = User(
            id="adm-002",
            email="admin2@gov.in",
            hashed_password="hash",
            full_name="Admin 2",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user = User(
            id="target-user-001",
            email="badactor@spam.in",
            hashed_password="hash",
            full_name="Suspended Account",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add_all([admin, user])
        await session.commit()

    token = create_access_token({"sub": "adm-002", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Deactivate target user
    patch_res = client.patch(
        "/api/v1/admin/users/target-user-001/status",
        json={"is_active": False},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_route_rejects_non_admin():
    """Verify non-admin roles receive 403 Forbidden on admin endpoints."""
    async with AsyncSessionLocal() as session:
        industry_user = User(
            id="reg-user-005",
            email="regular@company.com",
            hashed_password="hash",
            full_name="Regular Business",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(industry_user)
        await session.commit()

    token = create_access_token({"sub": "reg-user-005", "role": "INDUSTRY_USER"})
    res = client.get(
        "/api/v1/admin/system-overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
