"""Export learning/calibration data to Recommendation Memory tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header


def export_memory(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    rows: list[dict[str, str]] = []

    try:
        from ozon_agent.approval.models import RecommendationStatus
        from ozon_agent.approval.repository import list_recommendations as list_stored
        from ozon_agent.learning.outcome_learning import (
            build_learning_samples,
            calculate_action_accuracy,
        )

        stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
        if stored:
            outcomes = []
            for s in stored:
                from ozon_agent.approval.repository import list_outcomes

                outcomes.extend(list_outcomes(s.id))
            samples = build_learning_samples(stored, outcomes)
            by_action = calculate_action_accuracy(samples)

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
    except Exception:
        pass

    if not rows:
        rows.append({
            "Dimension": "System",
            "Key": "No observed outcomes",
            "Samples": "0",
            "Calibration": "",
            "Error": "",
            "Direction Acc": "",
            "Success Rate": "",
        })

    df = pd.DataFrame(rows)

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(df.columns)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)

    return len(df)
