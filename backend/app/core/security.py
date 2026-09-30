"""
Security utilities for password hashing, verification, and cryptographic operations.
Includes JWT encoding, decoding, and validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError


def get_password_hash(password: str) -> str:
    """Generate a secure salted bcrypt hash for a plain-text password."""
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
    """Validate password length and character complexity."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with unique jti claim."""
    import uuid
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a long-lived signed JWT refresh token with unique jti claim."""
    import uuid
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a signed JWT token.
    Raises AuthenticationError if expired or signature is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Could not validate credentials: {str(e)}")
