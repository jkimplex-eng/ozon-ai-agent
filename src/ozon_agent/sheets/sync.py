"""Sync orchestrator — coordinates all tab exporters with throttling."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gspread
from gspread.exceptions import WorksheetNotFound

from ozon_agent.db.connection import is_db_available
from ozon_agent.sheets.client import (
    get_gspread_client,
    open_spreadsheet,
    retry_on_rate_limit,
)
from ozon_agent.sheets.exporters.approvals import export_approvals
from ozon_agent.sheets.exporters.competitors import export_competitors
from ozon_agent.sheets.exporters.daily_control import export_daily_control
from ozon_agent.sheets.exporters.daily_input import export_daily_input
from ozon_agent.sheets.exporters.daily_report import export_daily_report
from ozon_agent.sheets.exporters.daily_summary import export_daily_summary
from ozon_agent.sheets.exporters.experiments import export_experiments
from ozon_agent.sheets.exporters.ingestion_status import export_ingestion_status
from ozon_agent.sheets.exporters.market_insights import export_market_insights
from ozon_agent.sheets.exporters.memory import export_memory
from ozon_agent.sheets.exporters.performance_stats import export_performance_stats
from ozon_agent.sheets.exporters.products import export_products
from ozon_agent.sheets.exporters.recommendations import export_recommendations
from ozon_agent.sheets.exporters.stocks import export_stocks

logger = logging.getLogger(__name__)

TAB_EXPORTERS: dict[str, Any] = {
    "Daily Report": export_daily_report,
    "Recommendations": export_recommendations,
    "Market Insights": export_market_insights,
    "Competitors": export_competitors,
    "Experiments": export_experiments,
    "Recommendation Memory": export_memory,
    "Ingestion Status": export_ingestion_status,
    "Approvals": export_approvals,
    "Performance Stats": export_performance_stats,
    "Products": export_products,
    "Stocks": export_stocks,
    "Daily Summary": export_daily_summary,
    "Daily Control": export_daily_control,
    "Daily Input": export_daily_input,
}

_SYNC_STATUS_FILE = Path("data") / "sheets" / "sync_status.json"


def _load_sync_status() -> dict[str, str]:
    """Load last sync times from disk."""
    if _SYNC_STATUS_FILE.exists():
        try:
            data = json.loads(_SYNC_STATUS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_sync_status(status: dict[str, str]) -> None:
    """Persist last sync times to disk."""
    _SYNC_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SYNC_STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _resolve_source(source: str | None) -> bool:
    """Determine use_files flag from source argument or env var.

    Returns True if file-based sources should be used (DB skipped).
    """
    if source == "files":
        return True
    if source == "db":
        return False
    env_source = os.environ.get("SHEETS_DATA_SOURCE", "").lower()
    if env_source == "files":
        return True
    if env_source == "db":
        return False
    try:
        return not is_db_available()
    except Exception:
        return True


def _get_delay(delay: int | None) -> int:
    """Get sync delay in seconds from param, env, or default."""
    if delay is not None:
        return delay
    env_delay = os.environ.get("SHEETS_SYNC_DELAY_SECONDS")
    if env_delay:
        return int(env_delay)
    return 10


def _get_tab_columns(tab_name: str) -> list[str]:
    from ozon_agent.sheets.setup import TABS

    for tab_config in TABS:
        if tab_config["name"] == tab_name:
            return list(tab_config["columns"])
    return []


def _create_missing_worksheet(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
) -> gspread.Worksheet:
    from ozon_agent.sheets.format import (
        add_auto_filter,
        apply_header_format,
        auto_resize_columns,
        freeze_header,
    )

    columns = _get_tab_columns(tab_name)
    worksheet = spreadsheet.add_worksheet(
        title=tab_name,
        rows=1000,
        cols=max(len(columns), 1),
    )
    if columns:
        worksheet.update("A1", [columns])  # type: ignore[arg-type]
        num_cols = len(columns)
        apply_header_format(worksheet, num_cols)
        freeze_header(worksheet)
        auto_resize_columns(worksheet)
        add_auto_filter(worksheet, num_cols)
    logger.info("Created missing worksheet: %s", tab_name)
    return worksheet


def _get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(tab_name)
    except WorksheetNotFound:
        return _create_missing_worksheet(spreadsheet, tab_name)


def _sync_one_tab(
    tab_name: str,
    exporter: Any,
    use_files: bool,
    spreadsheet: Any,
    delay: int,
    is_last: bool,
) -> int:
    """Sync a single tab with retry on 429.

    Returns row count or -1 on failure.
    """
    try:
        ws = _get_or_create_worksheet(spreadsheet, tab_name)

        def _do_write() -> int:
            return int(exporter(ws, use_files=use_files))

        count = int(retry_on_rate_limit(_do_write))
        status = _load_sync_status()
        status[tab_name] = datetime.now(UTC).isoformat()
        _save_sync_status(status)
        logger.info("Synced %s: %d rows", tab_name, count)

        if not is_last:
            logger.debug("Waiting %ds before next tab...", delay)
            time.sleep(delay)

        return count
    except Exception as e:
        logger.error("Failed to sync %s: %s", tab_name, e)
        return -1


def sync_all(
    spreadsheet_id: str | None = None,
    source: str | None = None,
    delay: int | None = None,
) -> dict[str, int]:
    """Sync all tabs with throttling. Returns {tab_name: row_count}."""
    use_files = _resolve_source(source)
    sync_delay = _get_delay(delay)

    if use_files:
        logger.info("Using file-based data sources (PostgreSQL unavailable or source=files)")
    else:
        logger.info("Using PostgreSQL data sources")
    logger.info("Sync delay between tabs: %ds", sync_delay)

    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    results: dict[str, int] = {}

    tab_names = list(TAB_EXPORTERS.keys())
    for idx, tab_name in enumerate(tab_names):
        is_last = idx == len(tab_names) - 1
        exporter = TAB_EXPORTERS[tab_name]
        results[tab_name] = _sync_one_tab(
            tab_name, exporter, use_files, spreadsheet, sync_delay, is_last,
        )

    return results


def sync_tab(
    tab_name: str,
    spreadsheet_id: str | None = None,
    source: str | None = None,
) -> int:
    """Sync a single tab. Returns row count."""
    exporter = TAB_EXPORTERS.get(tab_name)
    if exporter is None:
        raise ValueError(
            f"Unknown tab '{tab_name}'. Available: {list(TAB_EXPORTERS.keys())}"
        )

    use_files = _resolve_source(source)

    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, tab_name)

    def _do_write() -> int:
        return int(exporter(ws, use_files=use_files))

    count = int(retry_on_rate_limit(_do_write))
    status = _load_sync_status()
    status[tab_name] = datetime.now(UTC).isoformat()
    _save_sync_status(status)
    return count


def get_sync_status() -> dict[str, str]:
    """Return last sync time per tab from disk."""
    return _load_sync_status()
