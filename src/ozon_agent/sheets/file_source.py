"""File-based data sources for Google Sheets sync.

Provides fallback data readers when PostgreSQL is unavailable.
Reads from:
- data/live_ozon/normalized/ (products, sales, advertising CSV/JSON)
- data/market_knowledge/ (snapshots, insights)
- data/experiments/ (experiments, outcomes, hypotheses)
- data/recommendation_memory/ (records, insights)
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_ROOT = Path("data")
LIVE_OZON_DIR = DATA_ROOT / "live_ozon" / "normalized"
MARKET_KNOWLEDGE_DIR = DATA_ROOT / "market_knowledge"
EXPERIMENTS_DIR = DATA_ROOT / "experiments"
MEMORY_DIR = DATA_ROOT / "recommendation_memory"


def _read_csv_files(directory: Path) -> list[dict[str, Any]]:
    """Read all CSV files in a directory and return combined rows."""
    rows: list[dict[str, Any]] = []
    if not directory.exists():
        return rows
    for csv_path in sorted(directory.glob("*.csv")):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows.extend(reader)
        except Exception as e:
            logger.warning("Failed to read %s: %s", csv_path, e)
    return rows


def _read_json_files(directory: Path) -> list[dict[str, Any]]:
    """Read all JSON files in a directory and return combined rows."""
    rows: list[dict[str, Any]] = []
    if not directory.exists():
        return rows
    for json_path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                rows.append(data)
            elif isinstance(data, list):
                rows.extend(item for item in data if isinstance(item, dict))
        except Exception as e:
            logger.warning("Failed to read %s: %s", json_path, e)
    return rows


def _read_nested_json(root: Path, subfolder: str) -> list[dict[str, Any]]:
    """Read JSON files from root/subfolder/."""
    return _read_json_files(root / subfolder)


def load_products() -> list[dict[str, Any]]:
    """Load products from file-based sources."""
    rows = _read_csv_files(LIVE_OZON_DIR / "products")
    if not rows:
        rows = _read_json_files(LIVE_OZON_DIR / "products")
    return rows


def load_sales() -> list[dict[str, Any]]:
    """Load sales from file-based sources."""
    rows = _read_csv_files(LIVE_OZON_DIR / "sales")
    if not rows:
        rows = _read_json_files(LIVE_OZON_DIR / "sales")
    return rows


def load_advertising() -> list[dict[str, Any]]:
    """Load advertising data from file-based sources."""
    rows = _read_csv_files(LIVE_OZON_DIR / "advertising")
    if not rows:
        rows = _read_json_files(LIVE_OZON_DIR / "advertising")
    return rows


def load_etl_log() -> list[dict[str, Any]]:
    """Load ETL log from file-based sources."""
    rows = _read_json_files(LIVE_OZON_DIR / "etl_log")
    if not rows:
        rows = _read_csv_files(LIVE_OZON_DIR / "etl_log")
    return rows


def load_market_insights() -> list[dict[str, Any]]:
    """Load market insights from file-based sources."""
    rows = _read_nested_json(MARKET_KNOWLEDGE_DIR, "insights")
    if not rows:
        rows = _read_nested_json(MARKET_KNOWLEDGE_DIR, "snapshots")
    return rows


def load_competitors() -> list[dict[str, Any]]:
    """Load competitor data from file-based sources."""
    rows = _read_nested_json(MARKET_KNOWLEDGE_DIR, "snapshots")
    if not rows:
        rows = load_products()
    return rows


def load_experiments() -> list[dict[str, Any]]:
    """Load experiments from file-based sources."""
    rows = _read_nested_json(EXPERIMENTS_DIR, "experiments")
    if not rows:
        rows = _read_nested_json(EXPERIMENTS_DIR, "hypotheses")
    return rows


def load_memory_records() -> list[dict[str, Any]]:
    """Load recommendation memory records from file-based sources."""
    return _read_nested_json(MEMORY_DIR, "records")


def load_memory_insights() -> list[dict[str, Any]]:
    """Load memory insights from file-based sources."""
    return _read_nested_json(MEMORY_DIR, "insights")


def has_any_file_data() -> bool:
    """Check if any file-based data exists."""
    for loader in (
        load_products, load_sales, load_advertising,
        load_market_insights, load_experiments, load_memory_records,
    ):
        if loader():
            return True
    return False
