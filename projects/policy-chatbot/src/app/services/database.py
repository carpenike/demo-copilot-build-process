"""Database session factory — async SQLAlchemy engine + session."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def create_engine(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Build an async session factory from the configured database URL."""
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, rolling back on error."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
