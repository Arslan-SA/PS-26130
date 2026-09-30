"""
Authentication and user lifecycle domain business service.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.core.security import get_password_hash, validate_password_strength
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest


async def register_user(db: AsyncSession, request: UserRegisterRequest) -> User:
    """
    Register a new user account with duplicate prevention and password complexity enforcement.
    """
    # 1. Check duplicate email
    existing_stmt = select(User).where(User.email == request.email.lower().strip())
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise ConflictError(
            message=f"An account with email '{request.email}' already exists.",
            details={"field": "email", "value": request.email},
        )

    # 2. Validate password strength
    is_valid, msg = validate_password_strength(request.password)
    if not is_valid:
        raise ValidationError(
            message=msg,
            details={"field": "password"},
        )

    # 3. Hash password and persist user
    user = User(
        email=request.email.lower().strip(),
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name.strip(),
        role=request.role or UserRole.INDUSTRY_USER,
        phone=request.phone.strip() if request.phone else None,
        department_id=request.department_id,
        designation=request.designation.strip() if request.designation else None,
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Authenticate user credentials against hashed password.
    Raises AuthenticationError on invalid credentials or deactivated accounts.
    """
    stmt = select(User).where(User.email == email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("This user account has been deactivated.")

    from app.core.security import verify_password
    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    return user


async def refresh_user_token(db: AsyncSession, refresh_token: str) -> tuple[str, str, int]:
    """
    Validate refresh token, verify user status, and issue a fresh access and rotated refresh token.
    """
    from app.core.security import create_access_token, create_refresh_token, decode_token
    from app.core.config import settings

    payload = decode_token(refresh_token)
    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "refresh":
        raise AuthenticationError("Invalid refresh token.")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User is no longer active.")

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "department_id": user.department_id,
    }

    new_access_token = create_access_token(data=token_payload)
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return new_access_token, new_refresh_token, expires_in
