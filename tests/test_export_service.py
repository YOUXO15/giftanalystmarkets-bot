"""Tests for local export file generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from src.services.export_service import ExportService
from src.utils.enums import Currency, DealStatus


@dataclass
class FakeDeal:
    """Minimal fake deal object for export tests."""

    external_deal_id: str
    item_name: str
    gift_number: str | None
    gift_url: str | None
    marketplace: str | None
    category: str | None
    buy_price: Decimal
    sell_price: Decimal | None
    fee: Decimal
    net_profit: Decimal | None
    ton_usd_rate: Decimal | None
    currency: Currency
    status: DealStatus
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _build_fake_deal() -> FakeDeal:
    """Create a deterministic fake deal."""

    return FakeDeal(
        external_deal_id="mock-1",
        item_name="Rare Gift Box",
        gift_number="31151",
        gift_url="https://t.me/nft/rare-gift-box-31151",
        marketplace="PORTALS",
        category="Gift Box",
        buy_price=Decimal("120.00"),
        sell_price=Decimal("179.00"),
        fee=Decimal("9.50"),
        net_profit=Decimal("49.50"),
        ton_usd_rate=Decimal("3.21"),
        currency=Currency.USD,
        status=DealStatus.CLOSED,
        opened_at=datetime(2026, 3, 1, 12, 0, 0),
        closed_at=datetime(2026, 3, 5, 15, 30, 0),
        created_at=datetime(2026, 3, 1, 12, 0, 0),
        updated_at=datetime(2026, 3, 5, 15, 30, 0),
    )


def _build_ton_fake_deal(*, ton_usd_rate: Decimal | None = Decimal("3.21")) -> FakeDeal:
    """Create a deal in TON to verify conversion in export."""

    return FakeDeal(
        external_deal_id="mock-ton-1",
        item_name="TON Deal",
        gift_number="70001",
        gift_url="https://t.me/nft/ton-deal-70001",
        marketplace="TELEGRAM",
        category="Collectible",
        buy_price=Decimal("10.00"),
        sell_price=Decimal("20.00"),
        fee=Decimal("1.00"),
        net_profit=Decimal("9.00"),
        ton_usd_rate=ton_usd_rate,
        currency=Currency.TON,
        status=DealStatus.CLOSED,
        opened_at=datetime(2026, 3, 1, 12, 0, 0),
        closed_at=datetime(2026, 3, 5, 15, 30, 0),
        created_at=datetime(2026, 3, 1, 12, 0, 0),
        updated_at=datetime(2026, 3, 5, 15, 30, 0),
    )


def test_build_csv_content_contains_manual_tracking_columns() -> None:
    service = ExportService(None)  # type: ignore[arg-type]
    rows = service._build_export_rows([_build_fake_deal()], Decimal("3.21"))

    content = service._build_csv_content(rows).decode("utf-8-sig")

    assert "ID сделки" in content
    assert "Rare Gift Box" in content
    assert "31151" in content
    assert "PORTALS" in content
    assert "Ссылка на подарок" in content
    assert "https://t.me/nft/rare-gift-box-31151" in content
    assert "Маржа (%)" in content
    assert "41.25%" in content
    assert "Курс TON (USD)" in content
    assert "3.21" in content


def test_build_xlsx_content_creates_valid_workbook_with_new_columns() -> None:
    service = ExportService(None)  # type: ignore[arg-type]
    rows = service._build_export_rows([_build_fake_deal()], Decimal("3.21"))

    content = service._build_xlsx_content(rows)
    workbook = load_workbook(BytesIO(content))
    worksheet = workbook["Сделки"]

    assert worksheet["A1"].value == "ID сделки"
    assert worksheet["A2"].value == "mock-1"
    assert worksheet["B2"].value == "Rare Gift Box"
    assert worksheet["C1"].value == "Номер"
    assert worksheet["C2"].value == "31151"
    assert worksheet["D1"].value == "Маркет"
    assert worksheet["D2"].value == "PORTALS"
    assert worksheet["I1"].value == "Маржа (%)"
    assert worksheet["I2"].value == "41.25%"
    assert worksheet["K1"].value == "Курс TON (USD)"
    assert worksheet["K2"].value == "3.21"
    assert worksheet["Q1"].value == "Ссылка на подарок"


def test_build_rows_converts_values_using_deal_specific_ton_rate() -> None:
    service = ExportService(None)  # type: ignore[arg-type]
    rows = service._build_export_rows(
        [_build_ton_fake_deal()],
        None,
        selected_fields=["buy", "sell", "fee", "profit", "currency"],
        report_currency="RUB",
    )

    assert rows[0] == [
        "Цена покупки (RUB)",
        "Цена продажи (RUB)",
        "Комиссия (RUB)",
        "Чистая прибыль (RUB)",
        "Валюта отчета",
    ]
    assert rows[1] == ["2918.18", "5836.36", "291.82", "2626.36", "RUB"]


def test_build_rows_without_any_ton_rate_marks_amounts_unavailable() -> None:
    service = ExportService(None)  # type: ignore[arg-type]
    rows = service._build_export_rows(
        [_build_ton_fake_deal(ton_usd_rate=None)],
        None,
        selected_fields=["buy", "profit", "margin", "currency"],
        report_currency="RUB",
    )

    assert rows[1][0] == "—"
    assert rows[1][1] == "—"
    assert rows[1][2] == "90.00%"
    assert rows[1][3] == "RUB"


def test_build_full_export_rows_uses_manual_deal_schema() -> None:
    service = ExportService(None)  # type: ignore[arg-type]
    rows = service.build_full_export_rows([_build_fake_deal()], Decimal("3.21"))

    assert rows[0] == [
        "ID сделки",
        "Предмет",
        "Номер",
        "Маркет",
        "Цена покупки",
        "Цена продажи",
        "Комиссия",
        "Чистая прибыль",
        "Маржа (%)",
        "Валюта",
        "Курс TON (USD)",
        "Статус",
        "Дата открытия",
        "Дата закрытия",
        "Добавлено в бота",
        "Обновлено в боте",
        "Ссылка на подарок",
    ]
    assert rows[1][0] == "mock-1"
    assert rows[1][2] == "31151"
    assert rows[1][3] == "PORTALS"
    assert rows[1][9] == "USD"
