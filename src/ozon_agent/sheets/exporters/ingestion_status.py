"""Export ETL log to Ingestion Status tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.db.connection import execute_query
from ozon_agent.sheets.format import (
    apply_header_format,
    apply_status_colors,
    auto_resize_columns,
    freeze_header,
)


def export_ingestion_status(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    try:
        rows = execute_query(
            "SELECT source, status, rows_fetched, rows_inserted, "
            "error_message, started_at, completed_at "
            "FROM etl_log ORDER BY started_at DESC LIMIT 100"
        )
    except Exception:
        rows = []

    if not rows:
        rows = [{
            "source": "N/A",
            "status": "no data",
            "rows_fetched": 0,
            "rows_inserted": 0,
            "error_message": "",
            "started_at": "",
            "completed_at": "",
        }]

    df = pd.DataFrame(rows)
    df.columns = [
        "Source", "Status", "Rows Fetched", "Rows Inserted",
        "Error", "Started", "Completed",
    ]
    for col in ["Started", "Completed"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(df.columns)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)
    apply_status_colors(ws, 2, len(df))

    return len(df)
