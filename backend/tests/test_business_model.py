"""
Unit tests for Business enterprise domain model, statutory fields, and user associations.
"""

from datetime import date
import pytest
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.business import Business, EntityType, MSMECategory


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_business_creation_and_defaults():
    """Verify Business entity creation, default values, and statutory attributes."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@bharatalloys.com",
            hashed_password="hashed_pw_test",
            full_name="Anil Singhal",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.flush()

        business = Business(
            user_id=user.id,
            legal_name="Bharat Alloys & Casting Private Limited",
            trade_name="Bharat Alloys",
            entity_type=EntityType.PRIVATE_LIMITED,
            pan="AAACB1234D",
            gstin="27AAACB1234D1Z5",
            udyam_number="UDYAM-MH-01-0098765",
            cin="U27100MH2020PTC123456",
            msme_category=MSMECategory.MEDIUM,
            incorporation_date=date(2020, 4, 15),
            website="https://bharatalloys.com",
        )
        session.add(business)
        await session.commit()

        # Retrieve and verify
        stmt = select(Business).where(Business.pan == "AAACB1234D")
        result = await session.execute(stmt)
        saved = result.scalar_one()

        assert saved.id is not None
        assert saved.legal_name == "Bharat Alloys & Casting Private Limited"
        assert saved.trade_name == "Bharat Alloys"
        assert saved.entity_type == EntityType.PRIVATE_LIMITED
        assert saved.msme_category == MSMECategory.MEDIUM
        assert saved.is_active is True
        assert saved.is_verified is False
        assert saved.incorporation_date == date(2020, 4, 15)
        assert saved.created_at is not None
        assert saved.updated_at is not None


@pytest.mark.asyncio
async def test_business_user_relationship():
    """Verify bidirectional relationship between User and Business."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="founder@greenenergy.in",
            hashed_password="pw_test_123",
            full_name="Pooja Deshmukh",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.flush()

        b1 = Business(
            user_id=user.id,
            legal_name="Green Energy Plant 1 LLP",
            entity_type=EntityType.LLP,
            pan="AABCG5432E",
            msme_category=MSMECategory.SMALL,
        )
        b2 = Business(
            user_id=user.id,
            legal_name="Green Energy Solar Works Pvt Ltd",
            entity_type=EntityType.PRIVATE_LIMITED,
            pan="AAACG9876F",
            msme_category=MSMECategory.MICRO,
        )
        session.add_all([b1, b2])
        await session.commit()

        # Query user with businesses
        stmt = select(User).where(User.id == user.id)
        result = await session.execute(stmt)
        queried_user = result.scalar_one()

        # Check relationship
        assert len(queried_user.businesses) == 2
        names = {b.legal_name for b in queried_user.businesses}
        assert "Green Energy Plant 1 LLP" in names
        assert "Green Energy Solar Works Pvt Ltd" in names


@pytest.mark.asyncio
async def test_business_cascade_deletion():
    """Verify that deleting a User cascades and removes linked Business records."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="to_delete@steel.in",
            hashed_password="pw_test_123",
            full_name="Deletable User",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.flush()

        b = Business(
            user_id=user.id,
            legal_name="Deletable Steel Works Ltd",
            entity_type=EntityType.PUBLIC_LIMITED,
            pan="AAACD9999Z",
        )
        session.add(b)
        await session.commit()

        # Delete user
        await session.delete(user)
        await session.commit()

        # Check that business is also gone
        stmt = select(Business).where(Business.pan == "AAACD9999Z")
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is None
