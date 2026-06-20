"""Export stock levels to Stocks tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = ["name", "sku", "offer_id", "stock"]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLS)


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        rows = execute_query(
            "SELECT p.name, p.sku, p.offer_id, "
            "COALESCE(SUM(s.stock_total), 0) as stock "
            "FROM products p "
            "LEFT JOIN stocks s ON s.product_id = p.id "
            "GROUP BY p.id, p.name, p.sku, p.offer_id "
            "ORDER BY p.sku"
        )
    except Exception as e:
        logger.warning("DB unavailable for Stocks: %s", e)
        return None

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df["stock"] = df["stock"].fillna(0)
    return df[EXPORT_COLS]


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_products

        products = load_products()
    except Exception as e:
        logger.warning("File source unavailable for Stocks: %s", e)
        return None

    if not products:
        return None

    df = pd.DataFrame(products)
    for col in EXPORT_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPORT_COLS]


def export_stocks(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
