"""Tests for COGS importer."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from ozon_agent.cogs.importer import import_csv, import_rows, import_text
from ozon_agent.cogs.repository import override_connection_factory


@contextmanager
def fake_importer() -> Any:
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
            if "INSERT" in sql:
                storage["cogs"].append(dict(params))
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


def test_import_csv_basic() -> None:
    with fake_importer() as storage:
        count = import_csv("SKU,UnitCost\n12345,550\n67890,320\n")
        assert count == 2
        assert len(storage["cogs"]) == 2


def test_import_csv_with_logistics() -> None:
    with fake_importer() as storage:
        count = import_csv("SKU,UnitCost,LogisticsCost\n12345,550,50\n")
        assert count == 1
        assert storage["cogs"][0]["logistics_cost"] == 50


def test_import_text_basic() -> None:
    with fake_importer():
        count = import_text("12345 550\n67890 320\n")
        assert count == 2


def test_import_text_with_comments() -> None:
    with fake_importer():
        count = import_text("# Header\n12345 550\n\n67890 320\n")
        assert count == 2


def test_import_rows() -> None:
    with fake_importer() as storage:
        rows = [
            {"sku": "SKU-1", "unit_cost": 550, "product_name": "P1"},
            {"sku": "SKU-2", "unit_cost": 320},
        ]
        count = import_rows(rows)
        assert count == 2
        assert len(storage["cogs"]) == 2
