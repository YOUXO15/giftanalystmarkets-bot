"""Async client for the Crypto Pay API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from src.config.settings import Settings
from src.utils.enums import Currency, PaymentInvoiceStatus

logger = logging.getLogger(__name__)


class CryptoPayApiError(RuntimeError):
    """Raised when Crypto Pay API returns an error or invalid payload."""


@dataclass(slots=True)
class CryptoPayInvoice:
    """Normalized invoice payload returned by Crypto Pay."""

    invoice_id: int
    invoice_hash: str
    asset: Currency | None
    amount: Decimal
    status: PaymentInvoiceStatus
    bot_invoice_url: str
    description: str | None
    payload: str | None
    expires_at: datetime | None
    paid_at: datetime | None


class CryptoPayClient:
    """Minimal async wrapper around Crypto Pay API methods used by the bot."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = self._normalize_base_url(settings.crypto_pay_base_url)
        self._timeout = settings.http_timeout_seconds

    async def create_invoice(
        self,
        *,
        amount: Decimal,
        asset: Currency,
        description: str,
        payload: str,
    ) -> CryptoPayInvoice:
        """Create a Crypto Pay invoice for a bot subscription."""

        result = await self._request(
            "POST",
            "createInvoice",
            json_payload={
                "currency_type": "crypto",
                "asset": asset.value,
                "amount": self._format_decimal(amount),
                "description": description,
                "hidden_message": (
                    "Спасибо за оплату. Вернись в GiftAnalystMarkets "
                    "и нажми «Проверить оплату»."
                ),
                "payload": payload,
                "allow_comments": False,
                "expires_in": self._settings.crypto_pay_invoice_expires_in,
            },
        )
        return self._parse_invoice(result)

    async def get_invoice(self, invoice_id: int) -> CryptoPayInvoice | None:
        """Fetch a single invoice by its provider-side identifier."""

        result = await self._request(
            "GET",
            "getInvoices",
            params={"invoice_ids": str(invoice_id), "count": 1},
        )
        if isinstance(result, dict):
            items = result.get("items")
        else:
            items = result
        if not isinstance(items, list):
            raise CryptoPayApiError("Unexpected getInvoices response payload.")
        if not items:
            return None
        return self._parse_invoice(items[0])

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an authenticated Crypto Pay request."""

        token = self._settings.crypto_pay_api_token_value
        if not token:
            raise CryptoPayApiError("Crypto Pay token is not configured.")

        headers = {
            "Crypto-Pay-API-Token": token,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
        ) as client:
            try:
                response = await client.request(method, path, params=params, json=json_payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise CryptoPayApiError(f"HTTP error while calling Crypto Pay: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise CryptoPayApiError("Crypto Pay returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise CryptoPayApiError("Crypto Pay returned a non-object response.")
        if payload.get("ok") is not True:
            error_code = payload.get("error", "UNKNOWN_ERROR")
            raise CryptoPayApiError(f"Crypto Pay returned an error: {error_code}")
        return payload.get("result")

    def _parse_invoice(self, data: Any) -> CryptoPayInvoice:
        """Convert raw Crypto Pay invoice payload into a typed dataclass."""

        if not isinstance(data, dict):
            raise CryptoPayApiError("Crypto Pay invoice payload is malformed.")

        status_value = str(data.get("status", "")).lower()
        try:
            status = PaymentInvoiceStatus(status_value)
        except ValueError as exc:
            raise CryptoPayApiError(f"Unsupported invoice status: {status_value}") from exc

        asset_raw = data.get("asset")
        asset = None
        if isinstance(asset_raw, str):
            try:
                asset = Currency(asset_raw.upper())
            except ValueError:
                logger.warning("Unknown Crypto Pay asset received: %s", asset_raw)

        return CryptoPayInvoice(
            invoice_id=int(data["invoice_id"]),
            invoice_hash=str(data["hash"]),
            asset=asset,
            amount=Decimal(str(data["amount"])),
            status=status,
            bot_invoice_url=str(data["bot_invoice_url"]),
            description=self._as_optional_str(data.get("description")),
            payload=self._as_optional_str(data.get("payload")),
            expires_at=self._parse_datetime(data.get("expiration_date")),
            paid_at=self._parse_datetime(data.get("paid_at")),
        )

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        """Normalize the configured API base URL."""

        normalized = base_url.rstrip("/")
        if normalized.endswith("/api"):
            return f"{normalized}/"
        return f"{normalized}/api/"

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        """Serialize Decimal into the string format expected by Crypto Pay."""

        return format(value.normalize(), "f")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse ISO 8601 datetime strings returned by the API."""

        if not isinstance(value, str) or not value:
            return None
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        """Convert payload fields into strings when present."""

        if value is None:
            return None
        text = str(value).strip()
        return text or None
