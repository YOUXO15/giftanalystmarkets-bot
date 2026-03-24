"""Tests for parsing custom export parameters."""

from __future__ import annotations

from src.services.export_service import parse_export_query_text
from src.utils.enums import ExportFormat


def test_parse_export_query_text_success() -> None:
    query, export_format, error = parse_export_query_text(
        "format=xlsx;status=closed;currency=USD,TON;profit=positive;days=45;limit=20;fields=id,item,profit,margin,status"
    )

    assert error is None
    assert query is not None
    assert export_format is ExportFormat.XLSX
    assert query.statuses == {"closed"}
    assert query.currencies == {"USD", "TON"}
    assert query.profit_filter == "positive"
    assert query.days == 45
    assert query.limit == 20
    assert query.fields == ["id", "item", "profit", "margin", "status"]


def test_parse_export_query_text_unknown_key() -> None:
    query, export_format, error = parse_export_query_text("foo=bar")

    assert query is None
    assert export_format is None
    assert error is not None
