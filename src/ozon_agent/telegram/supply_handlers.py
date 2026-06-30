from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ozon_agent.api.ozon_client import create_client
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


def _render_cluster_lines(items: list[tuple[str, str, int]], title: str) -> str:
    if not items:
        return title + "\n\nНет данных."

    grouped: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for cluster_name, label, qty in items:
        grouped[cluster_name].append((label, qty))

    lines = [title, ""]
    for cluster_name in sorted(grouped):
        lines.append(f"{cluster_name}")
        for label, qty in sorted(grouped[cluster_name], key=lambda row: (-row[1], row[0]))[:12]:
            lines.append(f"- {label} - {qty} шт")
        lines.append("")
    return "\n".join(lines).strip()


def _proposal_cluster_summary(proposals: list[SupplyProposal], title: str) -> str:
    items = [
        (proposal.target_cluster_name, _proposal_label(proposal), int(proposal.quantity))
        for proposal in proposals
        if int(proposal.quantity or 0) > 0
    ]
    return _render_cluster_lines(items, title)


def _fbo_cluster_summary(plans: list[object], title: str) -> str:
    items = [
        (
            str(getattr(plan, "cluster_name", "")),
            str(getattr(plan, "offer_id", "") or getattr(plan, "sku", "")),
            int(getattr(plan, "recommended_30", 0) or 0),
        )
        for plan in plans
        if int(getattr(plan, "recommended_30", 0) or 0) > 0
    ]
    return _render_cluster_lines(items, title)


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
            lines.append(f"  {status} {wh.name} (ID: {wh.warehouse_id})")

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
            lines.append(f"  {cl.name} (ID: {cl.cluster_id}, warehouses: {cl.warehouses_count})")

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

        summary = _fbo_cluster_summary(plans, "Что нужно подсортировать по кластерам")
        return (
            f"{summary}\n\n"
            "Горизонт: 30 дней\n"
            "Таблица: Google Sheets -> FBO Demand\n"
            "Следующий шаг: /supply fbo-propose"
        )
    except Exception as e:
        return f"Error: {e}"


def _supply_proposals() -> str:
    try:
        proposals = list_proposals(limit=50)
        if not proposals:
            return "No supply proposals found."

        actionable = [proposal for proposal in proposals if proposal.status in _ACTIONABLE_STATUSES]
        if actionable:
            return _proposal_cluster_summary(actionable[:30], "Что нужно подсортировать сейчас")

        return _proposal_cluster_summary(proposals[:20], "Последние предложения")
    except Exception as e:
        return f"Error: {e}"


def _fbo_plan_to_supply_plan(plan: object) -> dict[str, object] | None:
    quantity = int(getattr(plan, "recommended_30", 0) or 0)
    if quantity <= 0:
        return None
    return {
        "sku": int(str(getattr(plan, "sku", 0) or 0)),
        "offer_id": str(getattr(plan, "offer_id", "")),
        "product_name": str(getattr(plan, "product_name", "")),
        "quantity": quantity,
        "target_warehouse_id": int(getattr(plan, "warehouse_id", 0) or 0),
        "target_warehouse_name": str(getattr(plan, "warehouse_name", "")),
        "target_cluster_id": str(getattr(plan, "cluster_id", "")),
        "target_cluster_name": str(getattr(plan, "cluster_name", "")),
        "reason": (
            f"FBO 30-day demand coverage for {getattr(plan, 'cluster_name', '')}; "
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
        return f"{summary}\n\nДальше: нажмите Согласовать, затем Создать поставку"
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
        for p in proposals[:5]:
            lines.append(f"  {p.proposal_id}")
            lines.append(f"  SKU: {p.sku}, Quantity: {p.quantity}")
            lines.append(f"  Warehouse: {p.target_warehouse_name}")
            lines.append(f"  Status: {p.status.value}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _latest_proposal(*statuses: ProposalStatus) -> SupplyProposal | None:
    proposals = list_proposals(limit=50)
    if not proposals:
        return None

    if statuses:
        for proposal in proposals:
            if proposal.status in statuses:
                return proposal
        return None

    preferred = (
        ProposalStatus.PROPOSED,
        ProposalStatus.OWNER_APPROVED,
        ProposalStatus.DRAFT_CREATED,
        ProposalStatus.SUPPLY_CREATED,
    )
    for status in preferred:
        for proposal in proposals:
            if proposal.status == status:
                return proposal

    return proposals[0]


def _render_proposal(proposal: SupplyProposal) -> str:
    lines = [
        "Latest Proposal:\n",
        f"ID: {proposal.proposal_id}",
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
