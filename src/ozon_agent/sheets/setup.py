"""Create Google Spreadsheet with all 8 tabs and formatting."""
from __future__ import annotations

from typing import Any

import gspread

from ozon_agent.sheets.client import create_spreadsheet as create_sheet
from ozon_agent.sheets.client import get_gspread_client
from ozon_agent.sheets.format import (
    add_auto_filter,
    apply_header_format,
    auto_resize_columns,
    freeze_header,
)

TABS: list[dict[str, Any]] = [
    {
        "name": "Daily Report",
        "columns": [
            "SKU", "Product", "Revenue", "Quantity", "Spend",
            "DRR %", "Margin %", "Gross Profit", "Rating", "Reviews",
            "Stock Days", "Date Range",
        ],
        "status_col": None,
    },
    {
        "name": "Recommendations",
        "columns": [
            "ID", "Status", "SKU", "Action", "Confidence",
            "Risk", "Expected Effect", "Reason", "Created", "Approved By",
        ],
        "status_col": 2,
    },
    {
        "name": "Market Insights",
        "columns": [
            "Source", "Type", "Insight", "Confidence", "Category",
            "Relevance", "Date",
        ],
        "status_col": None,
    },
    {
        "name": "Competitors",
        "columns": [
            "SKU", "Category", "Revenue 30d", "GMV 30d", "Rating",
            "Reviews", "Price", "Verdict", "Date",
        ],
        "status_col": 8,
    },
    {
        "name": "Experiments",
        "columns": [
            "ID", "Status", "SKU", "Hypothesis", "Action",
            "Risk", "Confidence", "Baseline Rev", "Current Rev",
            "Success Score", "Direction", "Created", "Lifecycle",
        ],
        "status_col": 2,
    },
    {
        "name": "Recommendation Memory",
        "columns": [
            "Dimension", "Key", "Samples", "Calibration", "Error",
            "Direction Acc", "Success Rate",
        ],
        "status_col": None,
    },
    {
        "name": "Ingestion Status",
        "columns": [
            "Source", "Status", "Rows Fetched", "Rows Inserted",
            "Error", "Started", "Completed",
        ],
        "status_col": 2,
    },
    {
        "name": "Approvals",
        "columns": [
            "ID", "Status", "SKU", "Action", "Confidence",
            "Risk", "Approved By", "Rejected By", "Rejection Reason",
            "Lifecycle", "Created",
        ],
        "status_col": 2,
    },
]


def setup_spreadsheet(title: str = "Ozon AI Agent") -> str:
    """Create a new spreadsheet with all 8 tabs. Returns spreadsheet ID."""
    client = get_gspread_client()
    spreadsheet = create_sheet(client, title)

    for tab_config in TABS:
        _create_tab(spreadsheet, tab_config)

    default_tab = spreadsheet.sheet1
    default_tab.update_title("Daily Report")

    return spreadsheet.id


def _create_tab(spreadsheet: gspread.Spreadsheet, tab_config: dict[str, Any]) -> None:
    """Create a single tab with headers and formatting."""
    worksheet = spreadsheet.add_worksheet(
        title=tab_config["name"],
        rows=1000,
        cols=len(tab_config["columns"]),
    )

    worksheet.update("A1", [tab_config["columns"]])  # type: ignore[arg-type]

    num_cols = len(tab_config["columns"])
    apply_header_format(worksheet, num_cols)
    freeze_header(worksheet)
    auto_resize_columns(worksheet)
    add_auto_filter(worksheet, num_cols)

    worksheet.set_tab_color(_tab_color(tab_config["name"]))  # type: ignore[attr-defined]


def _tab_color(tab_name: str) -> dict[str, float]:
    """Return tab color based on tab name."""
    colors: dict[str, dict[str, float]] = {
        "Daily Report": {"red": 0.2, "green": 0.4, "blue": 0.8},
        "Recommendations": {"red": 0.1, "green": 0.6, "blue": 0.3},
        "Market Insights": {"red": 0.6, "green": 0.3, "blue": 0.8},
        "Competitors": {"red": 0.8, "green": 0.4, "blue": 0.1},
        "Experiments": {"red": 0.9, "green": 0.2, "blue": 0.2},
        "Recommendation Memory": {"red": 0.3, "green": 0.5, "blue": 0.7},
        "Ingestion Status": {"red": 0.5, "green": 0.5, "blue": 0.5},
        "Approvals": {"red": 0.1, "green": 0.5, "blue": 0.5},
    }
    return colors.get(tab_name, {"red": 0.3, "green": 0.3, "blue": 0.3})
