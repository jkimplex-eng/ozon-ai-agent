"""Tests for management workbook core tab exporters."""
from __future__ import annotations

from unittest.mock import patch

from ozon_agent.sheets.exporters.daily_control import (
    _empty_df as _control_empty,
)
from ozon_agent.sheets.exporters.daily_control import (
    _load_from_files as _control_files,
)
from ozon_agent.sheets.exporters.daily_input import (
    _empty_df as _input_empty,
)
from ozon_agent.sheets.exporters.daily_input import (
    _load_from_files as _input_files,
)
from ozon_agent.sheets.exporters.daily_summary import (
    _empty_df as _summary_empty,
)
from ozon_agent.sheets.exporters.daily_summary import (
    _load_from_files as _summary_files,
)
from ozon_agent.sheets.exporters.products import (
    _empty_df as _products_empty,
)
from ozon_agent.sheets.exporters.products import (
    _load_from_files as _products_files,
)
from ozon_agent.sheets.exporters.stocks import (
    _empty_df as _stocks_empty,
)
from ozon_agent.sheets.exporters.stocks import (
    _load_from_files as _stocks_files,
)
from ozon_agent.sheets.setup import TABS


def test_setup_has_13_tabs() -> None:
    assert len(TABS) == 13


def test_setup_tab_names() -> None:
    names = [t["name"] for t in TABS]
    assert "Products" in names
    assert "Stocks" in names
    assert "Daily Summary" in names
    assert "Daily Control" in names
    assert "Daily Input" in names


def test_products_empty_df() -> None:
    df = _products_empty()
    assert len(df) == 0
    assert "name" in df.columns
    assert "sku" in df.columns


def test_products_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_products", return_value=[]):
        result = _products_files()
        assert result is None


def test_products_load_from_files_with_data() -> None:
    products = [{"name": "Product 1", "sku": "SKU-1", "offer_id": "off-1", "price": 100}]
    with patch("ozon_agent.sheets.file_source.load_products", return_value=products):
        result = _products_files()
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["sku"] == "SKU-1"


def test_stocks_empty_df() -> None:
    df = _stocks_empty()
    assert len(df) == 0
    assert "stock" in df.columns


def test_stocks_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_products", return_value=[]):
        result = _stocks_files()
        assert result is None


def test_stocks_load_from_files_with_data() -> None:
    products = [{"name": "P1", "sku": "SKU-1", "offer_id": "off-1", "stock": 50}]
    with patch("ozon_agent.sheets.file_source.load_products", return_value=products):
        result = _stocks_files()
        assert result is not None
        assert len(result) == 1


def test_daily_summary_empty_df() -> None:
    df = _summary_empty()
    assert len(df) == 0
    assert "revenue" in df.columns
    assert "drr" in df.columns


def test_daily_summary_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=[]):
        result = _summary_files()
        assert result is None


def test_daily_summary_load_from_files_with_data() -> None:
    sales = [{"date": "2026-06-19", "revenue": 10000, "quantity": 50}]
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=sales), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]):
        result = _summary_files()
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["revenue"] == 10000


def test_daily_control_empty_df() -> None:
    df = _control_empty()
    assert len(df) == 0
    assert "gross_profit" in df.columns
    assert "status" in df.columns


def test_daily_control_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=[]):
        result = _control_files()
        assert result is None


def test_daily_control_load_from_files_with_data() -> None:
    sales = [{"date": "2026-06-19", "revenue": 10000, "quantity": 50}]
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=sales), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]):
        result = _control_files()
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["status"] == "OK"


def test_daily_input_empty_df() -> None:
    df = _input_empty()
    assert len(df) == 0
    assert "commission" in df.columns
    assert "run_rate" in df.columns


def test_daily_input_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=[]):
        result = _input_files()
        assert result is None


def test_daily_input_load_from_files_with_data() -> None:
    sales = [{"date": "2026-06-19", "revenue": 10000, "quantity": 50}]
    with patch("ozon_agent.sheets.file_source.load_sales", return_value=sales), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]):
        result = _input_files()
        assert result is not None
        assert len(result) == 1
        assert "OK" in result.iloc[0]["status"] or "BELOW" in result.iloc[0]["status"]


def test_tab_colors_defined() -> None:
    from ozon_agent.sheets.setup import _tab_color
    for tab in TABS:
        color = _tab_color(tab["name"])
        assert "red" in color
        assert "green" in color
        assert "blue" in color
