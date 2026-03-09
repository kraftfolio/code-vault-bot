"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Database Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Async SQLAlchemy engine & session factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings
from bot.models import Base

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

_DB_URL = f"sqlite+aiosqlite:///{settings.DB_PATH}"

engine = create_async_engine(_DB_URL, echo=False)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Convenience helper — returns a new session."""
    return async_session()
