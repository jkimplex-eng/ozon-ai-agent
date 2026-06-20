"""Export COGS data to COGS tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "sku", "offer_id", "product_name", "unit_cost",
    "logistics_cost", "packaging_cost", "source", "updated_at", "status",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLS)


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        rows = execute_query(
            "SELECT c.sku, c.offer_id, p.name as product_name, "
            "c.unit_cost, c.logistics_cost, c.packaging_cost, "
            "c.source, c.updated_at "
            "FROM cogs c "
            "LEFT JOIN products p ON p.sku = c.sku "
            "ORDER BY c.sku"
        )
    except Exception as e:
        logger.warning("DB unavailable for COGS: %s", e)
        return None

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df["status"] = "OK"
    df["updated_at"] = pd.to_datetime(df["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")
    return df[EXPORT_COLS]


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.cogs.repository import list_records

        records = list_records()
    except Exception as e:
        logger.warning("File source unavailable for COGS: %s", e)
        return None

    if not records:
        return None

    rows = []
    for r in records:
        rows.append({
            "sku": r.sku,
            "offer_id": r.offer_id or "",
            "product_name": r.product_name or "",
            "unit_cost": r.unit_cost,
            "logistics_cost": r.logistics_cost,
            "packaging_cost": r.packaging_cost,
            "source": r.source,
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M"),
            "status": "OK",
        })

    return pd.DataFrame(rows)[EXPORT_COLS]


def export_cogs(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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

    return len(df)
