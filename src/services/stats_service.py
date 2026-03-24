"""Statistics business logic."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.repositories.deal_repo import DealRepository
from src.db.repositories.ton_rate_repo import TonRateRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.currency_conversion import convert_amount_to_ton
from src.utils.enums import DealStatus
from src.utils.formatters import format_money
from src.utils.helpers import build_registration_required_text


class StatsService:
    """Application service for analytics and statistics."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def build_stats_message(self, telegram_id: int) -> str:
        """Build an aggregated statistics message for the user."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            deal_repo = DealRepository(session)
            ton_rate_repo = TonRateRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if user is None:
                return build_registration_required_text()

            deals = await deal_repo.get_all_by_user(user.id)
            latest_rate = await ton_rate_repo.get_latest()
            fallback_ton_rate = latest_rate.rate if latest_rate is not None else None

            total_count = len(deals)
            open_count = sum(1 for deal in deals if deal.status == DealStatus.OPEN)
            closed_count = sum(1 for deal in deals if deal.status == DealStatus.CLOSED)

            total_buy_volume = self._sum_field_in_ton(
                deals,
                field_name="buy_price",
                fallback_ton_rate=fallback_ton_rate,
            )
            total_net_profit = self._sum_field_in_ton(
                deals,
                field_name="net_profit",
                fallback_ton_rate=fallback_ton_rate,
            )

            last_activity_text = "ещё не было"
            if deals:
                activity_at = max((deal.updated_at or deal.created_at) for deal in deals)
                last_activity_text = activity_at.strftime("%d.%m.%Y %H:%M UTC")

            return (
                "<b>Статистика</b>\n\n"
                f"Всего сделок: {total_count}\n"
                f"Открытых: {open_count}\n"
                f"Закрытых: {closed_count}\n"
                f"Сумма входа: {format_money(total_buy_volume, 'TON')}\n"
                f"Суммарный профит: {format_money(total_net_profit, 'TON')}\n"
                f"Последнее обновление учёта: {last_activity_text}"
            )

    def _sum_field_in_ton(
        self,
        deals: list[Any],
        *,
        field_name: str,
        fallback_ton_rate: Decimal | None,
    ) -> Decimal | None:
        """Sum a numeric deal field in TON using per-deal or fallback conversion rates."""

        if not deals:
            return Decimal("0")

        total = Decimal("0")
        converted_any = False

        for deal in deals:
            amount = getattr(deal, field_name, None)
            if amount is None:
                continue

            converted = convert_amount_to_ton(
                amount,
                source_currency=deal.currency,
                ton_usd_rate=getattr(deal, "ton_usd_rate", None) or fallback_ton_rate,
                quantize_to=None,
            )
            if converted is None:
                continue

            total += converted
            converted_any = True

        if not converted_any:
            return None

        return total
