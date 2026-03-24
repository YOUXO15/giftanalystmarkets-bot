"""Base repository helpers."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Base repository with shared session access."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, model: ModelT) -> ModelT:
        """Add a model to the session and flush it."""

        self.session.add(model)
        await self.session.flush()
        return model
