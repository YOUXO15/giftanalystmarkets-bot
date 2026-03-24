"""HTTP client for future TON API integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from src.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TonRatePayload:
    """Represents TON rate lookup result."""

    rate: Decimal | None
    source: str
    success: bool
    message: str


class TonClient:
    """Small HTTP client wrapper around TON market data API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ton_api_base_url.rstrip("/")
        self._api_key = settings.ton_api_key_value
        self._timeout = settings.http_timeout_seconds
        self._coingecko_base_url = "https://api.coingecko.com/api/v3"

    async def get_current_rate(self) -> TonRatePayload:
        """Fetch the current TON/USD exchange rate."""

        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            ) as client:
                response = await client.get("/v2/rates", params={"tokens": "ton", "currencies": "usd"})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("TON API request failed")
            return TonRatePayload(
                rate=None,
                source="tonapi",
                success=False,
                message=f"Не удалось получить курс TON: {exc}",
            )

        rate = _extract_rate(response.json())
        if rate is None:
            return TonRatePayload(
                rate=None,
                source="tonapi",
                success=False,
                message="TON API ответил, но курс не удалось распарсить.",
            )

        return TonRatePayload(
            rate=rate,
            source="tonapi",
            success=True,
            message="Курс TON успешно обновлён.",
        )

    async def get_rate_for_date(self, target_date: date) -> TonRatePayload:
        """Fetch historical TON/USD rate for a specific calendar date."""

        try:
            async with httpx.AsyncClient(
                base_url=self._coingecko_base_url,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            ) as client:
                response = await client.get(
                    "/coins/the-open-network/history",
                    params={
                        "date": target_date.strftime("%d-%m-%Y"),
                        "localization": "false",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Historical TON rate request failed for %s", target_date.isoformat())
            return TonRatePayload(
                rate=None,
                source=f"coingecko:{target_date.isoformat()}",
                success=False,
                message=f"Не удалось получить курс TON за {target_date.strftime('%d.%m.%Y')}: {exc}",
            )

        rate = _extract_history_rate(response.json())
        if rate is None:
            return TonRatePayload(
                rate=None,
                source=f"coingecko:{target_date.isoformat()}",
                success=False,
                message=(
                    f"CoinGecko ответил за {target_date.strftime('%d.%m.%Y')}, "
                    "но курс TON/USD не удалось распарсить."
                ),
            )

        return TonRatePayload(
            rate=rate,
            source=f"coingecko:{target_date.isoformat()}",
            success=True,
            message=f"Курс TON за {target_date.strftime('%d.%m.%Y')} успешно получен.",
        )


def _extract_rate(payload: Any) -> Decimal | None:
    """Extract TON/USD rate from different response shapes."""

    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("rates", {}).get("TON", {}).get("prices", {}).get("USD"),
        payload.get("rates", {}).get("TON", {}).get("USD"),
        payload.get("rate"),
        payload.get("price", {}).get("USD") if isinstance(payload.get("price"), dict) else None,
    ]

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return Decimal(str(candidate))
        except Exception:
            continue

    return None


def _extract_history_rate(payload: Any) -> Decimal | None:
    """Extract historical TON/USD rate from CoinGecko history response."""

    if not isinstance(payload, dict):
        return None

    market_data = payload.get("market_data")
    if not isinstance(market_data, dict):
        return None

    current_price = market_data.get("current_price")
    if not isinstance(current_price, dict):
        return None

    usd_price = current_price.get("usd")
    if usd_price is None:
        return None

    try:
        return Decimal(str(usd_price))
    except Exception:
        return None
