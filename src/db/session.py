"""Async SQLAlchemy engine and session factory setup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import Settings


class DatabaseSessionManager:
    """Manage the SQLAlchemy async engine lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._engine = create_async_engine(
            settings.sqlalchemy_async_database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_use_lifo=True,
        )
        self._session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Return the configured async session factory."""

        return self._session_maker

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an async SQLAlchemy session."""

        async with self._session_maker() as session:
            yield session

    async def dispose(self) -> None:
        """Dispose the underlying SQLAlchemy engine."""

        await self._engine.dispose()
