"""
Declarative base and common mixins for all SQLAlchemy domain models.
Enforces UUID primary keys, UTC timestamp auditing, and serialization helpers.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    """Generate a standard canonical UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin adding standard audit timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class AuditMixin:
    """Mixin for tracking user actor provenance."""
    created_by_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )


class BaseModel(Base, TimestampMixin):
    """
    Abstract base entity providing canonical string UUID primary keys
    and timestamp audit tracking.
    """
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a plain Python dictionary."""
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
