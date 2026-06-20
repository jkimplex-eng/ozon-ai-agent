"""Export daily control metrics to Daily Control tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "date", "day", "orders", "revenue", "advertising", "cogs",
    "logistics", "gross_profit", "margin", "plan_vp", "deviation",
    "cumulative_vp", "run_rate", "status", "comment",
]

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

PLAN_VP_PER_DAY = float(
    __import__("os").environ.get("DAILY_CONTROL_PLAN_VP", "0")
)


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLS)


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.db.connection import execute_query

        rows = execute_query(
            "SELECT date, "
            "COALESCE(sales, 0) as revenue, "
            "COALESCE(advertising, 0) as advertising, "
            "COALESCE(ozon_commission, 0) as commission, "
            "COALESCE(logistics, 0) as logistics "
            "FROM finance ORDER BY date DESC LIMIT 31"
        )
    except Exception as e:
        logger.warning("DB unavailable for Daily Control: %s", e)
        return None

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["day"] = df["date"].dt.dayofweek.apply(
        lambda d: WEEKDAYS_RU[d] if 0 <= d < 7 else ""
    )
    df["orders"] = 0
    df["cogs"] = 0
    df["logistics"] = df["logistics"]
    df["gross_profit"] = (
        df["revenue"] - df["commission"] - df["logistics"] - df["advertising"]
    ).round(2)
    df["margin"] = (
        (df["gross_profit"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    df["plan_vp"] = PLAN_VP_PER_DAY
    df["deviation"] = (df["gross_profit"] - df["plan_vp"]).round(2)
    df["cumulative_vp"] = df["gross_profit"].cumsum().round(2)
    df["run_rate"] = 0.0

    for idx, row in df.iterrows():
        day_of_month = row["date"].day
        days_in_month = (
            row["date"].days_in_month
            if hasattr(row["date"], "days_in_month")
            else 30
        )
        if day_of_month > 0:
            df.at[idx, "run_rate"] = round(
                float(row["cumulative_vp"]) / day_of_month * days_in_month, 2
            )

    df["status"] = df["deviation"].apply(
        lambda d: "OK" if d >= 0 else "BELOW PLAN"
    )
    df["comment"] = ""
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    return df[EXPORT_COLS]


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_advertising, load_sales

        sales = load_sales()
        advertising = load_advertising()
    except Exception as e:
        logger.warning("File source unavailable for Daily Control: %s", e)
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
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(31)

    df["day"] = df["date"].dt.dayofweek.apply(
        lambda d: WEEKDAYS_RU[d] if 0 <= d < 7 else ""
    )
    df["cogs"] = 0
    df["logistics"] = 0
    df["gross_profit"] = (df["revenue"] - df["advertising"]).round(2)
    df["margin"] = (
        (df["gross_profit"] / df["revenue"].replace(0, float("nan")) * 100).round(2)
    ).fillna(0)
    df["plan_vp"] = PLAN_VP_PER_DAY
    df["deviation"] = (df["gross_profit"] - df["plan_vp"]).round(2)
    df["cumulative_vp"] = df["gross_profit"].cumsum().round(2)
    df["run_rate"] = 0.0

    for idx, row in df.iterrows():
        day_of_month = row["date"].day
        days_in_month = 30
        if day_of_month > 0:
            df.at[idx, "run_rate"] = round(
                float(row["cumulative_vp"]) / day_of_month * days_in_month, 2
            )

    df["status"] = df["deviation"].apply(
        lambda d: "OK" if d >= 0 else "BELOW PLAN"
    )
    df["comment"] = ""
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    return df[EXPORT_COLS]


def export_daily_control(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
