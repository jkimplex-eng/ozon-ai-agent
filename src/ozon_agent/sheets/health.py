"""Workbook health audit — scans tabs for formula errors and structural issues."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import gspread
from gspread.utils import ValueRenderOption

from ozon_agent.sheets.client import get_gspread_client, open_spreadsheet

logger = logging.getLogger(__name__)

ERROR_PATTERNS = ("#REF!", "#ERROR!", "#VALUE!", "#N/A", "#N/A ")

CRITICAL_TABS = [
    "Dashboard",
    "Unit Economics",
    "Month Review",
    "Settings",
    "Daily Input",
]


@dataclass(frozen=True)
class TabHealth:
    tab: str
    exists: bool
    rows: int = 0
    columns: int = 0
    formula_count: int = 0
    error_count: int = 0
    errors: dict[str, int] = field(default_factory=dict)
    status: str = "OK"


@dataclass(frozen=True)
class WorkbookHealth:
    spreadsheet_id: str
    title: str
    total_formulas: int
    total_errors: int
    error_summary: dict[str, int]
    tabs: list[TabHealth]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "title": self.title,
            "total_formulas": self.total_formulas,
            "total_errors": self.total_errors,
            "error_summary": self.error_summary,
            "status": self.status,
            "tabs": [asdict(t) for t in self.tabs],
        }


def _scan_worksheet(ws: gspread.Worksheet) -> TabHealth:
    """Scan a single worksheet for formula errors."""
    tab_name = ws.title
    try:
        formulas = ws.get(
            "A1:AZ2000",
            value_render_option=ValueRenderOption.formula,
        )
    except Exception as e:
        logger.warning("Failed to read tab %s: %s", tab_name, e)
        return TabHealth(
            tab=tab_name, exists=True, status=f"READ_ERROR: {e}",
        )

    values = ws.get_all_values()
    rows = len(values)
    cols = max((len(row) for row in values), default=0)

    formula_count = 0
    error_counts: dict[str, int] = {}
    total_errors = 0

    for row in formulas:
        for cell in row:
            if isinstance(cell, str) and cell.startswith("="):
                formula_count += 1
            if isinstance(cell, str):
                cell_upper = cell.strip().upper()
                for pattern in ERROR_PATTERNS:
                    normalized = pattern.strip()
                    if cell_upper == normalized or cell_upper.startswith(normalized):
                        error_counts[normalized] = error_counts.get(normalized, 0) + 1
                        total_errors += 1
                        break

    status = "OK" if total_errors == 0 else f"ERRORS: {total_errors}"

    return TabHealth(
        tab=tab_name,
        exists=True,
        rows=rows,
        columns=cols,
        formula_count=formula_count,
        error_count=total_errors,
        errors=error_counts,
        status=status,
    )


def audit_workbook(
    spreadsheet_id: str | None = None,
) -> WorkbookHealth:
    """Run full health audit on the workbook."""
    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)

    total_formulas = 0
    total_errors = 0
    error_summary: dict[str, int] = {}
    tab_healths: list[TabHealth] = []

    existing_tabs = {ws.title for ws in spreadsheet.worksheets()}

    for tab_name in CRITICAL_TABS:
        if tab_name not in existing_tabs:
            tab_healths.append(
                TabHealth(tab=tab_name, exists=False, status="MISSING")
            )
            continue
        ws = spreadsheet.worksheet(tab_name)
        health = _scan_worksheet(ws)
        tab_healths.append(health)
        total_formulas += health.formula_count
        total_errors += health.error_count
        for err_type, count in health.errors.items():
            error_summary[err_type] = error_summary.get(err_type, 0) + count

    for ws in spreadsheet.worksheets():
        if ws.title in CRITICAL_TABS:
            continue
        health = _scan_worksheet(ws)
        tab_healths.append(health)
        total_formulas += health.formula_count
        total_errors += health.error_count
        for err_type, count in health.errors.items():
            error_summary[err_type] = error_summary.get(err_type, 0) + count

    status = "OK" if total_errors == 0 else f"ERRORS: {total_errors}"

    return WorkbookHealth(
        spreadsheet_id=spreadsheet.id,
        title=spreadsheet.title,
        total_formulas=total_formulas,
        total_errors=total_errors,
        error_summary=error_summary,
        tabs=tab_healths,
        status=status,
    )


def save_audit_report(
    health: WorkbookHealth,
    output_dir: str | Path = "data/workbook_health",
) -> Path:
    """Save audit report to disk."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "health_report.json"
    report_path.write_text(
        json.dumps(health.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Health report saved: %s", report_path)
    return report_path
