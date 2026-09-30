"""
Integration tests for user registration endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.core.database import engine, Base
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_user_registration_success():
    """Verify that a new industry user can register successfully."""
    payload = {
        "email": "new.industry@tatasteel.com",
        "password": "Password123!",
        "full_name": "Tata Steel Plant Incharge",
        "role": "INDUSTRY_USER",
        "phone": "+919876543210",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new.industry@tatasteel.com"
    assert data["full_name"] == "Tata Steel Plant Incharge"
    assert data["role"] == "INDUSTRY_USER"
    assert "hashed_password" not in data  # Sensitive fields must not leak
    assert data["id"] is not None


def test_user_registration_duplicate_email():
    """Verify that duplicate registration with the same email returns 409 Conflict."""
    payload = {
        "email": "duplicate@company.com",
        "password": "Password123!",
        "full_name": "Applicant A",
    }
    # First registration
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CONFLICT"


def test_user_registration_weak_password():
    """Verify that passwords failing complexity rules return 422."""
    payload = {
        "email": "weak@company.com",
        "password": "weak",  # Less than 8 characters
        "full_name": "Weak Pass User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
