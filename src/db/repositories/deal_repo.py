"""Repository for deals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from src.db.models.deal import Deal
from src.db.repositories.base import BaseRepository
from src.utils.enums import Currency, DealStatus


@dataclass(slots=True)
class DealMetrics:
    """Aggregated deal metrics for a user."""

    total_count: int
    open_count: int
    closed_count: int
    total_buy_volume: Decimal
    total_net_profit: Decimal


class DealRepository(BaseRepository[Deal]):
    """Data access for deals."""

    async def get_by_external_deal_id(self, external_deal_id: str) -> Deal | None:
        """Fetch a deal by external system identifier."""

        stmt = select(Deal).where(Deal.external_deal_id == external_deal_id)
        return await self.session.scalar(stmt)

    async def get_recent_by_user(self, user_id: int, limit: int = 5) -> list[Deal]:
        """Return the most recent deals for a user."""

        stmt = (
            select(Deal)
            .where(Deal.user_id == user_id)
            .order_by(Deal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_all_by_user(self, user_id: int) -> list[Deal]:
        """Return all deals for a user."""

        stmt = select(Deal).where(Deal.user_id == user_id).order_by(Deal.created_at.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_by_id_for_user(self, deal_id: int, user_id: int) -> Deal | None:
        """Return a single deal by internal id for a specific user."""

        stmt = select(Deal).where(Deal.id == deal_id, Deal.user_id == user_id)
        return await self.session.scalar(stmt)

    async def get_open_by_user(self, user_id: int) -> list[Deal]:
        """Return all open deals for a user ordered by newest first."""

        stmt = (
            select(Deal)
            .where(Deal.user_id == user_id, Deal.status == DealStatus.OPEN)
            .order_by(Deal.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_open_by_gift_url(self, user_id: int, gift_url: str) -> Deal | None:
        """Return an open deal for the same gift URL if it already exists."""

        stmt = select(Deal).where(
            Deal.user_id == user_id,
            Deal.gift_url == gift_url,
            Deal.status == DealStatus.OPEN,
        )
        return await self.session.scalar(stmt)

    async def get_metrics(self, user_id: int) -> DealMetrics:
        """Return aggregate metrics for the user's deals."""

        total_count = await self.session.scalar(
            select(func.count(Deal.id)).where(Deal.user_id == user_id)
        )
        open_count = await self.session.scalar(
            select(func.count(Deal.id)).where(Deal.user_id == user_id, Deal.status == DealStatus.OPEN)
        )
        closed_count = await self.session.scalar(
            select(func.count(Deal.id)).where(Deal.user_id == user_id, Deal.status == DealStatus.CLOSED)
        )
        total_buy_volume = await self.session.scalar(
            select(func.coalesce(func.sum(Deal.buy_price), 0)).where(Deal.user_id == user_id)
        )
        total_net_profit = await self.session.scalar(
            select(func.coalesce(func.sum(Deal.net_profit), 0)).where(Deal.user_id == user_id)
        )

        return DealMetrics(
            total_count=int(total_count or 0),
            open_count=int(open_count or 0),
            closed_count=int(closed_count or 0),
            total_buy_volume=Decimal(str(total_buy_volume or 0)),
            total_net_profit=Decimal(str(total_net_profit or 0)),
        )

    async def upsert_many(self, user_id: int, payloads: list[dict[str, Any]]) -> int:
        """Insert or update a batch of deals from an external payload."""

        synced_count = 0
        for payload in payloads:
            external_deal_id = str(payload["external_deal_id"])
            deal = await self.get_by_external_deal_id(external_deal_id)
            if deal is None:
                deal = Deal(
                    user_id=user_id,
                    external_deal_id=external_deal_id,
                    item_name=str(payload.get("item_name") or "Unknown item"),
                    category=_nullable_str(payload.get("category")),
                    sale_marketplace=_nullable_str(payload.get("sale_marketplace")),
                    buy_price=_to_decimal(payload.get("buy_price"), default="0"),
                    sell_price=_to_nullable_decimal(payload.get("sell_price")),
                    fee=_to_decimal(payload.get("fee"), default="0"),
                    net_profit=_to_nullable_decimal(payload.get("net_profit")),
                    currency=_to_currency(payload.get("currency")),
                    ton_usd_rate=_to_nullable_decimal(payload.get("ton_usd_rate")),
                    sale_ton_usd_rate=_to_nullable_decimal(payload.get("sale_ton_usd_rate")),
                    status=_to_status(payload.get("status")),
                    opened_at=_to_datetime(payload.get("opened_at")),
                    closed_at=_to_datetime(payload.get("closed_at")),
                )
                self.session.add(deal)
            else:
                deal.item_name = str(payload.get("item_name") or deal.item_name)
                deal.category = _nullable_str(payload.get("category"))
                deal.sale_marketplace = _nullable_str(payload.get("sale_marketplace"))
                deal.buy_price = _to_decimal(payload.get("buy_price"), default=str(deal.buy_price))
                deal.sell_price = _to_nullable_decimal(payload.get("sell_price"))
                deal.fee = _to_decimal(payload.get("fee"), default=str(deal.fee))
                deal.net_profit = _to_nullable_decimal(payload.get("net_profit"))
                deal.currency = _to_currency(payload.get("currency"))
                deal.ton_usd_rate = _to_nullable_decimal(payload.get("ton_usd_rate"))
                deal.sale_ton_usd_rate = _to_nullable_decimal(payload.get("sale_ton_usd_rate"))
                deal.status = _to_status(payload.get("status"))
                deal.opened_at = _to_datetime(payload.get("opened_at"))
                deal.closed_at = _to_datetime(payload.get("closed_at"))
            synced_count += 1

        await self.session.flush()
        return synced_count

    async def create_manual_purchase(
        self,
        *,
        user_id: int,
        external_deal_id: str,
        item_name: str,
        gift_number: str | None,
        gift_url: str | None,
        marketplace: str | None,
        buy_price: Decimal,
        currency: Currency,
        ton_usd_rate: Decimal | None,
        opened_at: datetime,
    ) -> Deal:
        """Create a manually captured purchase deal."""

        deal = Deal(
            user_id=user_id,
            external_deal_id=external_deal_id,
            item_name=item_name,
            gift_number=gift_number,
            gift_url=gift_url,
            marketplace=marketplace,
            sale_marketplace=None,
            category=None,
            buy_price=buy_price,
            sell_price=None,
            fee=Decimal("0"),
            net_profit=None,
            ton_usd_rate=ton_usd_rate,
            sale_ton_usd_rate=None,
            currency=currency,
            status=DealStatus.OPEN,
            opened_at=opened_at,
            closed_at=None,
        )
        return await self.add(deal)


def _to_decimal(value: Any, default: str) -> Decimal:
    """Convert a value to Decimal with a fallback."""

    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value))


def _to_nullable_decimal(value: Any) -> Decimal | None:
    """Convert a value to nullable Decimal."""

    if value in (None, ""):
        return None
    return Decimal(str(value))


def _to_datetime(value: Any) -> datetime | None:
    """Convert ISO strings to datetime objects."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _to_currency(value: Any) -> Currency:
    """Convert a raw value to Currency enum."""

    try:
        return Currency(str(value))
    except ValueError:
        return Currency.USD


def _to_status(value: Any) -> DealStatus:
    """Convert a raw value to DealStatus enum."""

    try:
        return DealStatus(str(value))
    except ValueError:
        return DealStatus.OPEN


def _nullable_str(value: Any) -> str | None:
    """Convert a value to a nullable string."""

    if value in (None, ""):
        return None
    return str(value)
