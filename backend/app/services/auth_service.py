"""
Authentication and user lifecycle domain business service.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationError
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
