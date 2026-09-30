"""
Comprehensive End-to-End Multi-Role Authentication & RBAC Test Suite.
Validates the entire lifecycle: registration, login, JWT validation, token refresh,
cross-role authorization matrices, and administrative account governance.
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


@pytest.mark.asyncio
async def test_e2e_multi_role_registration_and_login():
    """Test full registration and login lifecycle for all 4 enterprise roles."""
    roles_data = [
        {
            "role": "INDUSTRY_USER",
            "email": "vikram.aditya@tatasteel.com",
            "password": "Password@123",
            "full_name": "Vikram Aditya",
            "phone": "+919876543210",
        },
        {
            "role": "DEPARTMENT_OFFICER",
            "email": "officer.singh@spcb.gov.in",
            "password": "Password@123",
            "full_name": "Harpreet Singh",
            "department_id": "SPCB-PUNJAB-01",
            "designation": "Chief Environmental Officer",
        },
        {
            "role": "INSPECTOR",
            "email": "inspector.gupta@fire.gov.in",
            "password": "Password@123",
            "full_name": "Rohan Gupta",
            "department_id": "FIRE-DELHI-03",
            "designation": "Divisional Fire Safety Inspector",
        },
        {
            "role": "ADMIN",
            "email": "admin.master@udyamsetu.gov.in",
            "password": "Password@123",
            "full_name": "National Administrator",
            "designation": "System Principal Admin",
        },
    ]

    tokens_by_role = {}

    for data in roles_data:
        # 1. Register
        reg_payload = {
            "email": data["email"],
            "password": data["password"],
            "full_name": data["full_name"],
            "role": data["role"],
            "phone": data.get("phone"),
            "department_id": data.get("department_id"),
            "designation": data.get("designation"),
        }
        reg_res = client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, f"Failed registration for {data['role']}: {reg_res.text}"
        user_info = reg_res.json()
        assert user_info["email"] == data["email"]
        assert user_info["role"] == data["role"]
        assert user_info["is_active"] is True

        # 2. Login
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": data["email"], "password": data["password"]},
        )
        assert login_res.status_code == 200, f"Failed login for {data['role']}: {login_res.text}"
        login_data = login_res.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert login_data["user"]["role"] == data["role"]

        tokens_by_role[data["role"]] = login_data["access_token"]

        # 3. Verify /me
        auth_header = {"Authorization": f"Bearer {login_data['access_token']}"}
        me_res = client.get("/api/v1/auth/me", headers=auth_header)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["id"] == user_info["id"]
        assert me_data["email"] == data["email"]
        assert me_data["role"] == data["role"]

    return tokens_by_role


@pytest.mark.asyncio
async def test_e2e_token_refresh_lifecycle():
    """Verify refresh token rotation and subsequent protected resource consumption."""
    # Register & Login
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh.test@msme.in",
            "password": "Password@123",
            "full_name": "Refresh Tester",
            "role": "INDUSTRY_USER",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh.test@msme.in", "password": "Password@123"},
    )
    login_data = login_res.json()
    refresh_token = login_data["refresh_token"]

    # Rotate refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # Access protected route with new access token
    new_header = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=new_header)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh.test@msme.in"


@pytest.mark.asyncio
async def test_e2e_cross_role_access_control_matrix():
    """
    Verify complete cross-role permission matrix:
    - Industry User: Can access Industry dashboard, CANNOT access Officer, Inspector, or Admin.
    - Officer: Can access Officer inbox, CANNOT access Industry, Inspector, or Admin.
    - Inspector: Can access Inspector schedule, CANNOT access Industry, Officer, or Admin.
    - Admin: Can access Admin endpoints and system overview.
    """
    credentials = [
        ("INDUSTRY_USER", "ind.matrix@enterprise.com"),
        ("DEPARTMENT_OFFICER", "off.matrix@spcb.gov.in"),
        ("INSPECTOR", "insp.matrix@fire.gov.in"),
        ("ADMIN", "adm.matrix@udyamsetu.gov.in"),
    ]

    tokens = {}
    for role, email in credentials:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password@123",
                "full_name": f"{role} User",
                "role": role,
            },
        )
        l_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
        tokens[role] = l_res.json()["access_token"]

    def auth_h(role_name):
        return {"Authorization": f"Bearer {tokens[role_name]}"}

    # 1. Industry portal checks
    assert client.get("/api/v1/industry/dashboard-summary", headers=auth_h("INDUSTRY_USER")).status_code == 200
    assert client.get("/api/v1/industry/dashboard-summary", headers=auth_h("DEPARTMENT_OFFICER")).status_code == 403
    assert client.get("/api/v1/industry/dashboard-summary", headers=auth_h("INSPECTOR")).status_code == 403

    # 2. Officer portal checks
    assert client.get("/api/v1/officer/inbox-summary", headers=auth_h("DEPARTMENT_OFFICER")).status_code == 200
    assert client.get("/api/v1/officer/inbox-summary", headers=auth_h("INDUSTRY_USER")).status_code == 403
    assert client.get("/api/v1/officer/inbox-summary", headers=auth_h("INSPECTOR")).status_code == 403

    # 3. Inspector portal checks
    assert client.get("/api/v1/inspector/schedule-summary", headers=auth_h("INSPECTOR")).status_code == 200
    assert client.get("/api/v1/inspector/schedule-summary", headers=auth_h("INDUSTRY_USER")).status_code == 403
    assert client.get("/api/v1/inspector/schedule-summary", headers=auth_h("DEPARTMENT_OFFICER")).status_code == 403

    # 4. Admin portal checks
    assert client.get("/api/v1/admin/system-overview", headers=auth_h("ADMIN")).status_code == 200
    assert client.get("/api/v1/admin/system-overview", headers=auth_h("INDUSTRY_USER")).status_code == 403
    assert client.get("/api/v1/admin/system-overview", headers=auth_h("DEPARTMENT_OFFICER")).status_code == 403
    assert client.get("/api/v1/admin/system-overview", headers=auth_h("INSPECTOR")).status_code == 403


@pytest.mark.asyncio
async def test_e2e_deactivated_account_enforcement():
    """Verify that deactivating a user via Admin immediately halts authentication and API access."""
    # 1. Register user and admin
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin.governor@udyamsetu.gov.in",
            "password": "Password@123",
            "full_name": "Governance Admin",
            "role": "ADMIN",
        },
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.governor@udyamsetu.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "rogue.enterprise@fake.com",
            "password": "Password@123",
            "full_name": "Rogue Entity",
            "role": "INDUSTRY_USER",
        },
    )
    user_login = client.post(
        "/api/v1/auth/login",
        json={"email": "rogue.enterprise@fake.com", "password": "Password@123"},
    )
    user_token = user_login.json()["access_token"]
    user_id = user_login.json()["user"]["id"]

    # Verify user can access industry dashboard before deactivation
    res = client.get(
        "/api/v1/industry/dashboard-summary",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200

    # 2. Admin deactivates the user
    deact_res = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # 3. Subsequent API calls with existing token must fail with 401 UNAUTHENTICATED
    blocked_res = client.get(
        "/api/v1/industry/dashboard-summary",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert blocked_res.status_code == 401
    assert blocked_res.json()["error"]["code"] == "UNAUTHENTICATED"

    # 4. Subsequent login attempt must fail with 401 UNAUTHENTICATED
    login_blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "rogue.enterprise@fake.com", "password": "Password@123"},
    )
    assert login_blocked.status_code == 401
    assert login_blocked.json()["error"]["code"] == "UNAUTHENTICATED"
