"""Export normalized Performance API stats to Google Sheets."""
from __future__ import annotations

import logging
from typing import Any

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "date",
    "campaign_id",
    "campaign_name",
    "sku",
    "product_name",
    "impressions",
    "clicks",
    "ctr",
    "add_to_cart",
    "cpc",
    "spend",
    "orders",
    "revenue",
    "model_orders",
    "model_revenue",
    "drr_promo",
    "ordered_amount",
    "drr_total",
    "raw_date_added",
]

FIELD_ALIASES = {
    "drr_promo": "drr",
    "drr_total": "total_drr",
    "raw_date_added": "added_at",
}


def _empty_df() -> pd.DataFrame:
    row = {col: "" for col in EXPORT_COLS}
    row["date"] = "NO DATA"
    return pd.DataFrame([row], columns=EXPORT_COLS)


def _value(row: dict[str, Any], column: str) -> Any:
    source_column = FIELD_ALIASES.get(column, column)
    value = row.get(source_column, "")
    if value is None:
        return ""
    return value


def _rows_to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return _empty_df()
    normalized_rows = [
        {column: _value(row, column) for column in EXPORT_COLS}
        for row in rows
    ]
    return pd.DataFrame(normalized_rows, columns=EXPORT_COLS)


def _load_from_files() -> pd.DataFrame:
    try:
        from ozon_agent.sheets.file_source import load_performance_stats

        rows = load_performance_stats()
    except Exception as e:
        logger.warning("File source unavailable for Performance Stats: %s", e)
        return _empty_df()
    return _rows_to_df(rows)


def export_performance_stats(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
    from gspread_dataframe import set_with_dataframe

    df = _load_from_files()

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(EXPORT_COLS)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)

    return len(df)
