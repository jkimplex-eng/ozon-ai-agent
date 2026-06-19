"""Export analytics data to Daily Report tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.db.connection import execute_query
from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header


def export_daily_report(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    products = pd.DataFrame(execute_query("SELECT * FROM products"))
    sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
    advertising = pd.DataFrame(execute_query("SELECT * FROM advertising"))

    if sales.empty:
        return 0

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
        df["date_range"] = (
            f"{sales['date'].min()} to {sales['date'].max()}"
        )
    else:
        df["date_range"] = ""

    export_cols = [
        "sku", "product", "revenue", "quantity", "spend",
        "drr", "margin", "gross_profit", "rating", "reviews",
        "stock_days", "date_range",
    ]
    export_df = df[export_cols]

    ws.clear()
    set_with_dataframe(ws, export_df, include_column_header=True, allow_formulas=False)

    num_cols = len(export_cols)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)

    return len(export_df)
