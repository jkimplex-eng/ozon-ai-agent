"""Tests for Google Sheets module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from ozon_agent.sheets.format import _col_letter
from ozon_agent.sheets.setup import TABS
from ozon_agent.sheets.sync import get_sync_status, sync_tab


def test_col_letter_single() -> None:
    assert _col_letter(1) == "A"
    assert _col_letter(26) == "Z"


def test_col_letter_double() -> None:
    assert _col_letter(27) == "AA"
    assert _col_letter(52) == "AZ"


def test_col_letter_triple() -> None:
    assert _col_letter(53) == "BA"


def test_tabs_have_required_keys() -> None:
    for tab in TABS:
        assert "name" in tab
        assert "columns" in tab
        assert isinstance(tab["columns"], list)
        assert len(tab["columns"]) > 0


def test_tabs_names() -> None:
    names = [t["name"] for t in TABS]
    assert "Daily Report" in names
    assert "Recommendations" in names
    assert "Market Insights" in names
    assert "Competitors" in names
    assert "Experiments" in names
    assert "Recommendation Memory" in names
    assert "Ingestion Status" in names
    assert "Approvals" in names


def test_tabs_count() -> None:
    assert len(TABS) == 8


def test_get_sync_status_empty() -> None:
    from ozon_agent.sheets import sync
    sync._last_sync.clear()
    status = get_sync_status()
    assert isinstance(status, dict)
    assert len(status) == 0


@patch("ozon_agent.sheets.sync.get_gspread_client")
def test_sync_tab_unknown(mock_client: MagicMock) -> None:
    import pytest
    with pytest.raises(ValueError, match="Unknown tab"):
        sync_tab("Nonexistent Tab")


@patch("ozon_agent.sheets.sync.is_db_available", return_value=False)
@patch("ozon_agent.sheets.sync.open_spreadsheet")
@patch("ozon_agent.sheets.sync.get_gspread_client")
def test_sync_tab_known(
    mock_client: MagicMock,
    mock_open: MagicMock,
    mock_db: MagicMock,
) -> None:
    mock_ws = MagicMock()
    mock_sheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_ws
    mock_open.return_value = mock_sheet

    def fake_exporter(ws: MagicMock, *, use_files: bool = False) -> int:
        return 5

    with patch("ozon_agent.sheets.sync.TAB_EXPORTERS", {"Test Tab": fake_exporter}):
        count = sync_tab("Test Tab")
        assert count == 5


def test_sync_all_requires_google_auth() -> None:
    import pytest

    from ozon_agent.sheets.sync import sync_all

    with pytest.raises((OSError, Exception)):
        sync_all()
