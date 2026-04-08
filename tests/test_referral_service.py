"""Tests for referral percentage and deep-link parsing logic."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from src.services.referral_service import ReferralService


def _build_service() -> ReferralService:
    settings_stub = SimpleNamespace(
        subscription_period_days=30,
        subscription_monthly_price_ton=Decimal("3"),
        referral_base_percent=Decimal("10"),
        referral_percent_after_level_1=Decimal("5"),
        referral_percent_after_level_2=Decimal("13"),
        referral_percent_after_level_3=Decimal("15"),
        referral_level_1_threshold=3,
        referral_level_2_threshold=10,
        referral_level_3_threshold=25,
        referral_withdraw_min_ton=Decimal("1"),
        bot_username="Gift_Analyst_Markets_Robot",
    )
    return ReferralService(None, settings_stub)  # type: ignore[arg-type]


def test_referral_percent_progression() -> None:
    service = _build_service()

    assert service._calculate_referral_percent(0) == Decimal("10")
    assert service._calculate_referral_percent(2) == Decimal("10")
    assert service._calculate_referral_percent(3) == Decimal("5")
    assert service._calculate_referral_percent(10) == Decimal("13")
    assert service._calculate_referral_percent(25) == Decimal("15")


def test_next_level_threshold() -> None:
    service = _build_service()

    assert service._next_level_threshold(0) == 3
    assert service._next_level_threshold(3) == 10
    assert service._next_level_threshold(10) == 25
    assert service._next_level_threshold(25) is None


def test_extract_referral_code_from_deep_link() -> None:
    service = _build_service()

    assert service._extract_referral_code("ref_gamabcd12") == "gamabcd12"
    assert service._extract_referral_code("GamAbCd12") == "gamabcd12"
    assert service._extract_referral_code("bad payload!") is None
