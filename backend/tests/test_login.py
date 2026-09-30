"""
Integration tests for user login and credential verification.
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_user_login_success():
    """Verify that a registered user can log in with correct credentials."""
    # Register user first
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@enterprise.com",
            "password": "CorrectPassword123!",
            "full_name": "Test User",
            "role": "INDUSTRY_USER",
        },
    )
    assert res_reg.status_code == 201

    # Attempt login
    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@enterprise.com",
            "password": "CorrectPassword123!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user@enterprise.com"
    assert data["user"]["role"] == "INDUSTRY_USER"


def test_user_login_wrong_password():
    """Verify that wrong password returns 401 Unauthenticated."""
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@enterprise.com",
            "password": "CorrectPassword123!",
            "full_name": "Test User 2",
        },
    )
    assert res_reg.status_code == 201

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user2@enterprise.com",
            "password": "WrongPassword123!",
        },
    )
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHENTICATED"


def test_user_login_nonexistent_email():
    """Verify that non-registered email returns 401 Unauthenticated."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@enterprise.com",
            "password": "SomePassword123!",
        },
    )
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHENTICATED"
