"""Export FBO demand calculation to Google Sheets."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.api.ozon_client import create_client
from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header
from ozon_agent.supply.fbo import FboPlanningEngine

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "sku",
    "offer_id",
    "product_name",
    "cluster_name",
    "warehouse_name",
    "avg_daily_sales",
    "current_stock",
    "stock_days",
    "city_sales",
    "demand_30",
    "demand_60",
    "demand_90",
    "recommended_30",
    "recommended_60",
    "recommended_90",
    "planning_mode",
    "confidence",
    "data_quality_note",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "sku": "",
        "offer_id": "",
        "product_name": "No FBO demand data",
        "cluster_name": "",
        "warehouse_name": "",
        "avg_daily_sales": "",
        "current_stock": "",
        "stock_days": "",
        "city_sales": "",
        "demand_30": "",
        "demand_60": "",
        "demand_90": "",
        "recommended_30": "",
        "recommended_60": "",
        "recommended_90": "",
        "planning_mode": "",
        "confidence": "",
        "data_quality_note": "",
    }])


def _load_from_db() -> pd.DataFrame | None:
    try:
        engine = FboPlanningEngine(create_client())
        plans = engine.generate_cluster_demand(max_rows=500)
    except Exception as e:
        logger.warning("FBO demand unavailable: %s", e)
        return None

    if not plans:
        return _empty_df()

    df = pd.DataFrame([plan.to_dict() for plan in plans])
    for col in EXPORT_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPORT_COLS]


def export_fbo_demand(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
    from gspread_dataframe import set_with_dataframe

    df = None if use_files else _load_from_db()
    if df is None:
        df = _empty_df()

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)
    apply_header_format(ws, len(EXPORT_COLS))
    freeze_header(ws)
    auto_resize_columns(ws)
    return len(df)
