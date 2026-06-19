"""Export market insights to Market Insights tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = ["Source", "Type", "Insight", "Confidence", "Category", "Relevance", "Date"]


def _no_data_row() -> list[dict[str, str]]:
    return [{
        "Source": "System", "Type": "Info",
        "Insight": "NO DATA — run sync or add file data",
        "Confidence": "N/A", "Category": "", "Relevance": "low", "Date": "",
    }]


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        products = execute_query("SELECT sku, name, price FROM products LIMIT 100")
    except Exception as e:
        logger.warning("DB unavailable for Market Insights: %s", e)
        return None

    if not products:
        return pd.DataFrame(_no_data_row())

    rows = []
    for p in products:
        rows.append({
            "Source": "Products DB",
            "Type": "Product",
            "Insight": f"{p.get('name', '')} — price {p.get('price', 0)}",
            "Confidence": "N/A",
            "Category": "",
            "Relevance": "high",
            "Date": "",
        })
    return pd.DataFrame(rows)


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_market_insights

        rows = load_market_insights()
    except Exception as e:
        logger.warning("File source unavailable for Market Insights: %s", e)
        return None

    if not rows:
        return None

    mapped = []
    for r in rows:
        insight_text = (
            r.get("message", r.get("insight", r.get("Insight", "")))
            or r.get("summary", "")
        )
        mapped.append({
            "Source": r.get("source", r.get("Source", "Files")),
            "Type": r.get("type", r.get("Type", "Insight")),
            "Insight": str(insight_text)[:200],
            "Confidence": str(r.get("confidence", r.get("Confidence", "N/A"))),
            "Category": r.get("category", r.get("Category", "")),
            "Relevance": r.get("relevance", r.get("Relevance", "medium")),
            "Date": r.get("date", r.get("created_at", r.get("Date", ""))),
        })
    return pd.DataFrame(mapped)


def export_market_insights(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
