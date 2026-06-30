"""Supply callback workflow for FBO proposals."""
from __future__ import annotations

from typing import Any

from ozon_agent.supply.models import ProposalStatus
from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.common import back_to_menu
from ozon_agent.telegram.keyboards.supply_kb import supply_keyboard
from ozon_agent.telegram.supply_handlers import (
    _cluster_names_for_supply,
    _latest_proposal,
    _latest_proposal_for_cluster,
    _render_proposal,
    _supply_approve,
    _supply_create_draft,
    _supply_fbo_propose,
    _supply_proposals,
    _supply_select_timeslot,
    _supply_timeslots,
)


@register("supply")
async def handle_supply(query: Any, context: Any, action: str, params: list[str]) -> None:
    del context
    if action == "show":
        await _show_supply(query)
    elif action == "cluster" and params:
        await _show_supply(query, params[0])
    elif action == "proposals":
        await query.edit_message_text(_supply_proposals(), reply_markup=back_to_menu())
    elif action == "fbo-propose":
        await _show_result(query, _supply_fbo_propose())
    elif action == "approve" and params:
        await _show_result(query, _supply_approve(params[0], "telegram_button"))
    elif action == "create-draft" and params:
        await _show_result(query, _supply_create_draft(params[0]))
    elif action == "timeslots" and params:
        await _show_timeslots(query, params[0])
    elif action == "book-first" and params:
        await _book_first(query, params[0])


async def _show_supply(query: Any, cluster_name: str | None = None) -> None:
    proposal = _latest_proposal_for_cluster(cluster_name) if cluster_name else _latest_proposal()
    cluster_names = _cluster_names_for_supply()
    if not proposal:
        text = (
            "🚚 Поставки FBO\n\n"
            "Пока нет готовых предложений.\n"
            "Нажмите 'Пересчитать FBO', чтобы агент собрал новые рекомендации.\n\n"
            "Таблица: Google Sheets -> FBO Demand"
        )
        await query.edit_message_text(
            text,
            reply_markup=supply_keyboard(cluster_names=cluster_names, selected_cluster=cluster_name),
        )
        return

    text = (
        "🚚 Поставки FBO\n\n"
        f"{_supply_proposals(cluster_name)}\n\n"
        "Текущая карточка для действий:\n\n"
        f"{_render_proposal(proposal)}\n\n"
        "Таблица: Google Sheets -> FBO Demand"
    )
    await query.edit_message_text(
        text,
        reply_markup=supply_keyboard(
            proposal.proposal_id,
            cluster_names=cluster_names,
            selected_cluster=cluster_name,
        ),
    )


async def _show_result(query: Any, result: str) -> None:
    proposal = _latest_proposal()
    await query.edit_message_text(
        result,
        reply_markup=supply_keyboard(
            proposal.proposal_id if proposal else None,
            cluster_names=_cluster_names_for_supply(),
        ),
    )


async def _show_timeslots(query: Any, proposal_id: str) -> None:
    proposal = _latest_proposal()
    if not proposal or proposal.proposal_id != proposal_id or not proposal.draft_id:
        await query.edit_message_text(
            "Сначала нужно создать поставку, затем можно смотреть слоты.",
            reply_markup=supply_keyboard(proposal_id, cluster_names=_cluster_names_for_supply()),
        )
        return

    text = _supply_timeslots(str(proposal.draft_id))
    await query.edit_message_text(
        text,
        reply_markup=supply_keyboard(proposal.proposal_id, cluster_names=_cluster_names_for_supply()),
    )


async def _book_first(query: Any, proposal_id: str) -> None:
    proposal = _latest_proposal(ProposalStatus.DRAFT_CREATED)
    if not proposal or proposal.proposal_id != proposal_id or not proposal.draft_id:
        await query.edit_message_text(
            "Нет готовой поставки для бронирования слота.",
            reply_markup=supply_keyboard(proposal_id, cluster_names=_cluster_names_for_supply()),
        )
        return

    timeslots_text = _supply_timeslots(str(proposal.draft_id))
    slot_lines = [
        line.strip()
        for line in timeslots_text.splitlines()
        if line.strip() and ":" in line and line.strip()[0].isdigit()
    ]
    if not slot_lines:
        await query.edit_message_text(
            timeslots_text,
            reply_markup=supply_keyboard(proposal.proposal_id, cluster_names=_cluster_names_for_supply()),
        )
        return

    timeslot_id = slot_lines[0].split(":", 1)[0].strip()
    result = _supply_select_timeslot(proposal.proposal_id, timeslot_id)
    await query.edit_message_text(
        result,
        reply_markup=supply_keyboard(proposal.proposal_id, cluster_names=_cluster_names_for_supply()),
    )
