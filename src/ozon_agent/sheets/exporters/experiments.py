"""Export experiments to Experiments tab."""
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
    "id", "status", "sku", "hypothesis", "action",
    "risk", "confidence", "baseline_revenue", "current_revenue",
    "success_score", "direction_accuracy", "created_at", "lifecycle",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "id": "", "status": "NO DATA", "sku": "", "hypothesis": "",
        "action": "", "risk": "", "confidence": "", "baseline_revenue": "",
        "current_revenue": "", "success_score": "", "direction_accuracy": "",
        "created_at": "", "lifecycle": "No experiments available",
    }])


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.experiments.experiment_summary import experiment_to_dict
        from ozon_agent.experiments.repository import list_experiments

        exps = list_experiments(limit=200)
    except Exception as e:
        logger.warning("DB unavailable for Experiments: %s", e)
        return None

    if not exps:
        return _empty_df()

    rows = [experiment_to_dict(e) for e in exps]
    df = pd.DataFrame(rows)
    for col in EXPORT_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[EXPORT_COLS]
    df["id"] = df["id"].str[:12]
    df["hypothesis"] = df["hypothesis"].apply(lambda x: str(x)[:80] if x else "")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime(
        "%Y-%m-%d %H:%M"
    )
    return df


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_experiments

        rows = load_experiments()
    except Exception as e:
        logger.warning("File source unavailable for Experiments: %s", e)
        return None

    if not rows:
        return None

    mapped = []
    for r in rows:
        mapped.append({
            "id": str(r.get("id", ""))[:12],
            "status": r.get("status", r.get("result", "UNKNOWN")),
            "sku": r.get("sku", ""),
            "hypothesis": str(r.get("hypothesis", r.get("title", "")))[:80],
            "action": r.get("action", r.get("experiment_type", "")),
            "risk": r.get("risk", ""),
            "confidence": r.get("confidence", ""),
            "baseline_revenue": str(r.get("baseline_revenue", "")),
            "current_revenue": str(r.get("current_revenue", "")),
            "success_score": str(r.get("success_score", "")),
            "direction_accuracy": str(r.get("direction_accuracy", "")),
            "created_at": r.get("created_at", ""),
            "lifecycle": r.get("lifecycle", ""),
        })
    return pd.DataFrame(mapped)


def export_experiments(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
    if len(df) > 0 and "status" in df.columns:
        apply_status_colors(ws, 2, len(df))

    return len(df)
