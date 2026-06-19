"""Export competitor data to Competitors tab."""
from __future__ import annotations

import gspread
import pandas as pd

from ozon_agent.sheets.format import apply_header_format, auto_resize_columns, freeze_header


def export_competitors(ws: gspread.Worksheet) -> int:
    from gspread_dataframe import set_with_dataframe

    rows: list[dict[str, str]] = []

    try:
        from ozon_agent.db.connection import execute_query

        products = execute_query("SELECT sku, name, price FROM products LIMIT 100")
        for p in products:
            rows.append({
                "SKU": p.get("sku", ""),
                "Category": "",
                "Revenue 30d": "",
                "GMV 30d": "",
                "Rating": "",
                "Reviews": "",
                "Price": str(p.get("price", "")),
                "Verdict": "N/A",
                "Date": "",
            })
    except Exception:
        pass

    if not rows:
        rows.append({
            "SKU": "",
            "Category": "",
            "Revenue 30d": "",
            "GMV 30d": "",
            "Rating": "",
            "Reviews": "",
            "Price": "",
            "Verdict": "No data",
            "Date": "",
        })

    df = pd.DataFrame(rows)

    ws.clear()
    set_with_dataframe(ws, df, include_column_header=True, allow_formulas=False)

    num_cols = len(df.columns)
    apply_header_format(ws, num_cols)
    freeze_header(ws)
    auto_resize_columns(ws)

    return len(df)
