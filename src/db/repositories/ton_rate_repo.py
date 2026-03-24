"""Repository for TON rate snapshots."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from src.db.models.ton_rate import TonRate
from src.db.repositories.base import BaseRepository


class TonRateRepository(BaseRepository[TonRate]):
    """Data access for TON rates."""

    async def create(self, rate: Decimal, source: str) -> TonRate:
        """Persist a TON rate snapshot."""

        ton_rate = TonRate(rate=rate, source=source)
        return await self.add(ton_rate)

    async def get_latest(self) -> TonRate | None:
        """Return the latest stored TON rate."""

        stmt = select(TonRate).order_by(TonRate.created_at.desc()).limit(1)
        return await self.session.scalar(stmt)
