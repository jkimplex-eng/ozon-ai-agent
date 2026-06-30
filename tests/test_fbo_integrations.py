"""Tests for FBO Sheets and Telegram integration."""
from unittest.mock import MagicMock, patch

from ozon_agent.sheets.exporters.fbo_demand import EXPORT_COLS, _empty_df, export_fbo_demand
from ozon_agent.sheets.sync import TAB_EXPORTERS
from ozon_agent.telegram.bot import handle_message
from ozon_agent.telegram.supply_handlers import _handle_supply


def test_fbo_demand_exporter_registered() -> None:
    assert "FBO Demand" in TAB_EXPORTERS


def test_fbo_empty_df_has_export_columns() -> None:
    assert list(_empty_df().columns) == EXPORT_COLS


def test_export_fbo_demand_use_files_skips_api() -> None:
    ws = MagicMock()
    ws.row_count = 100
    ws.col_count = len(EXPORT_COLS)
    with patch("ozon_agent.sheets.exporters.fbo_demand._load_from_db") as mock_load:
        count = export_fbo_demand(ws, use_files=True)

    assert count == 1
    mock_load.assert_not_called()
    ws.clear.assert_called_once()


def test_telegram_supply_fbo_routes_to_supply_handler() -> None:
    with patch("ozon_agent.telegram.bot._handle_supply", return_value="FBO Demand ok") as handler:
        response = handle_message("/supply fbo", "user")

    assert response == "FBO Demand ok"
    handler.assert_called_once()


def test_supply_latest_approve_uses_latest_proposed() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-1"
    with patch("ozon_agent.telegram.supply_handlers._latest_proposal", return_value=proposal):
        with patch("ozon_agent.telegram.supply_handlers._supply_approve", return_value="approved") as approve:
            response = _handle_supply(["/supply", "latest-approve"])

    assert response == "approved"
    approve.assert_called_once_with("p-1", "telegram_user")


def test_supply_latest_create_draft_uses_latest_owner_approved() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-2"
    with patch("ozon_agent.telegram.supply_handlers._latest_proposal", return_value=proposal):
        with patch("ozon_agent.telegram.supply_handlers._supply_create_draft", return_value="draft ok") as create_draft:
            response = _handle_supply(["/supply", "latest-create-draft"])

    assert response == "draft ok"
    create_draft.assert_called_once_with("p-2")
