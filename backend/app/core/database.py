"""
Database engine configuration and async session manager.
Supports both PostgreSQL (asyncpg with pgvector) and SQLite (aiosqlite) fallback.
"""

import logging
from typing import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger("udyamsetu.database")

DATABASE_URL = settings.DATABASE_URL

# Setup engine arguments based on database driver
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })
elif DATABASE_URL.startswith("sqlite"):
    # SQLite requires connect_args for multithreaded/async safety
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine: AsyncEngine = create_async_engine(DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
