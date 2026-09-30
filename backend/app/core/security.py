"""
Security utilities for password hashing, verification, and cryptographic operations.
Uses direct bcrypt implementation for maximum security, Python 3.12 compatibility, and speed.
"""

import bcrypt


def get_password_hash(password: str) -> str:
    """Generate a secure salted bcrypt hash for a plain-text password."""
    # Bcrypt operates on byte sequences and max 72 bytes
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plain-text password matches a salted bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate that password meets enterprise security standards:
    Minimum 8 characters, at least one letter, and at least one digit.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""
