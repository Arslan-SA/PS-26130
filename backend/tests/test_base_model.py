"""
Unit tests for BaseModel and mixin behaviors.
"""

import pytest
from sqlalchemy import Column, String
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.base import BaseModel, AuditMixin


class DummyEntity(BaseModel, AuditMixin):
    __tablename__ = "dummy_entities"
    title = Column(String(100), nullable=False)


@pytest.mark.asyncio
async def test_base_model_lifecycle():
    """Verify that BaseModel generates UUIDs and handles timestamps properly."""
    # Ensure test table exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        entity = DummyEntity(title="Industrial Unit A", created_by_id="user-123")
        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        assert entity.id is not None
        assert len(entity.id) == 36
        assert entity.title == "Industrial Unit A"
        assert entity.created_by_id == "user-123"
        assert entity.is_active is True
        assert entity.created_at is not None

        d = entity.to_dict()
        assert d["id"] == entity.id
        assert d["title"] == "Industrial Unit A"
