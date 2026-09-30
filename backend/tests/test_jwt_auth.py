"""
Unit and integration tests for JWT authentication and /auth/me endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.core.database import engine, Base
from app.core.security import create_access_token, decode_token
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_jwt_token_encode_decode():
    """Verify raw JWT encoding and decoding."""
    payload = {"sub": "user-uuid-12345", "role": "INDUSTRY_USER"}
    token = create_access_token(payload)
    decoded = decode_token(token)

    assert decoded["sub"] == "user-uuid-12345"
    assert decoded["role"] == "INDUSTRY_USER"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_auth_me_with_valid_bearer_token():
    """Verify that /auth/me returns the authenticated user using Bearer token."""
    # Register user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "officer@pcb.state.gov.in",
            "password": "SecurePassword123!",
            "full_name": "Senior Environmental Officer",
            "role": "DEPARTMENT_OFFICER",
        },
    )
    assert reg_res.status_code == 201

    # Login to obtain JWT
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "officer@pcb.state.gov.in",
            "password": "SecurePassword123!",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Access /auth/me with Bearer header
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "officer@pcb.state.gov.in"
    assert me_data["role"] == "DEPARTMENT_OFFICER"


def test_auth_me_missing_token():
    """Verify that calling /auth/me without token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_me_invalid_token():
    """Verify that calling /auth/me with forged token returns 401."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.forged.token"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"
