"""Tests for Performance Stats Google Sheets export."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ozon_agent.sheets.exporters.performance_stats import EXPORT_COLS, _load_from_files
from ozon_agent.sheets.file_source import load_performance_stats
from ozon_agent.sheets.setup import TABS
from ozon_agent.sheets.sync import TAB_EXPORTERS


def _write_stats_file(
    root: Path,
    filename: str,
    rows: list[dict[str, Any]],
    *,
    mtime: int,
) -> Path:
    stats_dir = root / "data" / "performance" / "normalized" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)
    path = stats_dir / filename
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_performance_stats_no_files_returns_no_data(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)

    df = _load_from_files()

    assert list(df.columns) == EXPORT_COLS
    assert len(df) == 1
    assert df.iloc[0]["date"] == "NO DATA"


def test_performance_stats_one_file_exports_rows(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_stats_file(
        tmp_path,
        "stats.json",
        [{
            "date": "2026-06-17",
            "campaign_id": "29645639",
            "campaign_name": "Campaign",
            "sku": "4536601352",
            "product_name": "Product",
            "impressions": 591,
            "clicks": 13,
            "ctr": 2.2,
            "add_to_cart": 0,
            "cpc": 48.13,
            "spend": 625.65,
            "orders": 0,
            "revenue": 0,
            "model_orders": 0,
            "model_revenue": 0,
            "drr": 0,
            "ordered_amount": 0,
            "total_drr": 0,
            "added_at": "17.06.2026",
        }],
        mtime=10,
    )

    rows = load_performance_stats()
    df = _load_from_files()

    assert len(rows) == 1
    assert len(df) == 1
    assert df.iloc[0]["campaign_id"] == "29645639"
    assert df.iloc[0]["drr_promo"] == 0
    assert df.iloc[0]["drr_total"] == 0
    assert df.iloc[0]["raw_date_added"] == "17.06.2026"


def test_performance_stats_selects_latest_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_stats_file(tmp_path, "old.json", [{"sku": "old"}], mtime=10)
    _write_stats_file(tmp_path, "new.json", [{"sku": "new"}], mtime=20)

    df = _load_from_files()

    assert len(df) == 1
    assert df.iloc[0]["sku"] == "new"


def test_performance_stats_missing_optional_fields_are_empty(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_stats_file(
        tmp_path,
        "partial.json",
        [{"date": "2026-06-17", "campaign_id": "1", "sku": "sku-1"}],
        mtime=10,
    )

    df = _load_from_files()

    assert list(df.columns) == EXPORT_COLS
    assert df.iloc[0]["campaign_name"] == ""
    assert df.iloc[0]["spend"] == ""
    assert df.iloc[0]["raw_date_added"] == ""


def test_performance_stats_registered_in_sheets_sync() -> None:
    assert "Performance Stats" in TAB_EXPORTERS

    tab_names = [tab["name"] for tab in TABS]
    assert "Performance Stats" in tab_names
