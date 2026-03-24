"""Tests for TON-based aggregate statistics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.services.stats_service import StatsService
from src.utils.enums import Currency, DealStatus


@dataclass
class FakeDeal:
    """Minimal fake deal object for stats conversion tests."""

    buy_price: Decimal
    net_profit: Decimal | None
    ton_usd_rate: Decimal | None
    currency: Currency
    status: DealStatus
    created_at: datetime
    updated_at: datetime


def test_sum_field_in_ton_converts_mixed_currencies() -> None:
    service = StatsService(None)  # type: ignore[arg-type]
    deals = [
        FakeDeal(
            buy_price=Decimal("10"),
            net_profit=Decimal("2"),
            ton_usd_rate=Decimal("3.10"),
            currency=Currency.TON,
            status=DealStatus.OPEN,
            created_at=datetime(2026, 3, 1, 12, 0, 0),
            updated_at=datetime(2026, 3, 1, 12, 0, 0),
        ),
        FakeDeal(
            buy_price=Decimal("31"),
            net_profit=Decimal("6.2"),
            ton_usd_rate=Decimal("3.10"),
            currency=Currency.USD,
            status=DealStatus.CLOSED,
            created_at=datetime(2026, 3, 2, 12, 0, 0),
            updated_at=datetime(2026, 3, 2, 12, 0, 0),
        ),
    ]

    total_buy = service._sum_field_in_ton(deals, field_name="buy_price", fallback_ton_rate=None)
    total_profit = service._sum_field_in_ton(deals, field_name="net_profit", fallback_ton_rate=None)

    assert total_buy == Decimal("20")
    assert total_profit == Decimal("4")


def test_sum_field_in_ton_uses_fallback_rate_when_deal_snapshot_missing() -> None:
    service = StatsService(None)  # type: ignore[arg-type]
    deals = [
        FakeDeal(
            buy_price=Decimal("62"),
            net_profit=None,
            ton_usd_rate=None,
            currency=Currency.USD,
            status=DealStatus.OPEN,
            created_at=datetime(2026, 3, 1, 12, 0, 0),
            updated_at=datetime(2026, 3, 1, 12, 0, 0),
        ),
    ]

    total_buy = service._sum_field_in_ton(
        deals,
        field_name="buy_price",
        fallback_ton_rate=Decimal("3.10"),
    )

    assert total_buy == Decimal("20")
