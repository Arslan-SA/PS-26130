"""
Common FastAPI dependencies for authentication, RBAC, and database sessions.
Enforces role-based permission checks across industry users, department officers, inspectors, and administrators.
"""

from typing import Callable, Sequence
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and authenticate user identity from Bearer JWT token.
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


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory that enforces Role-Based Access Control (RBAC).
    ADMIN always possesses global oversight privileges.
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # Admin has universal administrative clearance
        if current_user.role == UserRole.ADMIN:
            return current_user

        if current_user.role not in allowed_roles:
            role_names = [r.value for r in allowed_roles]
            raise AuthorizationError(
                message=f"Access forbidden: User has role '{current_user.role.value}', but role in {role_names} is required.",
                details={
                    "user_role": current_user.role.value,
                    "required_roles": role_names,
                },
            )
        return current_user

    return role_checker


# Convenient pre-configured role dependency guards
require_industry_user = require_roles(UserRole.INDUSTRY_USER)
require_officer = require_roles(UserRole.DEPARTMENT_OFFICER)
require_inspector = require_roles(UserRole.INSPECTOR)
require_admin = require_roles(UserRole.ADMIN)
