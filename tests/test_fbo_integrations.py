"""Tests for FBO Sheets and Telegram integration."""
from unittest.mock import MagicMock, patch

from ozon_agent.sheets.exporters.fbo_demand import EXPORT_COLS, _empty_df, export_fbo_demand
from ozon_agent.sheets.sync import TAB_EXPORTERS
from ozon_agent.supply.models import ProposalStatus
from ozon_agent.telegram.callbacks import supply_cb  # noqa: F401
from ozon_agent.telegram.callbacks.router import route_callback_data, route_callback_payload
from ozon_agent.telegram.bot import handle_message
from ozon_agent.telegram.keyboards.supply_kb import supply_keyboard
from ozon_agent.telegram.supply_handlers import _cluster_token, _handle_supply, _latest_proposal


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


def test_supply_callback_show_uses_latest_proposal() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-3"
    proposal.draft_id = None
    with patch("ozon_agent.telegram.callbacks.supply_cb._latest_proposal", return_value=proposal):
        with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_buttons_for_supply", return_value=[("c1", "Москва")]):
            with patch("ozon_agent.telegram.callbacks.supply_cb._current_fbo_summary", return_value="Москва — 1 SKU, всего 5 шт"):
                response = route_callback_data("supply.show")

    assert response is not None
    assert "Выберите город" in response


def test_supply_callback_approve_routes_to_button_user() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-4"
    proposal.draft_id = None
    with patch("ozon_agent.telegram.callbacks.supply_cb._supply_city_approve", return_value="Москва: Approved 2 proposals; already ready: 0") as approve:
        with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_name_from_token", return_value="Москва"):
            with patch("ozon_agent.telegram.callbacks.supply_cb._latest_proposal_for_cluster", return_value=proposal):
                with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_buttons_for_supply", return_value=[("c1", "Москва")]):
                    with patch("ozon_agent.telegram.callbacks.supply_cb._render_city_card", return_value="Город: Москва"):
                        response = route_callback_data("supply.city-approve|c1")

    assert response is not None
    assert "Approved 2 proposals" in response
    approve.assert_called_once_with("Москва", "telegram_button")


def test_supply_callback_payload_preserves_keyboard() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-5"
    proposal.draft_id = None
    with patch("ozon_agent.telegram.callbacks.supply_cb._latest_proposal", return_value=proposal):
        with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_buttons_for_supply", return_value=[("c1", "Москва")]):
            with patch("ozon_agent.telegram.callbacks.supply_cb._current_fbo_summary", return_value="Москва — 1 SKU, всего 5 шт"):
                text, reply_markup = route_callback_payload("supply.show")

    assert text is not None
    assert reply_markup is not None


def test_latest_proposal_prefers_actionable_over_failed() -> None:
    failed = MagicMock()
    failed.status = ProposalStatus.FAILED
    proposed = MagicMock()
    proposed.status = ProposalStatus.PROPOSED
    with patch("ozon_agent.telegram.supply_handlers.list_proposals", return_value=[failed, proposed]):
        proposal = _latest_proposal()

    assert proposal is proposed


def test_supply_proposals_groups_by_cluster_and_offer() -> None:
    p1 = MagicMock()
    p1.status = ProposalStatus.PROPOSED
    p1.target_cluster_name = "Москва"
    p1.offer_id = "SJ11"
    p1.sku = 111
    p1.quantity = 70

    p2 = MagicMock()
    p2.status = ProposalStatus.PROPOSED
    p2.target_cluster_name = "Москва"
    p2.offer_id = "SJ28"
    p2.sku = 222
    p2.quantity = 30

    with patch("ozon_agent.telegram.supply_handlers.list_proposals", return_value=[p1, p2]):
        from ozon_agent.telegram.supply_handlers import _supply_proposals
        text = _supply_proposals()

    assert "Москва — 2 SKU, всего 100 шт" in text
    assert "SJ11 — 70" in text
    assert "SJ28 — 30" in text


def test_supply_proposals_filters_selected_cluster() -> None:
    p1 = MagicMock()
    p1.status = ProposalStatus.PROPOSED
    p1.target_cluster_name = "Москва"
    p1.offer_id = "SJ11"
    p1.sku = 111
    p1.quantity = 70

    p2 = MagicMock()
    p2.status = ProposalStatus.PROPOSED
    p2.target_cluster_name = "Казань"
    p2.offer_id = "SJ28"
    p2.sku = 222
    p2.quantity = 30

    with patch("ozon_agent.telegram.supply_handlers.list_proposals", return_value=[p1, p2]):
        from ozon_agent.telegram.supply_handlers import _supply_proposals
        text = _supply_proposals("Москва")

    assert "Москва — 1 SKU, всего 70 шт" in text
    assert "SJ11 — 70" in text
    assert "Казань" not in text


def test_supply_cluster_callback_uses_cluster_summary() -> None:
    proposal = MagicMock()
    proposal.proposal_id = "p-cluster"
    proposal.draft_id = None
    token = _cluster_token("Москва")
    with patch("ozon_agent.telegram.callbacks.supply_cb._latest_proposal_for_cluster", return_value=proposal):
        with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_name_from_token", return_value="Москва"):
            with patch("ozon_agent.telegram.callbacks.supply_cb._cluster_buttons_for_supply", return_value=[(token, "Москва"), ("c2", "Казань")]):
                with patch("ozon_agent.telegram.callbacks.supply_cb._current_fbo_summary", return_value="Москва — 2 SKU, всего 16 шт"):
                    with patch("ozon_agent.telegram.callbacks.supply_cb._render_city_card", return_value="Город: Москва"):
                        response = route_callback_data(f"supply.cluster|{token}")

    assert response is not None
    assert "Москва — 2 SKU, всего 16 шт" in response
    assert "Город: Москва" in response


def test_supply_keyboard_callback_data_stays_within_telegram_limit() -> None:
    markup = supply_keyboard(
        proposal_id="p-6",
        cluster_buttons=[(_cluster_token("ЕКАТЕРИНБУРГ_РФЦ_НОВЫЙ_ВОЗВРАТЫ"), "ЕКАТЕРИНБУРГ_РФЦ_НОВЫЙ_ВОЗВРАТЫ")],
    )

    for row in markup.inline_keyboard:
        for button in row:
            callback_data = getattr(button, "callback_data", None)
            if callback_data:
                assert len(callback_data.encode("utf-8")) <= 64
