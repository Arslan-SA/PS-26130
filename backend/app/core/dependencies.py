"""
Common FastAPI dependencies for authentication, RBAC, and database sessions.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and authenticate the user identity from the Bearer JWT token.
    Raises AuthenticationError if token is absent, invalid, or user does not exist.
    """
    if not token:
        raise AuthenticationError("Authorization header with Bearer token is required.")

    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Malformed token: missing subject claim.")

    token_type: str = payload.get("type", "access")
    if token_type != "access":
        raise AuthenticationError("Invalid token type: access token required.")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User account belonging to this token no longer exists.")

    if not user.is_active:
        raise AuthenticationError("User account has been deactivated.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify that the authenticated user is currently active."""
    if not current_user.is_active:
        raise AuthenticationError("Inactive user account.")
    return current_user
