"""Automatic monthly tab creation — creates next month's Daily Input from template."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import gspread

from ozon_agent.sheets.client import get_gspread_client, open_spreadsheet
from ozon_agent.sheets.format import (
    add_auto_filter,
    apply_header_format,
    auto_resize_columns,
    freeze_header,
)

logger = logging.getLogger(__name__)

TEMPLATE_TAB = "Daily Input Template"
DAYS_IN_MONTH: dict[int, int] = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap_year(year):
        return 29
    return DAYS_IN_MONTH.get(month, 30)


def _month_str(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


@dataclass(frozen=True)
class MonthTabResult:
    created: bool
    tab_name: str
    source_tab: str
    rows: int
    columns: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_tab_names(spreadsheet: gspread.Spreadsheet) -> set[str]:
    """Get all tab names in the spreadsheet."""
    return {ws.title for ws in spreadsheet.worksheets()}


def _copy_template(
    spreadsheet: gspread.Spreadsheet,
    template_ws: gspread.Worksheet,
    new_tab_name: str,
    year: int,
    month: int,
    days: int,
) -> gspread.Worksheet:
    """Copy template tab with proper dates and formulas."""
    template_values = template_ws.get_all_values()

    new_ws = spreadsheet.add_worksheet(
        title=new_tab_name,
        rows=max(len(template_values) + 5, days + 5),
        cols=max(len(template_values[0]) if template_values else 18, 18),
    )

    month_start = datetime(year, month, 1)

    for row_idx, row in enumerate(template_values):
        for col_idx, cell in enumerate(row):
            if row_idx == 0:
                new_ws.update_cell(row_idx + 1, col_idx + 1, cell)
                continue

            if col_idx == 0 and row_idx >= 1 and row_idx <= days:
                day_num = row_idx
                try:
                    date_val = month_start.replace(day=day_num)
                    new_ws.update_cell(row_idx + 1, col_idx + 1, date_val.strftime("%d.%m"))
                except ValueError:
                    new_ws.update_cell(row_idx + 1, col_idx + 1, f"{day_num:02d}.{month:02d}")
            else:
                new_ws.update_cell(row_idx + 1, col_idx + 1, cell)

    try:
        num_cols = max(len(row) for row in template_values) if template_values else 18
        apply_header_format(new_ws, num_cols)
        freeze_header(new_ws)
        auto_resize_columns(new_ws)
        add_auto_filter(new_ws, num_cols)
    except Exception as e:
        logger.warning("Failed to apply formatting to %s: %s", new_tab_name, e)

    return new_ws


def create_next_month_tab(
    spreadsheet_id: str | None = None,
    target_month: str | None = None,
) -> MonthTabResult:
    """Create the next month's Daily Input tab from template.

    Args:
        spreadsheet_id: Google Spreadsheet ID. Uses env default if None.
        target_month: Target month as 'YYYY-MM'. Defaults to next month.
    """
    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)

    now = datetime.now()
    if target_month:
        parts = target_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _next_month(now.year, now.month)

    tab_name = f"Daily Input {_month_str(year, month)}"
    days = _days_in_month(year, month)

    existing_tabs = _get_tab_names(spreadsheet)

    if tab_name in existing_tabs:
        return MonthTabResult(
            created=False,
            tab_name=tab_name,
            source_tab=TEMPLATE_TAB,
            rows=0,
            columns=0,
            message=f"Tab '{tab_name}' already exists",
        )

    template_ws = None
    for ws_name in [TEMPLATE_TAB, "Daily Input Template"]:
        try:
            template_ws = spreadsheet.worksheet(ws_name)
            break
        except gspread.exceptions.WorksheetNotFound:
            continue

    if template_ws is None:
        fallback_tab = f"Daily Input {_month_str(now.year, now.month)}"
        try:
            template_ws = spreadsheet.worksheet(fallback_tab)
        except gspread.exceptions.WorksheetNotFound:
            return MonthTabResult(
                created=False,
                tab_name=tab_name,
                source_tab="NONE",
                rows=0,
                columns=0,
                message="No template or existing tab found to copy from",
            )

    new_ws = _copy_template(
        spreadsheet, template_ws, tab_name, year, month, days,
    )

    values = new_ws.get_all_values()
    rows = len(values)
    cols = max((len(row) for row in values), default=0)

    logger.info("Created month tab: %s (%d rows, %d cols)", tab_name, rows, cols)

    return MonthTabResult(
        created=True,
        tab_name=tab_name,
        source_tab=template_ws.title,
        rows=rows,
        columns=cols,
        message=f"Created '{tab_name}' with {days} days from '{template_ws.title}'",
    )


def check_month_tab_exists(
    spreadsheet_id: str | None = None,
    month: str | None = None,
) -> bool:
    """Check if a month tab exists."""
    client = get_gspread_client()
    spreadsheet = open_spreadsheet(client, spreadsheet_id)

    if month:
        tab_name = f"Daily Input {month}"
    else:
        now = datetime.now()
        tab_name = f"Daily Input {_month_str(now.year, now.month)}"

    return tab_name in _get_tab_names(spreadsheet)
