"""
Authentication API endpoints: Registration, Login, Token Refresh, and Profile.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserRegisterRequest, UserResponse
from app.services.auth_service import register_user

router = APIRouter(prefix="/auth", tags=["Authentication & Access"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new legal industry user, officer, or inspector.
    Performs password hashing and validates uniqueness of email.
    """
    user = await register_user(db, payload)
    return UserResponse.model_validate(user)
