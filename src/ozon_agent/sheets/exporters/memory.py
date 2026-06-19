"""Export learning/calibration data to Recommendation Memory tab."""
from __future__ import annotations

import logging

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header

logger = logging.getLogger(__name__)

EXPORT_COLS = [
    "Dimension", "Key", "Samples", "Calibration", "Error",
    "Direction Acc", "Success Rate",
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "Dimension": "System", "Key": "NO DATA — no observed outcomes",
        "Samples": "0", "Calibration": "", "Error": "",
        "Direction Acc": "", "Success Rate": "",
    }])


def _load_from_db() -> pd.DataFrame | None:
    try:
        from ozon_agent.approval.models import RecommendationStatus
        from ozon_agent.approval.repository import list_recommendations as list_stored
        from ozon_agent.learning.outcome_learning import (
            build_learning_samples,
            calculate_action_accuracy,
        )

        stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    except Exception as e:
        logger.warning("DB unavailable for Recommendation Memory: %s", e)
        return None

    if not stored:
        return None

    try:
        outcomes = []
        for s in stored:
            from ozon_agent.approval.repository import list_outcomes

            outcomes.extend(list_outcomes(s.id))
        samples = build_learning_samples(stored, outcomes)
        by_action = calculate_action_accuracy(samples)
    except Exception as e:
        logger.warning("Learning computation failed: %s", e)
        return None

    rows = []
    for action, acc in by_action.items():
        rows.append({
            "Dimension": "Action",
            "Key": action,
            "Samples": str(getattr(acc, "total_samples", 0)),
            "Calibration": f"{getattr(acc, 'direction_accuracy', 0):.2f}",
            "Error": f"{getattr(acc, 'average_percentage_error', 0):.2f}",
            "Direction Acc": f"{getattr(acc, 'direction_accuracy', 0):.2f}",
            "Success Rate": f"{getattr(acc, 'success_rate', 0):.2f}",
        })
    return pd.DataFrame(rows) if rows else None


def _load_from_files() -> pd.DataFrame | None:
    try:
        from ozon_agent.sheets.file_source import load_memory_insights, load_memory_records

        records = load_memory_records()
        insights = load_memory_insights()
    except Exception as e:
        logger.warning("File source unavailable for Recommendation Memory: %s", e)
        return None

    rows = []
    for r in records:
        rows.append({
            "Dimension": "Record",
            "Key": f"{r.get('sku', '')} / {r.get('action', '')}",
            "Samples": "1",
            "Calibration": str(r.get("success_score", "")),
            "Error": "",
            "Direction Acc": "",
            "Success Rate": str(r.get("result", "")),
        })
    for ins in insights:
        rows.append({
            "Dimension": "Insight",
            "Key": ins.get("message", ins.get("action", "")),
            "Samples": str(ins.get("sample_size", "")),
            "Calibration": "",
            "Error": "",
            "Direction Acc": "",
            "Success Rate": str(ins.get("success_rate", "")),
        })

    return pd.DataFrame(rows) if rows else None


def export_memory(ws: gspread.Worksheet, *, use_files: bool = False) -> int:
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
