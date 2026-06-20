"""Export daily P&L summary to Daily Summary tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "date", "revenue", "payout", "orders", "commission",
    "logistics", "advertising", "cogs", "profit", "margin", "drr",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLS)


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        rows = execute_query(
            "SELECT date, "
            "COALESCE(sales, 0) as revenue, "
            "COALESCE(accrued_total, 0) as payout, "
            "0 as orders, "
            "COALESCE(ozon_commission, 0) as commission, "
            "COALESCE(logistics, 0) as logistics, "
            "COALESCE(advertising, 0) as advertising, "
            "0 as cogs, "
            "0 as profit, "
            "0.0 as margin, "
            "0.0 as drr "
            "FROM finance ORDER BY date DESC LIMIT 90"
        )
    except Exception as e:
        logger.warning("DB unavailable for Daily Summary: %s", e)
        return None

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["profit"] = (df["revenue"] - df["commission"] - df["logistics"]
                    - df["advertising"]).round(2)
    df["margin"] = (
        (df["profit"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    df["drr"] = (
        (df["advertising"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    return df[EXPORT_COLS]


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_advertising, load_sales

        sales = load_sales()
        advertising = load_advertising()
    except Exception as e:
        logger.warning("File source unavailable for Daily Summary: %s", e)
        return None

    if not sales:
        return None

    sales_df = pd.DataFrame(sales)
    ad_df = pd.DataFrame(advertising) if advertising else pd.DataFrame()

    if "date" not in sales_df.columns:
        return None

    agg = sales_df.groupby("date").agg(
        revenue=("revenue", "sum"),
        orders=("quantity", "sum"),
    ).reset_index()

    if not ad_df.empty and "date" in ad_df.columns and "spend" in ad_df.columns:
        ad_agg = ad_df.groupby("date").agg(advertising=("spend", "sum")).reset_index()
        df = agg.merge(ad_agg, on="date", how="left")
    else:
        df = agg
        df["advertising"] = 0

    df["advertising"] = df["advertising"].fillna(0)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["payout"] = 0
    df["commission"] = 0
    df["logistics"] = 0
    df["cogs"] = 0
    df["profit"] = (df["revenue"] - df["advertising"]).round(2)
    df["margin"] = (
        (df["profit"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    df["drr"] = (
        (df["advertising"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    return df[EXPORT_COLS]


def export_daily_summary(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
