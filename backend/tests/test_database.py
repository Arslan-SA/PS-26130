"""
Unit tests for async database engine and session dependency.
"""

import pytest
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine


@pytest.mark.asyncio
async def test_database_connection():
    """Verify that the configured engine can connect and execute a basic query."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        val = result.scalar()
        assert val == 1
