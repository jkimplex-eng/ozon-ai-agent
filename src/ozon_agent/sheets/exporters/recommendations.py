"""Export recommendations to Recommendations tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.approval.approval_summary import recommendation_to_dict
from ozon_agent.approval.repository import list_recommendations
from ozon_agent.sheets.format import (
    apply_header_format,
    apply_status_colors,
    auto_resize_columns,
    freeze_header,
)


def export_recommendations(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    recs = list_recommendations(limit=500)
    if not recs:
        return 0

    rows = [recommendation_to_dict(r) for r in recs]

    export_cols = [
        "id", "status", "sku", "action", "confidence_level",
        "risk_level", "expected_effect", "reason", "created_at", "approved_by",
    ]
    df = pd.DataFrame(rows)
    for col in export_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[export_cols]
    df["id"] = df["id"].str[:12]
    df["expected_effect"] = df["expected_effect"].apply(
        lambda x: str(x)[:80] if x else ""
    )
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime(
        "%Y-%m-%d %H:%M"
    )

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(export_cols)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)
    apply_status_colors(ws, 2, len(df))

    return len(df)
