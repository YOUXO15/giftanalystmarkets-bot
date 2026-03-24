"""Tests for manual trade capture parsing."""

from __future__ import annotations

from decimal import Decimal

from pydantic import SecretStr

from src.config.settings import Settings
from src.services.trade_capture_service import TradeCaptureService
from src.utils.enums import Currency


def _build_service() -> TradeCaptureService:
    settings = Settings.model_construct(
        bot_token=SecretStr("token"),
        database_url="postgresql://user:pass@localhost:5432/db",
        ton_api_base_url="https://tonapi.io",
        ton_api_key=None,
        http_timeout_seconds=15.0,
    )
    return TradeCaptureService(None, settings)  # type: ignore[arg-type]


def test_parse_gift_link_extracts_name_number_and_marketplace() -> None:
    service = _build_service()

    payload = service.parse_gift_link("https://portals.market/gifts/Bow-Tie-31151")

    assert payload is not None
    assert payload.item_name == "Bow Tie"
    assert payload.gift_number == "31151"
    assert payload.marketplace == "PORTALS"


def test_parse_purchase_price_defaults_to_ton() -> None:
    service = _build_service()

    payload = service.parse_purchase_price("4.9522")

    assert payload is not None
    assert str(payload.amount) == "4.9522"
    assert payload.currency == Currency.TON


def test_parse_sale_notification_extracts_amount_and_identity() -> None:
    service = _build_service()

    payload = service.parse_sale_notification(
        "Bow Tie #31151 has been sold\nYou received: 31.35 TON",
        source_label="portals_bot",
    )

    assert payload is not None
    assert payload.item_name == "Bow Tie"
    assert payload.gift_number == "31151"
    assert payload.amount == Decimal("31.35")
    assert payload.currency == Currency.TON
    assert payload.marketplace == "PORTALS"


def test_parse_sale_notification_accepts_received_line_without_sold_hint() -> None:
    service = _build_service()

    payload = service.parse_sale_notification(
        "Bow Tie #31152\nYou received: 57 TON",
        source_label="fragment_bot",
    )

    assert payload is not None
    assert payload.item_name == "Bow Tie"
    assert payload.gift_number == "31152"
    assert payload.amount == Decimal("57")
    assert payload.currency == Currency.TON
    assert payload.marketplace == "FRAGMENT"


def test_parse_sale_fee_uses_notification_currency_by_default() -> None:
    service = _build_service()

    payload = service.parse_sale_fee("0.75", default_currency=Currency.TON)

    assert payload is not None
    assert payload.amount == Decimal("0.75")
    assert payload.currency == Currency.TON


def test_parse_sale_fee_accepts_explicit_currency() -> None:
    service = _build_service()

    payload = service.parse_sale_fee("1.25 USDT", default_currency=Currency.TON)

    assert payload is not None
    assert payload.amount == Decimal("1.25")
    assert payload.currency == Currency.USDT


def test_parse_gift_link_normalizes_url_noise() -> None:
    service = _build_service()

    payload = service.parse_gift_link("https://T.ME/nft/Bow-Tie-31151/?startapp=gift#section")

    assert payload is not None
    assert payload.gift_url == "https://t.me/nft/Bow-Tie-31151?startapp=gift"
