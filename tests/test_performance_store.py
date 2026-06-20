"""Tests for Performance API store."""
from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.performance.models import PerformanceCampaign, PerformanceStatsRow
from ozon_agent.performance.store import (
    list_normalized_stats_files,
    save_normalized_campaigns,
    save_normalized_stats,
    save_raw_campaigns,
    save_raw_stats,
)

AT = "2026-01-01T00:00:00"


def test_save_raw_campaigns(tmp_path: Path):
    campaigns = [PerformanceCampaign(id=1, name="C1", status="ACTIVE")]
    path = save_raw_campaigns(
        campaigns, storage_root=tmp_path, requested_at=AT,
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert "raw" in str(path)
    assert "campaigns" in str(path)


def test_save_normalized_campaigns(tmp_path: Path):
    campaigns = [PerformanceCampaign(id=2, name="C2", status="PAUSED")]
    path = save_normalized_campaigns(
        campaigns, storage_root=tmp_path, requested_at=AT,
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "campaigns" in data
    assert len(data["campaigns"]) == 1
    assert data["campaigns"][0]["name"] == "C2"
    assert "normalized" in str(path)


def test_save_raw_stats(tmp_path: Path):
    csv_text = "col1;col2\na;b\n"
    path = save_raw_stats(
        csv_text,
        storage_root=tmp_path,
        requested_at=AT,
        report_id="abc",
    )
    assert path.exists()
    assert path.read_text(encoding="utf-8") == csv_text
    assert "abc" in path.name
    assert path.suffix == ".csv"


def test_save_normalized_stats(tmp_path: Path):
    rows = [PerformanceStatsRow(
        date="2026-06-17", campaign_id="123", spend=100.5,
    )]
    path = save_normalized_stats(
        rows,
        storage_root=tmp_path,
        requested_at=AT,
        report_id="xyz",
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "rows" in data
    assert len(data["rows"]) == 1
    assert data["rows"][0]["spend"] == 100.5
    assert "xyz" in path.name


def test_list_normalized_stats_empty(tmp_path: Path):
    files = list_normalized_stats_files(storage_root=tmp_path)
    assert files == []


def test_list_normalized_stats_sorted(tmp_path: Path):
    stats_dir = tmp_path / "normalized" / "stats"
    stats_dir.mkdir(parents=True)
    (stats_dir / "old.json").write_text(
        '{"rows":[]}', encoding="utf-8",
    )
    (stats_dir / "new.json").write_text(
        '{"rows":[]}', encoding="utf-8",
    )
    files = list_normalized_stats_files(storage_root=tmp_path)
    assert len(files) == 2
    assert all(f.suffix == ".json" for f in files)


def test_save_raw_stats_without_report_id(tmp_path: Path):
    path = save_raw_stats(
        "data", storage_root=tmp_path, requested_at=AT,
    )
    assert path.exists()
    assert "stats_2026" in path.name


def test_creates_directories(tmp_path: Path):
    assert not (tmp_path / "raw").exists()
    save_raw_campaigns(
        [], storage_root=tmp_path, requested_at=AT,
    )
    assert (tmp_path / "raw" / "campaigns").exists()
