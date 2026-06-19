"""Sync orchestrator — coordinates all tab exporters."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ozon_agent.sheets.client import get_gspread_client, open_spreadsheet
from ozon_agent.sheets.exporters.approvals import export_approvals
from ozon_agent.sheets.exporters.competitors import export_competitors
from ozon_agent.sheets.exporters.daily_report import export_daily_report
from ozon_agent.sheets.exporters.experiments import export_experiments
from ozon_agent.sheets.exporters.ingestion_status import export_ingestion_status
from ozon_agent.sheets.exporters.market_insights import export_market_insights
from ozon_agent.sheets.exporters.memory import export_memory
from ozon_agent.sheets.exporters.recommendations import export_recommendations

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
}

_last_sync: dict[str, str] = {}


def sync_all(spreadsheet_id: str | None = None) -> dict[str, int]:
    """Sync all tabs. Returns {tab_name: row_count}."""
    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    results: dict[str, int] = {}

    for tab_name, exporter in TAB_EXPORTERS.items():
        try:
            ws = spreadsheet.worksheet(tab_name)
            count = exporter(ws)
            results[tab_name] = count
            _last_sync[tab_name] = datetime.now(UTC).isoformat()
            logger.info("Synced %s: %d rows", tab_name, count)
        except Exception as e:
            results[tab_name] = -1
            logger.error("Failed to sync %s: %s", tab_name, e)

    return results


def sync_tab(tab_name: str, spreadsheet_id: str | None = None) -> int:
    """Sync a single tab. Returns row count."""
    exporter = TAB_EXPORTERS.get(tab_name)
    if exporter is None:
        raise ValueError(
            f"Unknown tab '{tab_name}'. Available: {list(TAB_EXPORTERS.keys())}"
        )

    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    ws = spreadsheet.worksheet(tab_name)
    count = int(exporter(ws))
    _last_sync[tab_name] = datetime.now(UTC).isoformat()
    return count


def get_sync_status() -> dict[str, str]:
    """Return last sync time per tab."""
    return dict(_last_sync)
