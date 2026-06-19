"""Export experiments to Experiments tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.experiments.experiment_summary import experiment_to_dict
from ozon_agent.experiments.repository import list_experiments
from ozon_agent.sheets.format import (
    apply_header_format,
    apply_status_colors,
    auto_resize_columns,
    freeze_header,
)


def export_experiments(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    exps = list_experiments(limit=200)
    if not exps:
        return 0

    rows = [experiment_to_dict(e) for e in exps]

    export_cols = [
        "id", "status", "sku", "hypothesis", "action",
        "risk", "confidence", "baseline_revenue", "current_revenue",
        "success_score", "direction_accuracy", "created_at", "lifecycle",
    ]
    df = pd.DataFrame(rows)
    for col in export_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[export_cols]
    df["id"] = df["id"].str[:12]
    df["hypothesis"] = df["hypothesis"].apply(lambda x: str(x)[:80] if x else "")
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
