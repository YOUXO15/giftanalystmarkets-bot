"""Tests for subscription pricing and period activation logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.db.models.payment_invoice import PaymentInvoice
from src.db.models.user import User
from src.db.models.user_subscription import UserSubscription
from src.services.billing_service import BillingContext, BillingService
from src.utils.enums import BillingPlanType, Currency, PaymentInvoiceStatus, SubscriptionStatus


def _build_service() -> BillingService:
    settings_stub = SimpleNamespace(
        is_crypto_pay_configured=False,
        subscription_intro_price_ton=Decimal("0.1"),
        subscription_monthly_price_ton=Decimal("3"),
        subscription_period_days=30,
        crypto_pay_asset=Currency.TON,
    )
    return BillingService(None, settings_stub)  # type: ignore[arg-type]


def test_build_quote_uses_discount_for_first_payment() -> None:
    service = _build_service()
    subscription = UserSubscription(
        user_id=1,
        status=SubscriptionStatus.INACTIVE,
        discount_consumed=False,
        first_paid_at=None,
    )

    quote = service._build_quote(subscription)

    assert quote.amount == Decimal("0.1")
    assert quote.plan_type == BillingPlanType.INTRO


def test_build_quote_switches_to_regular_after_first_payment() -> None:
    service = _build_service()
    subscription = UserSubscription(
        user_id=1,
        status=SubscriptionStatus.ACTIVE,
        discount_consumed=True,
        first_paid_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    quote = service._build_quote(subscription)

    assert quote.amount == Decimal("3")
    assert quote.plan_type == BillingPlanType.MONTHLY


def test_activate_subscription_extends_from_current_period_end() -> None:
    service = _build_service()
    current_end = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    subscription = UserSubscription(
        user_id=1,
        status=SubscriptionStatus.ACTIVE,
        current_period_started_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        current_period_ends_at=current_end,
        discount_consumed=True,
        first_paid_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )
    invoice = PaymentInvoice(
        user_id=1,
        provider_invoice_id=101,
        invoice_hash="hash-101",
        asset=Currency.TON,
        amount=Decimal("3"),
        plan_type=BillingPlanType.MONTHLY,
        status=PaymentInvoiceStatus.ACTIVE,
        pay_url="https://pay.example/invoice",
    )
    paid_at = datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc)

    service._activate_subscription(subscription=subscription, invoice=invoice, paid_at=paid_at)

    assert subscription.current_period_started_at == current_end
    assert subscription.current_period_ends_at == current_end + timedelta(days=30)
    assert subscription.last_paid_at == paid_at
    assert subscription.discount_consumed is True
    assert invoice.processed_at is not None


@pytest.mark.asyncio
async def test_create_invoice_returns_overview_for_active_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service()
    now = datetime(2026, 3, 24, 10, 0, tzinfo=timezone.utc)
    context = BillingContext(
        user=User(id=1, telegram_id=1001, first_name="Test"),
        subscription=UserSubscription(
            user_id=1,
            status=SubscriptionStatus.ACTIVE,
            current_period_started_at=now - timedelta(days=1),
            current_period_ends_at=now + timedelta(days=20),
            first_paid_at=now - timedelta(days=1),
            last_paid_at=now - timedelta(days=1),
            discount_consumed=True,
        ),
        latest_invoice=None,
    )

    async def fake_load_context(_: int) -> BillingContext:
        return context

    monkeypatch.setattr(service, "_load_context_by_telegram_id", fake_load_context)

    result = await service.create_or_reuse_invoice(1001)

    assert result.success is True
    assert result.reply_to_main_menu is True
    assert "Подписка GiftAnalystMarkets" in result.message


@pytest.mark.asyncio
async def test_refresh_payment_returns_overview_for_active_subscription_without_invoice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service()
    now = datetime(2026, 3, 24, 10, 0, tzinfo=timezone.utc)
    context = BillingContext(
        user=User(id=2, telegram_id=1002, first_name="Test"),
        subscription=UserSubscription(
            user_id=2,
            status=SubscriptionStatus.ACTIVE,
            current_period_started_at=now - timedelta(days=3),
            current_period_ends_at=now + timedelta(days=27),
            first_paid_at=now - timedelta(days=3),
            last_paid_at=now - timedelta(days=3),
            discount_consumed=True,
        ),
        latest_invoice=None,
    )

    async def fake_load_context(_: int) -> BillingContext:
        return context

    monkeypatch.setattr(service, "_load_context_by_telegram_id", fake_load_context)

    result = await service.refresh_payment_status(1002)

    assert result.success is True
    assert result.reply_to_main_menu is True
    assert "Подписка GiftAnalystMarkets" in result.message
