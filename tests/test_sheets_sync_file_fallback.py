"""Tests for Google Sheets sync without PostgreSQL."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from ozon_agent.sheets.file_source import has_any_file_data
from ozon_agent.sheets.sync import _load_sync_status, _resolve_source, _save_sync_status


def test_resolve_source_files_explicit() -> None:
    assert _resolve_source("files") is True


def test_resolve_source_db_explicit() -> None:
    assert _resolve_source("db") is False


def test_resolve_source_env_files() -> None:
    import os
    os.environ["SHEETS_DATA_SOURCE"] = "files"
    try:
        assert _resolve_source(None) is True
    finally:
        del os.environ["SHEETS_DATA_SOURCE"]


def test_resolve_source_env_db() -> None:
    import os
    os.environ["SHEETS_DATA_SOURCE"] = "db"
    try:
        assert _resolve_source(None) is False
    finally:
        del os.environ["SHEETS_DATA_SOURCE"]


def test_resolve_source_auto_db_unavailable() -> None:
    with patch("ozon_agent.sheets.sync.is_db_available", return_value=False):
        assert _resolve_source(None) is True


def test_resolve_source_auto_db_available() -> None:
    with patch("ozon_agent.sheets.sync.is_db_available", return_value=True):
        assert _resolve_source(None) is False


def test_resolve_source_auto_db_import_error() -> None:
    with patch(
        "ozon_agent.sheets.sync.is_db_available",
        side_effect=ImportError("no psycopg"),
    ):
        assert _resolve_source(None) is True


def test_file_source_has_any_file_data_false() -> None:
    with patch("ozon_agent.sheets.file_source.load_products", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_sales", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_market_insights", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_experiments", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_memory_records", return_value=[]):
        assert has_any_file_data() is False


def test_file_source_has_any_file_data_true() -> None:
    with patch("ozon_agent.sheets.file_source.load_products", return_value=[{"sku": "X"}]), \
         patch("ozon_agent.sheets.file_source.load_sales", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_market_insights", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_experiments", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_memory_records", return_value=[]):
        assert has_any_file_data() is True


def test_daily_report_empty_df() -> None:
    from ozon_agent.sheets.exporters.daily_report import _empty_df
    df = _empty_df()
    assert len(df) == 0
    assert "sku" in df.columns
    assert "revenue" in df.columns


def test_daily_report_load_from_db_fails_gracefully() -> None:
    with patch("ozon_agent.db.connection.execute_query", side_effect=Exception("conn")):
        from ozon_agent.sheets.exporters.daily_report import _load_from_db
        result = _load_from_db()
        assert result is None


def test_daily_report_load_from_files_empty() -> None:
    with patch("ozon_agent.sheets.file_source.load_products", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_sales", return_value=[]), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=[]):
        from ozon_agent.sheets.exporters.daily_report import _load_from_files
        result = _load_from_files()
        assert result is None


def test_daily_report_load_from_files_with_data() -> None:
    products = [{"sku": "SKU-1", "name": "Product 1"}]
    sales = [{"sku": "SKU-1", "revenue": 1000, "quantity": 10, "date": "2026-01-01"}]
    advertising = [{"sku": "SKU-1", "spend": 100}]
    with patch("ozon_agent.sheets.file_source.load_products", return_value=products), \
         patch("ozon_agent.sheets.file_source.load_sales", return_value=sales), \
         patch("ozon_agent.sheets.file_source.load_advertising", return_value=advertising):
        from ozon_agent.sheets.exporters.daily_report import _load_from_files
        result = _load_from_files()
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["sku"] == "SKU-1"
        assert result.iloc[0]["product"] == "Product 1"
        assert result.iloc[0]["revenue"] == 1000


def test_ingestion_status_empty_df() -> None:
    from ozon_agent.sheets.exporters.ingestion_status import _empty_df
    df = _empty_df()
    assert len(df) == 1
    assert df.iloc[0]["Status"] == "NO DATA"


def test_market_insights_no_data_row() -> None:
    from ozon_agent.sheets.exporters.market_insights import _no_data_row
    rows = _no_data_row()
    assert len(rows) == 1
    assert "NO DATA" in rows[0]["Insight"]


def test_export_daily_report_use_files_skips_db() -> None:
    with patch("ozon_agent.sheets.exporters.daily_report._load_from_db") as mock_db, \
         patch("ozon_agent.sheets.exporters.daily_report._load_from_files") as mock_files:
        mock_db.return_value = None
        mock_files.return_value = None
        from ozon_agent.sheets.exporters.daily_report import export_daily_report
        mock_ws = MagicMock()
        mock_ws.row_count = 100
        mock_ws.col_count = 12
        count = export_daily_report(mock_ws, use_files=True)
        assert count == 0
        mock_db.assert_not_called()


def test_export_experiments_use_files_skips_db() -> None:
    with patch("ozon_agent.sheets.exporters.experiments._load_from_db") as mock_db, \
         patch("ozon_agent.sheets.exporters.experiments._load_from_files") as mock_files:
        mock_files.return_value = None
        from ozon_agent.sheets.exporters.experiments import export_experiments
        mock_ws = MagicMock()
        mock_ws.row_count = 100
        mock_ws.col_count = 13
        mock_ws.id = "sheet123"
        mock_ws.row_values.return_value = ["col1", "col2"]
        export_experiments(mock_ws, use_files=True)
        mock_db.assert_not_called()


def test_sync_status_persistence() -> None:
    from ozon_agent.sheets.sync import _SYNC_STATUS_FILE

    _SYNC_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _save_sync_status({"Daily Report": "2026-01-01T00:00:00"})

    loaded = _load_sync_status()
    assert loaded["Daily Report"] == "2026-01-01T00:00:00"

    _save_sync_status({"Daily Report": "2026-01-01T00:00:00", "Recommendations": "2026-01-02"})
    loaded = _load_sync_status()
    assert len(loaded) == 2
    assert loaded["Recommendations"] == "2026-01-02"

    _SYNC_STATUS_FILE.unlink(missing_ok=True)


def test_sync_status_load_missing_file() -> None:
    from ozon_agent.sheets.sync import _SYNC_STATUS_FILE

    if _SYNC_STATUS_FILE.exists():
        _SYNC_STATUS_FILE.unlink()

    loaded = _load_sync_status()
    assert loaded == {}


def test_sync_status_load_corrupt_file() -> None:
    from ozon_agent.sheets.sync import _SYNC_STATUS_FILE

    _SYNC_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SYNC_STATUS_FILE.write_text("not json {{{", encoding="utf-8")

    loaded = _load_sync_status()
    assert loaded == {}

    _SYNC_STATUS_FILE.unlink(missing_ok=True)
