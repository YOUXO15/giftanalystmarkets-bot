"""TON exchange-rate business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import Settings
from src.db.repositories.ton_rate_repo import TonRateRepository
from src.integrations.ton_client import TonClient
from src.utils.enums import Currency
from src.utils.formatters import format_money


class TonService:
    """Application service for TON rates."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._session_maker = session_maker
        self._client = TonClient(settings)

    async def build_rate_message(self) -> str:
        """Fetch a fresh TON rate or fall back to the latest stored snapshot."""

        payload = await self._client.get_current_rate()

        async with self._session_maker() as session:
            ton_rate_repo = TonRateRepository(session)

            if payload.success and payload.rate is not None:
                async with session.begin():
                    await ton_rate_repo.create(payload.rate, payload.source)
                return (
                    "<b>Курс TON</b>\n\n"
                    f"Текущее значение: {format_money(payload.rate, Currency.USD.value)}"
                )

            latest_rate = await ton_rate_repo.get_latest()
            if latest_rate is not None:
                return (
                    "<b>Курс TON</b>\n\n"
                    "Не удалось обновить котировку в реальном времени.\n"
                    f"Последнее сохранённое значение: {format_money(latest_rate.rate, Currency.USD.value)}"
                )

            return f"<b>Курс TON</b>\n\n{payload.message}"
