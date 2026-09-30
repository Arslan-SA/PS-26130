"""
Unit and integration tests for refresh token rotation.
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


def test_refresh_token_rotation_success():
    """Verify that a valid refresh token generates fresh tokens and rotates."""
    # Register & Login
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh.user@enterprise.com",
            "password": "SecurePassword123!",
            "full_name": "Session Tester",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh.user@enterprise.com",
            "password": "SecurePassword123!",
        },
    )
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Exchange refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]


def test_refresh_token_rejects_access_token():
    """Verify that an access token cannot be used at the /refresh endpoint."""
    login_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh.access@enterprise.com",
            "password": "SecurePassword123!",
            "full_name": "Tester",
        },
    )
    assert login_res.status_code == 201

    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh.access@enterprise.com",
            "password": "SecurePassword123!",
        },
    )
    access_token = login_res.json()["access_token"]

    # Attempting to use access token at /refresh
    res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"
