"""Tests for manual trade capture parsing."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from pydantic import SecretStr

from src.config.settings import Settings
from src.services.trade_capture_service import (
    TradeCaptureService,
    _extract_name_and_number_from_html,
)
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


def test_parse_purchase_input_extracts_marketplace_and_price_from_notification() -> None:
    service = _build_service()

    payload = asyncio.run(
        service.parse_purchase_input(
            "Bought Bow Tie #31151 for 4.9522 TON\nMarket: PORTALS",
            source_label="market_bot",
        )
    )

    assert payload is not None
    assert payload.gift.item_name == "Bow Tie"
    assert payload.gift.gift_number == "31151"
    assert payload.gift.marketplace == "PORTALS"
    assert payload.price is not None
    assert payload.price.amount == Decimal("4.9522")
    assert payload.price.currency == Currency.TON


def test_should_request_manual_marketplace_for_link_only_purchase() -> None:
    service = _build_service()

    assert service.should_request_manual_marketplace(
        raw_text="https://t.me/nft/MoonPendant-150",
        source_label=None,
        gift_url="https://t.me/nft/MoonPendant-150",
        marketplace="TELEGRAM",
    )


def test_parse_marketplace_input_normalizes_alias() -> None:
    service = _build_service()

    assert service.parse_marketplace_input("portal marketplace") == "PORTALS"


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


def test_parse_sale_notification_draft_allows_missing_amount() -> None:
    service = _build_service()

    payload = service.parse_sale_notification_draft(
        "Bow Tie #31152 has been sold",
        source_label="fragment_bot",
    )

    assert payload is not None
    assert payload.item_name == "Bow Tie"
    assert payload.gift_number == "31152"
    assert payload.amount is None
    assert payload.currency is None
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


def test_parse_gift_link_keeps_number_from_telegram_url() -> None:
    service = _build_service()

    payload = service.parse_gift_link("https://t.me/nft/MoonPendant-150")

    assert payload is not None
    assert payload.item_name == "MoonPendant"
    assert payload.gift_number == "150"
    assert payload.marketplace == "TELEGRAM"


def test_parse_purchase_input_keeps_url_number_when_metadata_unavailable() -> None:
    service = _build_service()

    async def _fake_fetch_page_html(url: str) -> str | None:
        return None

    service._fetch_page_html = _fake_fetch_page_html  # type: ignore[method-assign]

    payload = asyncio.run(service.parse_purchase_input("https://t.me/nft/MoonPendant-150"))

    assert payload is not None
    assert payload.gift.item_name == "MoonPendant"
    assert payload.gift.gift_number == "150"


def test_extract_name_and_number_from_html_uses_preview_title() -> None:
    html = '<meta property="og:title" content="Spring Basket #74760" />'

    name, number = _extract_name_and_number_from_html(html)

    assert name == "Spring Basket"
    assert number == "74760"
