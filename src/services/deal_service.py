"""Deal-related business logic."""

from __future__ import annotations

from html import escape

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.repositories.deal_repo import DealRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.formatters import format_money
from src.utils.helpers import build_registration_required_text


class DealService:
    """Application service for reading deal data."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def build_recent_deals_message(self, telegram_id: int) -> str:
        """Build a Telegram-friendly summary of the user's recent deals."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            deal_repo = DealRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if user is None:
                return build_registration_required_text()

            deals = await deal_repo.get_recent_by_user(user.id, limit=5)
            if not deals:
                return (
                    "<b>Сделки</b>\n\n"
                    "Сделок пока нет.\n"
                    "Нажми «Добавить купленный подарок» и перешли уведомление о покупке, чтобы записать первую сделку."
                )

            lines = ["<b>Последние сделки</b>", ""]
            for deal in deals:
                title = escape(deal.item_name)
                if deal.gift_number:
                    title = f"{title} #{escape(deal.gift_number)}"
                lines.append(f"• <b>{title}</b>")
                if deal.marketplace:
                    lines.append(f"  Маркет покупки: {escape(deal.marketplace)}")
                if getattr(deal, "sale_marketplace", None):
                    lines.append(f"  Маркет продажи: {escape(deal.sale_marketplace)}")
                status_label = {
                    "open": "открыта",
                    "closed": "закрыта",
                    "cancelled": "отменена",
                }.get(deal.status.value, deal.status.value)
                lines.append(f"  Статус: {status_label}")
                lines.append(f"  Покупка: {format_money(deal.buy_price, deal.currency.value)}")
                if deal.sell_price is not None:
                    lines.append(f"  Продажа: {format_money(deal.sell_price, deal.currency.value)}")
                if deal.net_profit is not None:
                    lines.append(f"  Профит: {format_money(deal.net_profit, deal.currency.value)}")
                if deal.gift_url:
                    lines.append(f'  Ссылка: <a href="{escape(deal.gift_url)}">открыть</a>')
                lines.append("")

            lines.append("Показаны последние 5 сделок.")
            return "\n".join(lines)
