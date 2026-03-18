from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,  # SQL logging is only enabled in dev to avoid log noise in production
    pool_pre_ping=True,  # validates connections before use so stale pool connections don't surface as errors
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keeps ORM objects usable after commit without triggering extra SELECT queries
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Context manager handles session teardown (commit/rollback/close) automatically
    async with AsyncSessionLocal() as session:
        yield session
