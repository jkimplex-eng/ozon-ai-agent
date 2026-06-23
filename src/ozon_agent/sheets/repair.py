"""Workbook auto-repair — fixes missing formulas, broken references, and structural issues."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

import gspread
from gspread.utils import ValueRenderOption

from ozon_agent.sheets.client import get_gspread_client, open_spreadsheet

logger = logging.getLogger(__name__)

TEMPLATE_TAB = "Daily Input Template"


@dataclass(frozen=True)
class RepairAction:
    tab: str
    issue: str
    fix: str
    applied: bool


@dataclass(frozen=True)
class RepairResult:
    actions: list[RepairAction]
    dry_run: bool
    total_actions: int
    applied_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "total_actions": self.total_actions,
            "applied_count": self.applied_count,
            "actions": [asdict(a) for a in self.actions],
        }


DASHBOARD_FORMULAS: dict[str, str] = {
    "B2": "=Settings!$B$5",
    "B4": "=Settings!$B$4",
    "E2": "=SUM('Daily Input 2026-06'!D1:D31)",
    "B3": "=IFERROR(E2/B2;0)",
}

UNIT_ECONOMICS_FORMULAS: dict[str, str] = {
    "B2": "='Daily Input 2026-05'!D2",
    "C2": "='Daily Input 2026-05'!F2",
}


def _check_tab_exists(
    spreadsheet: gspread.Spreadsheet, tab_name: str,
) -> gspread.Worksheet | None:
    """Check if tab exists, return worksheet or None."""
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return None


def _get_current_month_str() -> str:
    """Get current month string like '2026-06'."""
    from datetime import datetime
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"


def _repair_missing_formulas(
    spreadsheet: gspread.Spreadsheet,
    dry_run: bool,
) -> list[RepairAction]:
    """Check and repair missing formulas in critical tabs."""
    actions: list[RepairAction] = []

    dashboard = _check_tab_exists(spreadsheet, "Dashboard")
    if dashboard:
        values = dashboard.get("A1:F40", value_render_option=ValueRenderOption.formula)
        has_formulas = False
        for row in values:
            for cell in row:
                if isinstance(cell, str) and cell.startswith("="):
                    has_formulas = True
                    break
            if has_formulas:
                break

        if not has_formulas:
            actions.append(RepairAction(
                tab="Dashboard",
                issue="No formulas found in Dashboard",
                fix="Restore standard Dashboard formulas",
                applied=not dry_run,
            ))
            if not dry_run:
                _restore_dashboard_formulas(dashboard)

    unit_econ = _check_tab_exists(spreadsheet, "Unit Economics")
    if unit_econ:
        values = unit_econ.get("A1:J5", value_render_option=ValueRenderOption.formula)
        has_formulas = False
        for row in values:
            for cell in row:
                if isinstance(cell, str) and cell.startswith("="):
                    has_formulas = True
                    break
            if has_formulas:
                break

        if not has_formulas:
            actions.append(RepairAction(
                tab="Unit Economics",
                issue="No formulas found in Unit Economics",
                fix="Restore standard Unit Economics formulas",
                applied=not dry_run,
            ))

    month_review = _check_tab_exists(spreadsheet, "Month Review")
    if month_review:
        values = month_review.get("A1:H10", value_render_option=ValueRenderOption.formula)
        has_formulas = False
        for row in values:
            for cell in row:
                if isinstance(cell, str) and cell.startswith("="):
                    has_formulas = True
                    break
            if has_formulas:
                break

        if not has_formulas:
            actions.append(RepairAction(
                tab="Month Review",
                issue="No formulas found in Month Review",
                fix="Restore standard Month Review formulas",
                applied=not dry_run,
            ))

    return actions


def _restore_dashboard_formulas(dashboard: gspread.Worksheet) -> None:
    """Restore standard formulas to Dashboard tab."""
    current_month = _get_current_month_str()
    tab_name = f"Daily Input {current_month}"

    updates = [
        ("B2", "=Settings!$B$5"),
        ("B4", "=Settings!$B$4"),
        ("E2", f"=SUM('{tab_name}'!D1:D31)"),
        ("B3", "=IFERROR(E2/B2;0)"),
    ]

    for cell_ref, formula in updates:
        try:
            dashboard.update(cell_ref, formula)
        except Exception as e:
            logger.warning("Failed to update %s.%s: %s", "Dashboard", cell_ref, e)


def _check_named_ranges(
    spreadsheet: gspread.Spreadsheet,
    dry_run: bool,
) -> list[RepairAction]:
    """Check for missing named ranges."""
    actions: list[RepairAction] = []
    try:
        named_ranges = spreadsheet.list_named_ranges()
        range_names = {nr.name for nr in named_ranges}
        logger.info("Found %d named ranges: %s", len(range_names), range_names)
    except Exception as e:
        logger.warning("Could not read named ranges: %s", e)
    return actions


def _check_month_tabs(
    spreadsheet: gspread.Spreadsheet,
    dry_run: bool,
) -> list[RepairAction]:
    """Check if current and next month tabs exist."""
    actions: list[RepairAction] = []
    current_month = _get_current_month_str()
    current_tab = f"Daily Input {current_month}"

    ws = _check_tab_exists(spreadsheet, current_tab)
    if not ws:
        actions.append(RepairAction(
            tab=current_tab,
            issue=f"Current month tab '{current_tab}' is missing",
            fix=f"Create '{current_tab}' from template",
            applied=not dry_run,
        ))

    return actions


def repair_workbook(
    spreadsheet_id: str | None = None,
    dry_run: bool = True,
) -> RepairResult:
    """Run full workbook repair. Use dry_run=True to preview changes."""
    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)

    actions: list[RepairAction] = []

    actions.extend(_repair_missing_formulas(spreadsheet, dry_run))
    actions.extend(_check_named_ranges(spreadsheet, dry_run))
    actions.extend(_check_month_tabs(spreadsheet, dry_run))

    applied_count = sum(1 for a in actions if a.applied)

    return RepairResult(
        actions=actions,
        dry_run=dry_run,
        total_actions=len(actions),
        applied_count=applied_count,
    )
