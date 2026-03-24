"""HTTP client for the legacy external market sync integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Any

import httpx

from src.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GiftAnalystMarketsSyncPayload:
    """Represents the result of an external market sync request."""

    items: list[dict[str, Any]]
    success: bool
    is_configured: bool
    message: str


class GiftAnalystMarketsClient:
    """Small HTTP client wrapper around the legacy sync endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.gift_analyst_markets_base_url.rstrip("/")
        self._api_key = settings.gift_analyst_markets_api_key_value
        self._timeout = settings.http_timeout_seconds
        self._use_mock_data = settings.gift_analyst_markets_use_mock_data
        self._mock_deals_count = max(1, min(settings.gift_analyst_markets_mock_deals_count, 20))

    async def fetch_user_deals(self, telegram_id: int) -> GiftAnalystMarketsSyncPayload:
        """Fetch deals for a Telegram user from the legacy sync source."""

        if self._use_mock_data:
            items = _build_mock_deals(telegram_id=telegram_id, count=self._mock_deals_count)
            return GiftAnalystMarketsSyncPayload(
                items=items,
                success=True,
                is_configured=True,
                message=(
                    "Синхронизация выполнена в тестовом режиме. "
                    f"Подготовлено {len(items)} демонстрационных сделок."
                ),
            )

        if not self._base_url or not self._api_key:
            return GiftAnalystMarketsSyncPayload(
                items=[],
                success=False,
                is_configured=False,
                message=(
                    "Интеграция внешнего market sync еще не настроена. "
                    "Заполни GIFT_ANALYST_MARKETS_BASE_URL и GIFT_ANALYST_MARKETS_API_KEY "
                    "или включи GIFT_ANALYST_MARKETS_USE_MOCK_DATA=true для демо-режима."
                ),
            )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            ) as client:
                response = await client.get("/api/v1/deals", params={"telegram_id": telegram_id})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("GiftAnalystMarkets sync request failed")
            return GiftAnalystMarketsSyncPayload(
                items=[],
                success=False,
                is_configured=True,
                message=f"GiftAnalystMarkets sync API вернул ошибку: {exc}",
            )

        items = _extract_items(response.json())
        return GiftAnalystMarketsSyncPayload(
            items=items,
            success=True,
            is_configured=True,
            message=f"Получено {len(items)} сделок из GiftAnalystMarkets sync.",
        )


# Backward-compatible aliases for old imports.
GiftSatelliteSyncPayload = GiftAnalystMarketsSyncPayload
GiftSatelliteClient = GiftAnalystMarketsClient


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    """Extract a list of deal dictionaries from a flexible API payload."""

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "results", "data", "deals"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _build_mock_deals(telegram_id: int, count: int) -> list[dict[str, Any]]:
    """Build a deterministic demo dataset for local bot testing."""

    rng = random.Random(telegram_id)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    categories = [
        "Gift Box",
        "Stickers",
        "Emoji",
        "Avatar",
        "Badge",
        "Collectible",
    ]
    adjectives = ["Rare", "Limited", "Premium", "Collector", "Seasonal", "Legendary"]
    subjects = ["Gift Box", "Sticker Pack", "Emoji Set", "Avatar Skin", "Badge", "Ticket"]
    currencies = ["USD", "EUR", "USDT", "TON"]
    statuses = ["open", "closed", "closed", "closed", "cancelled"]

    items: list[dict[str, Any]] = []
    for index in range(count):
        category = rng.choice(categories)
        item_name = f"{rng.choice(adjectives)} {rng.choice(subjects)}"
        currency = rng.choice(currencies)
        status = rng.choice(statuses)

        buy_price = _quantize_money(Decimal(str(rng.uniform(18, 260))))
        opened_days_ago = rng.randint(3, 90)
        opened_at = now - timedelta(days=opened_days_ago, hours=rng.randint(0, 23))

        sell_price: Decimal | None = None
        fee: Decimal = Decimal("0")
        net_profit: Decimal | None = None
        closed_at: datetime | None = None

        if status == "closed":
            multiplier = Decimal(str(rng.uniform(0.82, 1.65)))
            sell_price = _quantize_money(buy_price * multiplier)
            fee = _quantize_money(sell_price * Decimal(str(rng.uniform(0.01, 0.08))))
            net_profit = _quantize_money(sell_price - buy_price - fee)
            holding_days = rng.randint(1, 25)
            closed_at = opened_at + timedelta(days=holding_days, hours=rng.randint(0, 23))
        elif status == "cancelled":
            fee = _quantize_money(buy_price * Decimal(str(rng.uniform(0.0, 0.02))))
            net_profit = _quantize_money(-(fee))
            holding_days = rng.randint(0, 10)
            closed_at = opened_at + timedelta(days=holding_days, hours=rng.randint(0, 23))

        items.append(
            {
                "external_deal_id": f"mock-{telegram_id}-{index + 1:03d}",
                "item_name": item_name,
                "category": category,
                "buy_price": str(buy_price),
                "sell_price": str(sell_price) if sell_price is not None else None,
                "fee": str(fee),
                "net_profit": str(net_profit) if net_profit is not None else None,
                "currency": currency,
                "status": status,
                "opened_at": opened_at.isoformat(),
                "closed_at": closed_at.isoformat() if closed_at is not None else None,
            }
        )

    return items


def _quantize_money(value: Decimal) -> Decimal:
    """Normalize decimal values to 2 fraction digits."""

    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
