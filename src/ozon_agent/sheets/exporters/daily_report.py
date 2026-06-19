"""Export analytics data to Daily Report tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "sku", "product", "revenue", "quantity", "spend",
    "drr", "margin", "gross_profit", "rating", "reviews",
    "stock_days", "date_range",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLS)


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        products = pd.DataFrame(execute_query("SELECT * FROM products"))
        sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
        advertising = pd.DataFrame(execute_query("SELECT * FROM advertising"))
    except Exception as e:
        logger.warning("DB unavailable for Daily Report: %s", e)
        return None

    if sales.empty:
        return _empty_df()

    agg = sales.groupby("sku").agg(
        revenue=("revenue", "sum"),
        quantity=("quantity", "sum"),
    ).reset_index()

    ad_agg = advertising.groupby("sku").agg(spend=("spend", "sum")).reset_index()

    df = agg.merge(ad_agg, on="sku", how="left")
    df["spend"] = df["spend"].fillna(0)
    df["drr"] = (df["spend"] / df["revenue"] * 100).round(2)
    df["margin"] = ((df["revenue"] - df["spend"]) / df["revenue"] * 100).round(2)
    df["gross_profit"] = (df["revenue"] - df["spend"]).round(2)

    if not products.empty and "sku" in products.columns:
        name_map = (
            products.set_index("sku")["name"].to_dict()
            if "name" in products.columns
            else {}
        )
        df["product"] = df["sku"].map(name_map).fillna("")
    else:
        df["product"] = ""

    df["rating"] = ""
    df["reviews"] = ""
    df["stock_days"] = ""
    if "date" in sales.columns:
        df["date_range"] = f"{sales['date'].min()} to {sales['date'].max()}"
    else:
        df["date_range"] = ""

    return df[EXPORT_COLS]


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_advertising, load_products, load_sales

        products = load_products()
        sales = load_sales()
        advertising = load_advertising()
    except Exception as e:
        logger.warning("File source unavailable for Daily Report: %s", e)
        return None

    if not sales:
        return None

    sales_df = pd.DataFrame(sales)
    products_df = pd.DataFrame(products) if products else pd.DataFrame()
    ad_df = pd.DataFrame(advertising) if advertising else pd.DataFrame()

    if "sku" not in sales_df.columns:
        return None

    agg = sales_df.groupby("sku").agg(
        revenue=("revenue", "sum"),
        quantity=("quantity", "sum"),
    ).reset_index()

    if not ad_df.empty and "sku" in ad_df.columns and "spend" in ad_df.columns:
        ad_agg = ad_df.groupby("sku").agg(spend=("spend", "sum")).reset_index()
        df = agg.merge(ad_agg, on="sku", how="left")
    else:
        df = agg
        df["spend"] = 0

    df["spend"] = df["spend"].fillna(0)
    df["drr"] = (df["spend"] / df["revenue"] * 100).round(2)
    df["margin"] = ((df["revenue"] - df["spend"]) / df["revenue"] * 100).round(2)
    df["gross_profit"] = (df["revenue"] - df["spend"]).round(2)

    if not products_df.empty and "sku" in products_df.columns:
        name_map = (
            products_df.set_index("sku")["name"].to_dict()
            if "name" in products_df.columns
            else {}
        )
        df["product"] = df["sku"].map(name_map).fillna("")
    else:
        df["product"] = ""

    df["rating"] = ""
    df["reviews"] = ""
    df["stock_days"] = ""
    df["date_range"] = ""

    return df[EXPORT_COLS]


def export_daily_report(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
