from __future__ import annotations

import logging
import zlib
from collections import Counter, defaultdict
from typing import Any

from ozon_agent.api.ozon_client import create_client
from ozon_agent.supply.cities import canonical_supply_city
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.fbo import FboPlanningEngine
from ozon_agent.supply.models import ProposalStatus, SupplyProposal
from ozon_agent.supply.planning import SupplyPlanningEngine
from ozon_agent.supply.proposals import ProposalManager
from ozon_agent.supply.repository import get_proposal_by_draft_id, list_proposals

logger = logging.getLogger(__name__)

_ACTIONABLE_STATUSES = (
    ProposalStatus.PROPOSED,
    ProposalStatus.OWNER_APPROVED,
    ProposalStatus.DRAFT_CREATED,
    ProposalStatus.SUPPLY_CREATED,
)

_STATUS_PRIORITY = {
    ProposalStatus.PROPOSED: 5,
    ProposalStatus.OWNER_APPROVED: 4,
    ProposalStatus.DRAFT_CREATED: 3,
    ProposalStatus.SUPPLY_CREATED: 2,
    ProposalStatus.FAILED: 1,
    ProposalStatus.REJECTED: 0,
}


def _supply_help() -> str:
    return (
        "Supply API\n\n"
        "Основные команды:\n"
        "/supply fbo - показать рекомендации FBO\n"
        "/supply fbo-propose - создать предложения\n"
        "/supply proposals - список предложений\n"
        "/supply latest - последнее предложение\n"
        "/supply latest-approve - подтвердить последнее предложение\n"
        "/supply latest-create-draft - создать draft по последнему подтверждённому предложению\n"
        "/supply latest-timeslots - показать слоты по последнему draft\n"
        "/supply latest-book-first - забронировать первый доступный слот\n\n"
        "Технические команды:\n"
        "/supply warehouses\n"
        "/supply clusters\n"
        "/supply orders\n"
        "/supply approve ID\n"
        "/supply reject ID reason\n"
        "/supply create-draft ID\n"
        "/supply timeslots DRAFT_ID\n"
        "/supply select-timeslot ID SLOT\n"
    )


def _proposal_label(proposal: SupplyProposal) -> str:
    return proposal.offer_id or str(proposal.sku)


def _proposal_city_name(proposal: SupplyProposal) -> str:
    return canonical_supply_city(proposal.target_cluster_name, proposal.target_warehouse_name)


def _proposal_sort_key(proposal: SupplyProposal) -> tuple[int, Any]:
    return (_STATUS_PRIORITY.get(proposal.status, -1), proposal.created_at)


def _render_cluster_lines(items: list[tuple[str, str, int]], title: str) -> str:
    if not items:
        return title + "\n\nНет данных."

    grouped: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for city_name, label, qty in items:
        grouped[city_name][label] += qty

    lines = [title, ""]
    for city_name in sorted(grouped):
        city_items = sorted(grouped[city_name].items(), key=lambda row: (-row[1], row[0]))
        sku_count = len(city_items)
        total_qty = sum(qty for _label, qty in city_items)
        lines.append(f"{city_name} — {sku_count} SKU, всего {total_qty} шт")
        for label, qty in city_items[:12]:
            lines.append(f"- {label} — {qty}")
        lines.append("")
    return "\n".join(lines).strip()


def _proposal_cluster_summary(proposals: list[SupplyProposal], title: str) -> str:
    items = [
        (_proposal_city_name(proposal), _proposal_label(proposal), int(proposal.quantity))
        for proposal in proposals
        if int(proposal.quantity or 0) > 0
    ]
    return _render_cluster_lines(items, title)


def _latest_distinct_proposals(
    proposals: list[SupplyProposal],
    city_name: str | None = None,
    statuses: tuple[ProposalStatus, ...] | None = None,
) -> list[SupplyProposal]:
    filtered = proposals
    if city_name:
        filtered = [proposal for proposal in filtered if _proposal_city_name(proposal) == city_name]
    if statuses:
        filtered = [proposal for proposal in filtered if proposal.status in statuses]

    latest: dict[tuple[str, str], SupplyProposal] = {}
    for proposal in filtered:
        key = (_proposal_city_name(proposal), _proposal_label(proposal))
        current = latest.get(key)
        if current is None or _proposal_sort_key(proposal) > _proposal_sort_key(current):
            latest[key] = proposal

    return sorted(
        latest.values(),
        key=lambda proposal: (_proposal_city_name(proposal), -int(proposal.quantity or 0), _proposal_label(proposal)),
    )


def _cluster_names_for_supply() -> list[str]:
    proposals = list_proposals(limit=200)
    actionable = _latest_distinct_proposals(proposals, statuses=_ACTIONABLE_STATUSES)
    return sorted({_proposal_city_name(proposal) for proposal in actionable if _proposal_city_name(proposal)})


def _cluster_token(cluster_name: str) -> str:
    checksum = zlib.crc32(cluster_name.encode("utf-8")) & 0xFFFFFFFF
    return f"c{checksum:08x}"


def _cluster_buttons_for_supply() -> list[tuple[str, str]]:
    return [(_cluster_token(name), name) for name in _cluster_names_for_supply()]


def _cluster_name_from_token(token: str) -> str | None:
    for name in _cluster_names_for_supply():
        if _cluster_token(name) == token:
            return name
    return None


def _fbo_cluster_summary(plans: list[object], title: str) -> str:
    items = [
        (
            canonical_supply_city(getattr(plan, "cluster_name", ""), getattr(plan, "warehouse_name", "")),
            str(getattr(plan, "offer_id", "") or getattr(plan, "sku", "")),
            int(getattr(plan, "recommended_30", 0) or 0),
        )
        for plan in plans
        if int(getattr(plan, "recommended_30", 0) or 0) > 0
    ]
    return _render_cluster_lines(items, title)


def _city_proposals(city_name: str | None = None, statuses: tuple[ProposalStatus, ...] | None = None) -> list[SupplyProposal]:
    proposals = list_proposals(limit=200)
    return _latest_distinct_proposals(proposals, city_name=city_name, statuses=statuses)


def _city_proposal_ids(city_name: str, statuses: tuple[ProposalStatus, ...]) -> list[str]:
    return [str(proposal.proposal_id) for proposal in _city_proposals(city_name, statuses=statuses)]


def _render_city_card(city_name: str) -> str:
    proposals = _city_proposals(city_name, statuses=_ACTIONABLE_STATUSES)
    if not proposals:
        return f"Город: {city_name}\nНет активных SKU для поставки."

    total_qty = sum(int(proposal.quantity or 0) for proposal in proposals)
    status_counts = Counter(proposal.status.value for proposal in proposals)
    latest_with_supply = next(
        (proposal for proposal in proposals if proposal.status in (ProposalStatus.DRAFT_CREATED, ProposalStatus.SUPPLY_CREATED)),
        None,
    )

    lines = [
        f"Город: {city_name}",
        f"SKU в поставке: {len(proposals)}",
        f"Всего к поставке: {total_qty} шт",
        "Горизонт на экране: 30 дней",
        "В Google Sheets доступны 30 / 60 / 90 дней",
        "Статусы:",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    if latest_with_supply:
        lines.append(f"Draft ID: {latest_with_supply.draft_id or 'N/A'}")
        lines.append(f"Supply ID: {latest_with_supply.supply_id or 'N/A'}")
        lines.append(f"Маршрут Ozon: {latest_with_supply.target_warehouse_name}")
    return "\n".join(lines)


def _supply_warehouses() -> str:
    try:
        client = create_client()
        supply_client = SupplyAPIClient(client)
        warehouses = supply_client.list_fbo_warehouses()

        if not warehouses:
            return "No warehouses available."

        lines = [f"Warehouses ({len(warehouses)}):\n"]
        for wh in warehouses[:10]:
            status = "ACTIVE" if wh.is_active else "INACTIVE"
            city_name = canonical_supply_city(wh.cluster_name, wh.name)
            lines.append(f"  {status} {city_name} -> {wh.name} (ID: {wh.warehouse_id})")

        if len(warehouses) > 10:
            lines.append(f"  ... and {len(warehouses) - 10} more")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_clusters() -> str:
    try:
        client = create_client()
        supply_client = SupplyAPIClient(client)
        clusters = supply_client.list_clusters()

        if not clusters:
            return "No clusters available."

        lines = [f"Clusters ({len(clusters)}):\n"]
        for cl in clusters[:10]:
            lines.append(f"  {canonical_supply_city(cl.name)} (ID: {cl.cluster_id}, warehouses: {cl.warehouses_count})")

        if len(clusters) > 10:
            lines.append(f"  ... and {len(clusters) - 10} more")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_orders() -> str:
    try:
        client = create_client()
        supply_client = SupplyAPIClient(client)
        orders = supply_client.list_supply_orders()

        if not orders:
            return "No supply orders found."

        lines = [f"Supply Orders ({len(orders)}):\n"]
        for order in orders[:10]:
            lines.append(f"  {order.supply_id} - {order.status}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_plan() -> str:
    try:
        client = create_client()
        engine = SupplyPlanningEngine(client)
        plans = engine.generate_plans(max_plans=5)

        if not plans:
            return "No plans to generate (insufficient data or no demand)."

        lines = [f"Supply Plans ({len(plans)}):\n"]
        for i, plan in enumerate(plans[:5], 1):
            lines.append(f"{i}. SKU: {plan['sku']}")
            lines.append(f"   Product: {plan['product_name']}")
            lines.append(f"   Quantity: {plan['quantity']}")
            lines.append(f"   Warehouse: {plan['target_warehouse_name']}")
            lines.append(f"   Reason: {plan['reason']}")
            lines.append(f"   Confidence: {plan['confidence']:.0%}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_fbo() -> str:
    try:
        client = create_client()
        engine = FboPlanningEngine(client)
        plans = engine.generate_cluster_demand(max_rows=100)

        if not plans:
            return "No FBO demand rows generated."

        summary = _fbo_cluster_summary(plans, "Что нужно подсортировать сейчас")
        return (
            f"{summary}\n\n"
            "Показан подсорт на 30 дней\n"
            "В таблице есть расчёт на 30 / 60 / 90 дней\n"
            "Таблица: Google Sheets -> FBO Demand\n"
            "Следующий шаг: /supply fbo-propose"
        )
    except Exception as e:
        return f"Error: {e}"


def _supply_proposals(city_name: str | None = None) -> str:
    try:
        actionable = _city_proposals(city_name, statuses=_ACTIONABLE_STATUSES)
        if actionable:
            title = (
                f"Что нужно подсортировать: {city_name} (30 дней)"
                if city_name else
                "Что нужно подсортировать сейчас (30 дней)"
            )
            return _proposal_cluster_summary(actionable[:50], title)

        proposals = _city_proposals(city_name)
        if not proposals:
            return "No supply proposals found."

        title = f"Последние предложения: {city_name}" if city_name else "Последние предложения"
        return _proposal_cluster_summary(proposals[:50], title)
    except Exception as e:
        return f"Error: {e}"


def _fbo_plan_to_supply_plan(plan: object) -> dict[str, object] | None:
    quantity = int(getattr(plan, "recommended_30", 0) or 0)
    if quantity <= 0:
        return None
    city_name = canonical_supply_city(getattr(plan, "cluster_name", ""), getattr(plan, "warehouse_name", ""))
    return {
        "sku": int(str(getattr(plan, "sku", 0) or 0)),
        "offer_id": str(getattr(plan, "offer_id", "")),
        "product_name": str(getattr(plan, "product_name", "")),
        "quantity": quantity,
        "target_warehouse_id": int(getattr(plan, "warehouse_id", 0) or 0),
        "target_warehouse_name": str(getattr(plan, "warehouse_name", "")),
        "target_cluster_id": str(getattr(plan, "cluster_id", "")),
        "target_cluster_name": city_name,
        "reason": (
            f"FBO 30-day city demand coverage for {city_name}; "
            f"stock_days={getattr(plan, 'stock_days', None)}"
        ),
        "expected_prevented_loss": 0.0,
        "confidence": float(getattr(plan, "confidence", 0.0) or 0.0),
        "data_sources": list(getattr(plan, "data_sources", [])),
    }


def _supply_fbo_propose() -> str:
    try:
        client = create_client()
        engine = FboPlanningEngine(client)
        manager = ProposalManager(client)
        fbo_rows = engine.generate_cluster_demand(max_rows=100)
        plans = [p for p in (_fbo_plan_to_supply_plan(row) for row in fbo_rows) if p][:30]
        if not plans:
            return "No FBO proposals to create."
        proposals = manager.create_proposals_from_plans(plans)
        if not proposals:
            return "No new FBO proposals created."

        summary = _proposal_cluster_summary(proposals, f"Созданы предложения: {len(proposals)}")
        return f"{summary}\n\nДальше: выберите город, нажмите Согласовать, затем Создать поставку"
    except Exception as e:
        return f"Error: {e}"


def _supply_propose() -> str:
    try:
        client = create_client()
        engine = SupplyPlanningEngine(client)
        manager = ProposalManager(client)

        plans = engine.generate_plans(max_plans=5)
        proposals = manager.create_proposals_from_plans(plans)

        if not proposals:
            return "No proposals to create."

        lines = [f"Proposals created: {len(proposals)}\n"]
        for proposal in proposals[:5]:
            lines.append(f"  {proposal.proposal_id}")
            lines.append(f"  SKU: {proposal.sku}, Quantity: {proposal.quantity}")
            lines.append(f"  Warehouse: {proposal.target_warehouse_name}")
            lines.append(f"  Status: {proposal.status.value}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _latest_proposal_for_cluster(city_name: str | None, *statuses: ProposalStatus) -> SupplyProposal | None:
    proposals = _city_proposals(city_name, statuses=statuses or None)
    if not proposals:
        return None

    if statuses:
        sorted_proposals = sorted(proposals, key=_proposal_sort_key, reverse=True)
        return sorted_proposals[0] if sorted_proposals else None

    preferred = (
        ProposalStatus.PROPOSED,
        ProposalStatus.OWNER_APPROVED,
        ProposalStatus.DRAFT_CREATED,
        ProposalStatus.SUPPLY_CREATED,
    )
    for status in preferred:
        matching = [proposal for proposal in proposals if proposal.status == status]
        if matching:
            return sorted(matching, key=_proposal_sort_key, reverse=True)[0]

    return sorted(proposals, key=_proposal_sort_key, reverse=True)[0]


def _latest_proposal(*statuses: ProposalStatus) -> SupplyProposal | None:
    return _latest_proposal_for_cluster(None, *statuses)


def _render_proposal(proposal: SupplyProposal) -> str:
    lines = [
        "Latest Proposal:\n",
        f"ID: {proposal.proposal_id}",
        f"City: {_proposal_city_name(proposal)}",
        f"SKU: {proposal.sku}",
        f"Offer: {_proposal_label(proposal)}",
        f"Product: {proposal.product_name}",
        f"Qty: {proposal.quantity}",
        f"Warehouse: {proposal.target_warehouse_name}",
        f"Status: {proposal.status.value}",
        f"Draft ID: {proposal.draft_id or 'N/A'}",
        f"Supply ID: {proposal.supply_id or 'N/A'}",
    ]
    if proposal.timeslot_id:
        lines.append(f"Timeslot: {proposal.timeslot_id}")
    return "\n".join(lines)


def _supply_latest() -> str:
    proposal = _latest_proposal()
    if not proposal:
        return "No supply proposals found."
    return _render_proposal(proposal)


def _supply_latest_approve(user: str) -> str:
    proposal = _latest_proposal(ProposalStatus.PROPOSED)
    if not proposal:
        return "No proposed supply proposal found."
    return _supply_approve(proposal.proposal_id, user)


def _supply_latest_create_draft() -> str:
    proposal = _latest_proposal(ProposalStatus.OWNER_APPROVED)
    if not proposal:
        return "No approved proposal waiting for draft creation."
    return _supply_create_draft(proposal.proposal_id)


def _supply_latest_timeslots() -> str:
    proposal = _latest_proposal(ProposalStatus.DRAFT_CREATED, ProposalStatus.SUPPLY_CREATED)
    if not proposal or not proposal.draft_id:
        return "No draft found for timeslot lookup."
    return _supply_timeslots(str(proposal.draft_id))


def _supply_latest_book_first() -> str:
    proposal = _latest_proposal(ProposalStatus.DRAFT_CREATED)
    if not proposal or not proposal.draft_id:
        return "No draft ready for slot booking."

    client = create_client()
    supply_client = SupplyAPIClient(client)
    try:
        timeslots = supply_client.get_timeslots(
            str(proposal.draft_id),
            cluster_id=proposal.target_cluster_id,
            warehouse_id=int(proposal.target_warehouse_id),
            supply_order_id=str(proposal.supply_id) if proposal.supply_id else None,
        )
    except Exception as e:
        return f"Error: {e}"

    if not timeslots:
        return "No timeslots available for the latest draft."

    first_slot = timeslots[0].timeslot_id
    result = _supply_select_timeslot(proposal.proposal_id, first_slot)
    return f"{result}\nBooked slot: {first_slot}"


def _supply_city_approve(city_name: str, user: str) -> str:
    proposal_ids = _city_proposal_ids(city_name, (ProposalStatus.PROPOSED,))
    if not proposal_ids:
        return f"В городе {city_name} нет новых SKU для согласования."
    client = create_client()
    manager = ProposalManager(client)
    return f"{city_name}: {manager.approve_batch(proposal_ids, user)}"


def _supply_city_create_draft(city_name: str) -> str:
    proposal_ids = _city_proposal_ids(city_name, (ProposalStatus.OWNER_APPROVED,))
    if not proposal_ids:
        return f"В городе {city_name} нет согласованных SKU для создания поставки."
    client = create_client()
    manager = ProposalManager(client)
    return f"{city_name}: {manager.create_draft_batch(proposal_ids)}"


def _city_draft_anchor(city_name: str) -> SupplyProposal | None:
    proposals = _city_proposals(city_name, statuses=(ProposalStatus.DRAFT_CREATED, ProposalStatus.SUPPLY_CREATED))
    draft_ready = [proposal for proposal in proposals if proposal.draft_id]
    if not draft_ready:
        return None
    return sorted(draft_ready, key=_proposal_sort_key, reverse=True)[0]


def _city_batch_ids_for_supply(city_name: str, anchor: SupplyProposal) -> list[str]:
    proposals = _city_proposals(city_name, statuses=(ProposalStatus.DRAFT_CREATED, ProposalStatus.SUPPLY_CREATED))
    result = []
    for proposal in proposals:
        if proposal.supply_id == anchor.supply_id and proposal.draft_id == anchor.draft_id:
            result.append(str(proposal.proposal_id))
    return result


def _supply_city_timeslots(city_name: str) -> str:
    proposal = _city_draft_anchor(city_name)
    if not proposal or not proposal.draft_id:
        return f"В городе {city_name} ещё нет созданной поставки."
    return _supply_timeslots(str(proposal.draft_id))


def _supply_city_book_first(city_name: str) -> str:
    proposal = _city_draft_anchor(city_name)
    if not proposal or not proposal.draft_id:
        return f"В городе {city_name} нет поставки для бронирования слота."

    client = create_client()
    supply_client = SupplyAPIClient(client)
    timeslots = supply_client.get_timeslots(
        str(proposal.draft_id),
        cluster_id=proposal.target_cluster_id,
        warehouse_id=int(proposal.target_warehouse_id),
        supply_order_id=str(proposal.supply_id) if proposal.supply_id else None,
    )
    if not timeslots:
        return f"Для города {city_name} нет доступных слотов."

    manager = ProposalManager(client)
    proposal_ids = _city_batch_ids_for_supply(city_name, proposal)
    result = manager.create_supply_batch(proposal_ids, timeslots[0].timeslot_id)
    return f"{city_name}: {result}\nBooked slot: {timeslots[0].timeslot_id}"


def _supply_approve(proposal_id: str, user: str) -> str:
    try:
        client = create_client()
        manager = ProposalManager(client)
        result = manager.approve_proposal(proposal_id, user)
        return result
    except Exception as e:
        return f"Error: {e}"


def _supply_reject(proposal_id: str, reason: str, user: str) -> str:
    try:
        client = create_client()
        manager = ProposalManager(client)
        result = manager.reject_proposal(proposal_id, reason, user)
        return result
    except Exception as e:
        return f"Error: {e}"


def _supply_create_draft(proposal_id: str) -> str:
    try:
        client = create_client()
        manager = ProposalManager(client)
        return manager.create_draft(proposal_id)
    except Exception as e:
        return f"Error: {e}"


def _supply_timeslots(draft_id: str) -> str:
    try:
        proposal = get_proposal_by_draft_id(draft_id)
        if not proposal:
            return f"No proposal found for draft {draft_id}."

        client = create_client()
        supply_client = SupplyAPIClient(client)
        timeslots = supply_client.get_timeslots(
            draft_id,
            cluster_id=proposal.target_cluster_id,
            warehouse_id=int(proposal.target_warehouse_id),
            supply_order_id=str(proposal.supply_id) if proposal.supply_id else None,
        )

        if not timeslots:
            return f"No timeslots available for draft {draft_id}."

        lines = [f"Timeslots for {draft_id}:\n"]
        for ts in timeslots[:5]:
            lines.append(f"  {ts.timeslot_id}: {ts.date} {ts.time_from}-{ts.time_to}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_select_timeslot(proposal_id: str, timeslot_id: str) -> str:
    try:
        client = create_client()
        manager = ProposalManager(client)
        return manager.create_supply(proposal_id, timeslot_id)
    except Exception as e:
        return f"Error: {e}"


def _handle_supply(parts: list[str]) -> str:
    if len(parts) == 1 or parts[1] == "help":
        return _supply_help()

    cmd = parts[1]

    if cmd == "warehouses":
        return _supply_warehouses()
    elif cmd == "clusters":
        return _supply_clusters()
    elif cmd == "orders":
        return _supply_orders()
    elif cmd == "plan":
        return _supply_plan()
    elif cmd == "fbo":
        return _supply_fbo()
    elif cmd == "fbo-propose":
        return _supply_fbo_propose()
    elif cmd == "proposals":
        return _supply_proposals()
    elif cmd == "propose":
        return _supply_propose()
    elif cmd == "latest":
        return _supply_latest()
    elif cmd == "latest-approve":
        return _supply_latest_approve("telegram_user")
    elif cmd == "latest-create-draft":
        return _supply_latest_create_draft()
    elif cmd == "latest-timeslots":
        return _supply_latest_timeslots()
    elif cmd == "latest-book-first":
        return _supply_latest_book_first()
    elif cmd == "approve" and len(parts) >= 3:
        return _supply_approve(parts[2], "telegram_user")
    elif cmd == "reject" and len(parts) >= 4:
        return _supply_reject(parts[2], parts[3], "telegram_user")
    elif cmd == "create-draft" and len(parts) >= 3:
        return _supply_create_draft(parts[2])
    elif cmd == "timeslots" and len(parts) >= 3:
        return _supply_timeslots(parts[2])
    elif cmd == "select-timeslot" and len(parts) >= 4:
        return _supply_select_timeslot(parts[2], parts[3])
    else:
        return _supply_help()
