"""
User database model with Role-Based Access Control (RBAC) enumeration.
"""

import enum
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """System-wide Role-Based Access Control definitions."""
    INDUSTRY_USER = "INDUSTRY_USER"
    DEPARTMENT_OFFICER = "DEPARTMENT_OFFICER"
    INSPECTOR = "INSPECTOR"
    ADMIN = "ADMIN"


class User(BaseModel):
    """User account entity representing entrepreneurs, officers, inspectors, and admins."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.INDUSTRY_USER,
        nullable=False,
        index=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    # Scoping field for Department Officers and Inspectors
    department_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    designation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User email={self.email} role={self.role}>"
