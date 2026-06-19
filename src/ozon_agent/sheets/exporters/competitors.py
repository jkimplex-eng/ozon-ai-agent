"""Export competitor data to Competitors tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "SKU", "Category", "Revenue 30d", "GMV 30d", "Rating",
    "Reviews", "Price", "Verdict", "Date",
]


def _no_data_row() -> list[dict[str, str]]:
    return [{c: "" for c in EXPORT_COLS} | {"Verdict": "NO DATA"}]


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        products = execute_query("SELECT sku, name, price FROM products LIMIT 100")
    except Exception as e:
        logger.warning("DB unavailable for Competitors: %s", e)
        return None

    if not products:
        return pd.DataFrame(_no_data_row())

    rows = []
    for p in products:
        rows.append({
            "SKU": p.get("sku", ""),
            "Category": "",
            "Revenue 30d": "",
            "GMV 30d": "",
            "Rating": "",
            "Reviews": "",
            "Price": str(p.get("price", "")),
            "Verdict": "N/A",
            "Date": "",
        })
    return pd.DataFrame(rows)


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_competitors

        rows = load_competitors()
    except Exception as e:
        logger.warning("File source unavailable for Competitors: %s", e)
        return None

    if not rows:
        return None

    mapped = []
    for r in rows:
        mapped.append({
            "SKU": r.get("sku", r.get("SKU", "")),
            "Category": r.get("category", r.get("Category", "")),
            "Revenue 30d": str(r.get("revenue_30d", r.get("Revenue 30d", ""))),
            "GMV 30d": str(r.get("gmv_30d", r.get("GMV 30d", ""))),
            "Rating": str(r.get("rating", r.get("Rating", ""))),
            "Reviews": str(r.get("reviews", r.get("Reviews", ""))),
            "Price": str(r.get("price", r.get("Price", ""))),
            "Verdict": r.get("verdict", r.get("Verdict", "N/A")),
            "Date": r.get("date", r.get("Date", "")),
        })
    return pd.DataFrame(mapped)


def export_competitors(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
    from gspread_dataframe import set_with_dataframe

    df = None
    if not use_files:
        df = _load_from_db()
    if df is None:
        df = _load_from_files()
    if df is None:
        df = pd.DataFrame(_no_data_row())

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(EXPORT_COLS)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)

    return len(df)
