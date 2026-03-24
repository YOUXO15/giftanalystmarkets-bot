"""Tests for mock GiftSatellite data generation."""

from __future__ import annotations

from src.integrations.giftsatellite_client import _build_mock_deals


def test_mock_deals_are_stable_for_same_user() -> None:
    first = _build_mock_deals(telegram_id=123456, count=6)
    second = _build_mock_deals(telegram_id=123456, count=6)

    assert first == second


def test_mock_deals_differ_between_users() -> None:
    first_user = _build_mock_deals(telegram_id=111111, count=6)
    second_user = _build_mock_deals(telegram_id=222222, count=6)

    first_snapshot = [
        (deal["item_name"], deal["buy_price"], deal["currency"], deal["status"])
        for deal in first_user
    ]
    second_snapshot = [
        (deal["item_name"], deal["buy_price"], deal["currency"], deal["status"])
        for deal in second_user
    ]

    assert first_snapshot != second_snapshot
