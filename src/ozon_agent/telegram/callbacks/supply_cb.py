"""Supply callback workflow for FBO proposals."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.common import back_to_menu
from ozon_agent.telegram.keyboards.supply_kb import supply_keyboard
from ozon_agent.telegram.supply_handlers import (
    _cluster_buttons_for_supply,
    _cluster_name_from_token,
    _latest_proposal,
    _latest_proposal_for_cluster,
    _render_city_card,
    _supply_city_approve,
    _supply_city_book_first,
    _supply_city_create_draft,
    _supply_city_timeslots,
    _supply_fbo_propose,
    _supply_proposals,
)


@register("supply")
async def handle_supply(query: Any, context: Any, action: str, params: list[str]) -> None:
    del context
    if action == "show":
        await _show_supply(query)
    elif action == "cluster" and params:
        cluster_name = _cluster_name_from_token(params[0])
        await _show_supply(query, cluster_name)
    elif action == "proposals":
        await query.edit_message_text(_supply_proposals(), reply_markup=back_to_menu())
    elif action == "fbo-propose":
        await _show_result(query, _supply_fbo_propose())
    elif action == "city-approve" and params:
        await _show_city_result(query, params[0], _supply_city_approve)
    elif action == "city-create-draft" and params:
        await _show_city_result(query, params[0], _supply_city_create_draft)
    elif action == "city-timeslots" and params:
        await _show_city_result(query, params[0], _supply_city_timeslots)
    elif action == "city-book-first" and params:
        await _show_city_result(query, params[0], _supply_city_book_first)


async def _show_supply(query: Any, cluster_name: str | None = None) -> None:
    proposal = _latest_proposal_for_cluster(cluster_name) if cluster_name else _latest_proposal()
    cluster_buttons = _cluster_buttons_for_supply()
    if cluster_name:
        summary = _supply_proposals(cluster_name)
        city_card = _render_city_card(cluster_name)
        text = (
            "🚚 Поставки FBO\n\n"
            f"{summary}\n\n"
            "Карточка города:\n\n"
            f"{city_card}\n\n"
            "Таблица: Google Sheets -> FBO Demand"
        )
        await query.edit_message_text(
            text,
            reply_markup=supply_keyboard(
                proposal.proposal_id if proposal else None,
                cluster_buttons=cluster_buttons,
                selected_cluster=cluster_name,
            ),
        )
        return

    if not proposal:
        text = (
            "🚚 Поставки FBO\n\n"
            "Пока нет готовых предложений.\n"
            "Нажмите 'Пересчитать FBO', чтобы агент собрал новые рекомендации.\n\n"
            "Таблица: Google Sheets -> FBO Demand"
        )
        await query.edit_message_text(
            text,
            reply_markup=supply_keyboard(cluster_buttons=cluster_buttons),
        )
        return

    text = (
        "🚚 Поставки FBO\n\n"
        f"{_supply_proposals()}\n\n"
        "Выберите город, чтобы согласовать все SKU, создать поставку и забронировать слот.\n\n"
        "Таблица: Google Sheets -> FBO Demand"
    )
    await query.edit_message_text(
        text,
        reply_markup=supply_keyboard(
            proposal.proposal_id,
            cluster_buttons=cluster_buttons,
        ),
    )


async def _show_result(query: Any, result: str) -> None:
    proposal = _latest_proposal()
    await query.edit_message_text(
        result,
        reply_markup=supply_keyboard(
            proposal.proposal_id if proposal else None,
            cluster_buttons=_cluster_buttons_for_supply(),
        ),
    )


async def _show_city_result(query: Any, token: str, handler: Any) -> None:
    city_name = _cluster_name_from_token(token)
    if not city_name:
        await query.edit_message_text(
            "Город не найден. Нажмите 'Поставки' ещё раз.",
            reply_markup=supply_keyboard(cluster_buttons=_cluster_buttons_for_supply()),
        )
        return

    result = handler(city_name, "telegram_button") if handler is _supply_city_approve else handler(city_name)
    proposal = _latest_proposal_for_cluster(city_name)
    text = (
        f"{result}\n\n"
        f"{_render_city_card(city_name)}"
    )
    await query.edit_message_text(
        text,
        reply_markup=supply_keyboard(
            proposal.proposal_id if proposal else None,
            cluster_buttons=_cluster_buttons_for_supply(),
            selected_cluster=city_name,
        ),
    )
