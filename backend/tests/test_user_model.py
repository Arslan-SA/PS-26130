"""
Unit tests for User database model and RBAC roles.
"""

import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_user_creation_and_defaults():
    """Verify that User entity persists with defaults, UUID primary key, and correct role."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            email="entrepreneur@msme.example.com",
            hashed_password="fake-hashed-password",
            full_name="Rajesh Sharma",
            phone="+919876543210",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert len(user.id) == 36
        assert user.email == "entrepreneur@msme.example.com"
        assert user.role == UserRole.INDUSTRY_USER
        assert user.is_active is True
        assert user.is_verified is False

        # Query user back
        stmt = select(User).where(User.email == "entrepreneur@msme.example.com")
        result = await session.execute(stmt)
        fetched_user = result.scalar_one()
        assert fetched_user.full_name == "Rajesh Sharma"
        assert fetched_user.role == UserRole.INDUSTRY_USER
