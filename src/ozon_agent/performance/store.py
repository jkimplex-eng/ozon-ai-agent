from __future__ import annotations

import json
import logging
from pathlib import Path

from ozon_agent.performance.models import PerformanceCampaign, PerformanceStatsRow, utc_now_iso

logger = logging.getLogger(__name__)

DEFAULT_DATA_ROOT = Path("data") / "performance"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_raw_campaigns(
    campaigns: list[PerformanceCampaign],
    *,
    storage_root: Path | None = None,
    requested_at: str | None = None,
) -> Path:
    root = storage_root or DEFAULT_DATA_ROOT
    raw_dir = root / "raw" / "campaigns"
    _ensure_dir(raw_dir)
    ts = requested_at or utc_now_iso()
    safe_ts = ts.replace(":", "-").replace("T", "_").replace("+", "_")
    path = raw_dir / f"campaigns_{safe_ts}.json"
    data = [c.to_dict() for c in campaigns]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved raw campaigns to %s", path)
    return path


def save_normalized_campaigns(
    campaigns: list[PerformanceCampaign],
    *,
    storage_root: Path | None = None,
    requested_at: str | None = None,
) -> Path:
    root = storage_root or DEFAULT_DATA_ROOT
    norm_dir = root / "normalized" / "campaigns"
    _ensure_dir(norm_dir)
    ts = requested_at or utc_now_iso()
    safe_ts = ts.replace(":", "-").replace("T", "_").replace("+", "_")
    path = norm_dir / f"campaigns_{safe_ts}.json"
    data = {"campaigns": [c.to_dict() for c in campaigns]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved normalized campaigns to %s", path)
    return path


def save_raw_stats(
    csv_text: str,
    *,
    storage_root: Path | None = None,
    requested_at: str | None = None,
    report_id: str = "",
) -> Path:
    root = storage_root or DEFAULT_DATA_ROOT
    raw_dir = root / "raw" / "stats"
    _ensure_dir(raw_dir)
    ts = requested_at or utc_now_iso()
    safe_ts = ts.replace(":", "-").replace("T", "_").replace("+", "_")
    suffix = f"_{report_id}" if report_id else ""
    path = raw_dir / f"stats{suffix}_{safe_ts}.csv"
    path.write_text(csv_text, encoding="utf-8")
    logger.info("Saved raw stats to %s", path)
    return path


def save_normalized_stats(
    rows: list[PerformanceStatsRow],
    *,
    storage_root: Path | None = None,
    requested_at: str | None = None,
    report_id: str = "",
) -> Path:
    root = storage_root or DEFAULT_DATA_ROOT
    norm_dir = root / "normalized" / "stats"
    _ensure_dir(norm_dir)
    ts = requested_at or utc_now_iso()
    safe_ts = ts.replace(":", "-").replace("T", "_").replace("+", "_")
    suffix = f"_{report_id}" if report_id else ""
    path = norm_dir / f"stats{suffix}_{safe_ts}.json"
    data = {"rows": [r.to_dict() for r in rows]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d normalized stats rows to %s", len(rows), path)
    return path


def list_normalized_stats_files(
    *,
    storage_root: Path | None = None,
) -> list[Path]:
    root = storage_root or DEFAULT_DATA_ROOT
    stats_dir = root / "normalized" / "stats"
    if not stats_dir.exists():
        return []
    return sorted(stats_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
