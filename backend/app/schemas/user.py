"""
Pydantic schemas for User registration, authentication, and profiles.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user account."""
    email: EmailStr = Field(..., description="Corporate or official email address")
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full name of applicant or officer")
    role: UserRole = Field(default=UserRole.INDUSTRY_USER, description="Assigned system role")
    phone: Optional[str] = Field(default=None, max_length=20, description="Contact mobile number")
    department_id: Optional[str] = Field(default=None, description="Department UUID if officer/inspector")
    designation: Optional[str] = Field(default=None, max_length=100, description="Job title / designation")


class UserLoginRequest(BaseModel):
    """Payload for authenticating user credentials."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    """Public representation of user identity."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department_id: Optional[str] = None
    designation: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Standard Bearer token envelope with refresh token and user identity."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Payload for rotating tokens using an existing refresh token."""
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class RefreshTokenResponse(BaseModel):
    """Rotated access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
