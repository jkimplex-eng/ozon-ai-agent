"""Export recommendations to Recommendations tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import (
    apply_header_format,
    apply_status_colors,
    auto_resize_columns,
    freeze_header,
)

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "id", "status", "sku", "action", "confidence_level",
    "risk_level", "expected_effect", "reason", "created_at", "approved_by",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "id": "", "status": "NO DATA", "sku": "", "action": "",
        "confidence_level": "", "risk_level": "", "expected_effect": "",
        "reason": "No recommendations available", "created_at": "", "approved_by": "",
    }])


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.approval.approval_summary import recommendation_to_dict
        from ozon_agent.approval.repository import list_recommendations

        recs = list_recommendations(limit=500)
    except Exception as e:
        logger.warning("DB unavailable for Recommendations: %s", e)
        return None

    if not recs:
        return _empty_df()

    rows = [recommendation_to_dict(r) for r in recs]
    df = pd.DataFrame(rows)
    for col in EXPORT_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[EXPORT_COLS]
    df["id"] = df["id"].str[:12]
    df["expected_effect"] = df["expected_effect"].apply(
        lambda x: str(x)[:80] if x else ""
    )
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime(
        "%Y-%m-%d %H:%M"
    )
    return df


def export_recommendations(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
    from gspread_dataframe import set_with_dataframe

    df = None
    if not use_files:
        df = _load_from_db()
    if df is None:
        df = _empty_df()

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(EXPORT_COLS)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)
    if len(df) > 0 and "status" in df.columns:
        apply_status_colors(ws, 2, len(df))

    return len(df)
