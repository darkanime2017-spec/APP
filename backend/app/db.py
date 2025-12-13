"""
Database connection setup.

This module initializes the asynchronous SQLAlchemy engine and session factory.
It provides a dependency (`get_async_session`) for FastAPI endpoints to get a
database session.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create an asynchronous engine instance.
async_engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create a configured "Session" class.
AsyncSessionFactory = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    async with AsyncSessionFactory() as session:
        yield session