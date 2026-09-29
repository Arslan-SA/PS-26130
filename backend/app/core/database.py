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

logger = logging.getLogger("udyamsetu.database")

# Default database URL: fallback to local SQLite for zero-dependency local runs
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./udyamsetu.db")

# Setup engine arguments based on database driver
engine_kwargs = {
    "echo": os.getenv("DEBUG", "false").lower() == "true",
    "future": True,
}

if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
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
