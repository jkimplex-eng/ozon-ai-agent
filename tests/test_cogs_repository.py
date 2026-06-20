"""Tests for COGS repository."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from ozon_agent.cogs.models import create_cogs_record
from ozon_agent.cogs.repository import (
    clear_all,
    delete_record,
    get_record,
    list_records,
    override_connection_factory,
    save_record,
)


@contextmanager
def fake_repository() -> Any:
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


def test_save_and_get_record() -> None:
    with fake_repository():
        record = create_cogs_record(sku="SKU-1", unit_cost=550)
        save_record(record)
        loaded = get_record("SKU-1")
        assert loaded is not None
        assert loaded.unit_cost == 550


def test_list_records() -> None:
    with fake_repository():
        save_record(create_cogs_record(sku="SKU-1", unit_cost=100))
        save_record(create_cogs_record(sku="SKU-2", unit_cost=200))
        records = list_records()
        assert len(records) == 2
        assert records[0].sku == "SKU-1"


def test_delete_record() -> None:
    with fake_repository():
        save_record(create_cogs_record(sku="SKU-1", unit_cost=100))
        assert delete_record("SKU-1") is True
        assert get_record("SKU-1") is None


def test_clear_all() -> None:
    with fake_repository() as storage:
        save_record(create_cogs_record(sku="SKU-1", unit_cost=100))
        save_record(create_cogs_record(sku="SKU-2", unit_cost=200))
        assert len(list_records()) == 2
        count = clear_all()
        assert count >= 0
        assert list_records() == []


def test_get_nonexistent() -> None:
    with fake_repository():
        assert get_record("MISSING") is None
