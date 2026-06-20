"""Tests for COGS Sheets exporter."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from ozon_agent.cogs.models import CogsRecord
from ozon_agent.sheets.exporters.cogs import _empty_df, _load_from_files


def test_cogs_empty_df() -> None:
    df = _empty_df()
    assert len(df) == 0
    assert "sku" in df.columns
    assert "unit_cost" in df.columns
    assert "status" in df.columns


def test_cogs_load_from_files_empty() -> None:
    with patch("ozon_agent.cogs.repository.list_records", return_value=[]):
        result = _load_from_files()
        assert result is None


def test_cogs_load_from_files_with_data() -> None:
    records = [
        CogsRecord(
            id="1", sku="SKU-1", unit_cost=550, source="manual",
            updated_at=datetime(2026, 6, 20, tzinfo=UTC),
        ),
    ]
    with patch("ozon_agent.cogs.repository.list_records", return_value=records):
        result = _load_from_files()
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["sku"] == "SKU-1"
        assert result.iloc[0]["unit_cost"] == 550
        assert result.iloc[0]["status"] == "OK"


def test_setup_has_cogs_tab() -> None:
    from ozon_agent.sheets.setup import TABS
    names = [t["name"] for t in TABS]
    assert "COGS" in names


def test_sync_has_cogs_exporter() -> None:
    from ozon_agent.sheets.sync import TAB_EXPORTERS
    assert "COGS" in TAB_EXPORTERS
