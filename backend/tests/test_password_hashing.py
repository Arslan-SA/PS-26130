"""
Unit tests for password hashing and verification.
"""

from app.core.security import (
    get_password_hash,
    verify_password,
    validate_password_strength,
)


def test_password_hashing_and_verification():
    """Verify that hashing and verification are mathematically consistent."""
    raw_password = "SecurePassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_password_salt_randomness():
    """Verify that two hashes of the same password produce distinct salt hashes."""
    pwd = "IndustrialAuthPass2026"
    hash1 = get_password_hash(pwd)
    hash2 = get_password_hash(pwd)
    assert hash1 != hash2
    assert verify_password(pwd, hash1) is True
    assert verify_password(pwd, hash2) is True


def test_password_strength_validator():
    """Verify complexity rules enforcement."""
    ok, _ = validate_password_strength("Short1")
    assert ok is False

    ok, _ = validate_password_strength("alllettersinlowercase")
    assert ok is False

    ok, _ = validate_password_strength("1234567890")
    assert ok is False

    ok, _ = validate_password_strength("ValidPass2026")
    assert ok is True
