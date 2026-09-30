"""
Authentication API endpoints: Registration, Login, Token Refresh, and Profile.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import authenticate_user, register_user

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


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT tokens",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password credentials.
    Returns signed JWT access token, refresh token, and user identity profile.
    """
    user = await authenticate_user(db, payload.email, payload.password)

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "department_id": user.department_id,
    }

    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns the authenticated user's profile and permissions."""
    return UserResponse.model_validate(current_user)
