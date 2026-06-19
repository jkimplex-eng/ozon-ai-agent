"""Google Sheets formatting utilities.

Provides consistent formatting for all tabs:
- Header styling (bold white on colored background)
- Status color coding
- Auto-resize columns
- Frozen header row
- Auto-filters
- Conditional formatting rules
"""
from __future__ import annotations

import gspread
import gspread_formatting as gsf
from gspread_formatting import (
    BooleanCondition,
    BooleanRule,
    CellFormat,
    ConditionalFormatRule,
    GridRange,
)
from gspread_formatting.models import Color

HEADER_BACKGROUND = Color(0.102, 0.137, 0.494)
HEADER_FONT_COLOR = Color(1, 1, 1)

STATUS_COLORS: dict[str, Color] = {
    "COMPLETED": Color(0.784, 0.902, 0.784),
    "SUCCESS": Color(0.784, 0.902, 0.784),
    "APPROVED": Color(0.784, 0.902, 0.784),
    "EXECUTED": Color(0.784, 0.902, 0.784),
    "RUNNING": Color(0.741, 0.867, 0.984),
    "READY": Color(0.741, 0.867, 0.984),
    "PENDING": Color(0.741, 0.867, 0.984),
    "PAUSED": Color(1, 0.976, 0.769),
    "WARNING": Color(1, 0.976, 0.769),
    "FAILED": Color(1, 0.808, 0.824),
    "CANCELLED": Color(1, 0.808, 0.824),
    "REJECTED": Color(1, 0.808, 0.824),
    "DRAFT": Color(0.878, 0.878, 0.878),
}

COLUMN_WIDTHS: dict[str, int] = {
    "id": 120,
    "status": 100,
    "sku": 120,
    "action": 130,
    "reason": 250,
    "hypothesis": 250,
    "summary": 250,
    "date": 130,
    "created_at": 130,
    "updated_at": 130,
    "source": 100,
    "error": 200,
    "default": 120,
}


def apply_header_format(ws: gspread.Worksheet, num_cols: int) -> None:
    fmt = CellFormat(
        backgroundColor=HEADER_BACKGROUND,
        textFormat=gsf.TextFormat(bold=True, foregroundColor=HEADER_FONT_COLOR),
        horizontalAlignment="CENTER",
        verticalAlignment="MIDDLE",
    )
    fmt_range = f"A1:{_col_letter(num_cols)}1"
    gsf.format_cell_range(ws, fmt_range, fmt)
    ws.set_row_height(1, 32)  # type: ignore[attr-defined]


def apply_status_colors(
    ws: gspread.Worksheet,
    status_col: int,
    total_rows: int,
) -> None:
    col_letter = _col_letter(status_col)
    rules: list[ConditionalFormatRule] = []
    for status, color in STATUS_COLORS.items():
        rule = ConditionalFormatRule(
            ranges=[GridRange(ws.id, 2, total_rows + 1, status_col - 1, status_col)],
            rule=BooleanRule(
                condition=BooleanCondition(
                    "CUSTOM_FORMULA", [f'={col_letter}2="{status}"']
                ),
                format=CellFormat(backgroundColor=color),
            ),
        )
        rules.append(rule)
    if rules:
        existing = gsf.get_conditional_format_rules(ws)
        gsf.set_conditional_format_rules(ws, existing + rules)


def auto_resize_columns(
    ws: gspread.Worksheet, column_map: dict[str, int] | None = None
) -> None:
    if column_map is None:
        column_map = {}
    headers = ws.row_values(1)
    for i, header in enumerate(headers, 1):
        key = header.lower().strip()
        width = column_map.get(key, COLUMN_WIDTHS.get(key, COLUMN_WIDTHS["default"]))
        ws.set_column_width(i, width)  # type: ignore[attr-defined]


def freeze_header(ws: gspread.Worksheet) -> None:
    ws.freeze(rows=1)


def add_auto_filter(ws: gspread.Worksheet, num_cols: int) -> None:
    last_col = _col_letter(num_cols)
    ws.set_basic_filter(f"A1:{last_col}1")


def apply_conditional_rules(
    ws: gspread.Worksheet,
    rules: list[ConditionalFormatRule],
) -> None:
    existing = gsf.get_conditional_format_rules(ws)
    gsf.set_conditional_format_rules(ws, existing + rules)


def _col_letter(col_num: int) -> str:
    result = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        result = chr(65 + remainder) + result
    return result
