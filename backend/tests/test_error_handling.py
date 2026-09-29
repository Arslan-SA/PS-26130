"""
Unit tests for API error handling and RFC structured responses.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.exceptions import (
    register_exception_handlers,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
)

test_app = FastAPI()
register_exception_handlers(test_app)


@test_app.get("/test/not-found")
def trigger_not_found():
    raise NotFoundError("Approval application not found", details={"id": "app-404"})


@test_app.get("/test/validation")
def trigger_validation():
    raise ValidationError("Invalid investment amount", details={"field": "investment_amount"})


@test_app.get("/test/auth")
def trigger_auth():
    raise AuthenticationError("Session expired")


@test_app.get("/test/forbidden")
def trigger_forbidden():
    raise AuthorizationError("Only department officers can access this review queue")


@test_app.get("/test/conflict")
def trigger_conflict():
    raise ConflictError("Application already submitted")


client = TestClient(test_app)


def test_not_found_handling():
    res = client.get("/test/not-found")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "Approval application not found" in data["error"]["message"]
    assert data["error"]["details"] == {"id": "app-404"}


def test_validation_handling():
    res = client.get("/test/validation")
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_FAILED"


def test_auth_handling():
    res = client.get("/test/auth")
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHENTICATED"


def test_forbidden_handling():
    res = client.get("/test/forbidden")
    assert res.status_code == 403
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


def test_conflict_handling():
    res = client.get("/test/conflict")
    assert res.status_code == 409
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CONFLICT"
