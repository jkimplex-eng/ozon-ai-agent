"""Tests for COGS service."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

from ozon_agent.cogs.coverage import calculate_coverage, format_coverage_report
from ozon_agent.cogs.models import CogsCoverageReport
from ozon_agent.cogs.repository import override_connection_factory
from ozon_agent.cogs.service import get_cogs, list_cogs, set_cogs


@contextmanager
def fake_service() -> Any:
    storage: dict[str, list[dict[str, Any]]] = {"cogs": []}

    class _FakeCursor:
        def __init__(self) -> None:
            self.description: list[str] | None = None
            self._rows: list[dict[str, Any]] = []

        def __enter__(self) -> _FakeCursor:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, sql: str, params: Any) -> None:
            if "INSERT INTO cogs" in sql:
                existing = [r for r in storage["cogs"] if r["sku"] != params["sku"]]
                storage["cogs"] = existing + [dict(params)]
                self._rows = []
            elif "SELECT * FROM cogs WHERE sku" in sql:
                sku_val = list(params.values())[0] if params else ""
                self._rows = [
                    dict(r) for r in storage["cogs"] if r["sku"] == sku_val
                ]
                self.description = ["id"]
            elif "SELECT * FROM cogs ORDER BY sku" in sql:
                self._rows = sorted(
                    [dict(r) for r in storage["cogs"]],
                    key=lambda r: r.get("sku", ""),
                )
                self.description = ["id"]
            elif "DELETE FROM cogs WHERE sku" in sql:
                sku_val = list(params.values())[0] if params else ""
                storage["cogs"] = [
                    r for r in storage["cogs"] if r["sku"] != sku_val
                ]
                self._rows = []
            elif "DELETE FROM cogs" in sql:
                storage["cogs"] = []
                self._rows = []

        def fetchall(self) -> list[dict[str, Any]]:
            return self._rows

    class _FakeConnection:
        def __enter__(self) -> _FakeConnection:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def cursor(self) -> _FakeCursor:
            return _FakeCursor()

        def commit(self) -> None:
            return None

    @contextmanager
    def _factory() -> Any:
        yield _FakeConnection()

    with override_connection_factory(_factory):
        yield storage


def test_set_and_get_cogs() -> None:
    with fake_service():
        record = set_cogs("SKU-1", 550)
        assert record.unit_cost == 550
        assert get_cogs("SKU-1") == 550


def test_set_cogs_invalid_cost() -> None:
    with pytest.raises(ValueError, match="negative"):
        set_cogs("SKU-1", -100)


def test_set_cogs_zero_cost() -> None:
    with pytest.raises(ValueError, match="positive"):
        set_cogs("SKU-1", 0)


def test_set_cogs_string_cost() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        set_cogs("SKU-1", "abc")


def test_list_cogs_empty() -> None:
    with fake_service():
        assert list_cogs() == []


def test_coverage_calculation() -> None:
    with fake_service():
        set_cogs("SKU-1", 550)
        products = [
            {"sku": "SKU-1", "name": "P1"},
            {"sku": "SKU-2", "name": "P2"},
            {"sku": "SKU-3", "name": "P3"},
        ]
        report = calculate_coverage(products)
        assert report.total_products == 3
        assert report.with_cogs == 1
        assert report.without_cogs == 2
        assert report.coverage_pct == 33.3


def test_format_coverage_report() -> None:
    report = CogsCoverageReport(
        total_products=100,
        with_cogs=84,
        without_cogs=16,
        coverage_pct=84.0,
        missing_skus=["SKU-1", "SKU-2"],
    )
    text = format_coverage_report(report)
    assert "84.0%" in text
    assert "84" in text
    assert "SKU-1" in text
