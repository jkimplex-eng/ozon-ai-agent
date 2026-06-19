"""Export ETL log to Ingestion Status tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import (
    apply_header_format,
    apply_status_colors,
    auto_resize_columns,
    freeze_header,
)

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "Source", "Status", "Rows Fetched", "Rows Inserted",
    "Error", "Started", "Completed",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "Source": "N/A", "Status": "NO DATA", "Rows Fetched": 0,
        "Rows Inserted": 0, "Error": "", "Started": "", "Completed": "",
    }])


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        rows = execute_query(
            "SELECT source, status, rows_fetched, rows_inserted, "
            "error_message, started_at, completed_at "
            "FROM etl_log ORDER BY started_at DESC LIMIT 100"
        )
    except Exception as e:
        logger.warning("DB unavailable for Ingestion Status: %s", e)
        return None

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df.columns = EXPORT_COLS
    for col in ["Started", "Completed"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    return df


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_etl_log

        rows = load_etl_log()
    except Exception as e:
        logger.warning("File source unavailable for Ingestion Status: %s", e)
        return None

    if not rows:
        return None

    df = pd.DataFrame(rows)
    rename_map = {}
    for col in df.columns:
        lower = col.lower().replace(" ", "_")
        if lower in ("source", "status", "rows_fetched", "rows_inserted",
                      "error_message", "error", "started_at", "completed_at"):
            rename_map[col] = col
    if rename_map:
        df = df.rename(columns=rename_map)

    final_cols = []
    for c in EXPORT_COLS:
        if c in df.columns:
            final_cols.append(c)
        else:
            df[c] = ""
            final_cols.append(c)

    df = df[EXPORT_COLS]
    for col in ["Started", "Completed"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    return df


def export_ingestion_status(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
    from gspread_dataframe import set_with_dataframe

    df = None
    if not use_files:
        df = _load_from_db()
    if df is None:
        df = _load_from_files()
    if df is None:
        df = _empty_df()

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(EXPORT_COLS)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)
    apply_status_colors(ws, 2, len(df))

    return len(df)
