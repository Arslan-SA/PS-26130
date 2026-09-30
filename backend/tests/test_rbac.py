"""
Unit tests for Role-Based Access Control (RBAC) dependency guards.
"""

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.database import engine, Base
from app.core.dependencies import require_admin, require_industry_user, require_officer
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token
from app.models.user import User, UserRole

test_app = FastAPI()
register_exception_handlers(test_app)

test_router = APIRouter(prefix="/test-rbac")


@test_router.get("/industry", dependencies=[Depends(require_industry_user)])
def industry_only_endpoint():
    return {"message": "Welcome Industry User"}


@test_router.get("/officer", dependencies=[Depends(require_officer)])
def officer_only_endpoint():
    return {"message": "Welcome Department Officer"}


@test_router.get("/admin", dependencies=[Depends(require_admin)])
def admin_only_endpoint():
    return {"message": "Welcome Admin"}


test_app.include_router(test_router)
client = TestClient(test_app)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_rbac_industry_access_and_rejection():
    """Verify industry role can access industry route and is rejected on officer route."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        industry_user = User(
            id="user-ind-1",
            email="industry@company.com",
            hashed_password="hash",
            full_name="Industry User",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(industry_user)
        await session.commit()

    token = create_access_token({"sub": "user-ind-1", "role": "INDUSTRY_USER"})
    headers = {"Authorization": f"Bearer {token}"}

    # Access industry endpoint -> 200
    res1 = client.get("/test-rbac/industry", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["message"] == "Welcome Industry User"

    # Attempt officer endpoint -> 403 Forbidden
    res2 = client.get("/test-rbac/officer", headers=headers)
    assert res2.status_code == 403
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_rbac_admin_universal_access():
    """Verify admin role can access officer and industry routes."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        admin_user = User(
            id="user-adm-1",
            email="admin@udyamsetu.gov.in",
            hashed_password="hash",
            full_name="Super Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()

    token = create_access_token({"sub": "user-adm-1", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Admin accesses industry endpoint
    res1 = client.get("/test-rbac/industry", headers=headers)
    assert res1.status_code == 200

    # Admin accesses officer endpoint
    res2 = client.get("/test-rbac/officer", headers=headers)
    assert res2.status_code == 200

    # Admin accesses admin endpoint
    res3 = client.get("/test-rbac/admin", headers=headers)
    assert res3.status_code == 200
