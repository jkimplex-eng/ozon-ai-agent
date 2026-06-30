from __future__ import annotations

import logging
from typing import Any

from ozon_agent.api.ozon_client import create_client
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.fbo import FboPlanningEngine
from ozon_agent.supply.planning import SupplyPlanningEngine
from ozon_agent.supply.proposals import ProposalManager
from ozon_agent.supply.models import ProposalStatus
from ozon_agent.supply.repository import list_proposals

logger = logging.getLogger(__name__)


def _supply_help() -> str:
    return (
        "Supply API\n\n"
        "Commands:\n"
        "/supply warehouses - list warehouses\n"
        "/supply clusters - list clusters\n"
        "/supply orders - list orders\n"
        "/supply plan - generate plans\n"
        "/supply fbo - FBO demand 30/60/90 by cluster\n"
        "/supply propose - create proposals\n"
        "/supply approve ID - approve\n"
        "/supply reject ID reason - reject\n"
        "/supply create-draft ID - create draft\n"
        "/supply timeslots DRAFT_ID - show timeslots\n"
        "/supply select-timeslot ID SLOT - select timeslot\n"
    )


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
        plans = engine.generate_cluster_demand(max_rows=10)

        if not plans:
            return "No FBO demand rows generated."

        lines = [f"FBO Demand ({len(plans)} rows):\n"]
        for plan in plans[:5]:
            lines.append(f"SKU: {plan.sku} - {plan.product_name}")
            lines.append(f"Cluster: {plan.cluster_name}")
            lines.append(
                "Demand 30/60/90: "
                f"{plan.demand_30}/{plan.demand_60}/{plan.demand_90}"
            )
            lines.append(
                "Recommended 30/60/90: "
                f"{plan.recommended_30}/{plan.recommended_60}/{plan.recommended_90}"
            )
            lines.append(f"Confidence: {plan.confidence:.0%}\n")

        lines.append("Google Sheets tab: FBO Demand")
        lines.append("Slot booking requires approval and --execute.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_proposals() -> str:
    try:
        proposals = list_proposals(limit=10)
        if not proposals:
            return "No supply proposals found."

        lines = [f"Supply Proposals ({len(proposals)}):\n"]
        for proposal in proposals[:10]:
            lines.append(
                f"{proposal.proposal_id} | {proposal.sku} | {proposal.quantity} | {proposal.status.value}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _fbo_plan_to_supply_plan(plan: object) -> dict[str, object] | None:
    quantity = int(getattr(plan, "recommended_30", 0) or 0)
    if quantity <= 0:
        return None
    return {
        "sku": str(getattr(plan, "sku", "")),
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
        fbo_rows = engine.generate_cluster_demand(max_rows=25)
        plans = [p for p in (_fbo_plan_to_supply_plan(row) for row in fbo_rows) if p][:5]
        if not plans:
            return "No FBO proposals to create."
        proposals = manager.create_proposals_from_plans(plans)
        if not proposals:
            return "No new FBO proposals created."

        lines = [f"FBO proposals created: {len(proposals)}\n"]
        for proposal in proposals[:5]:
            lines.append(f"ID: {proposal.proposal_id}")
            lines.append(f"SKU: {proposal.sku}, Qty: {proposal.quantity}")
            lines.append(f"Warehouse: {proposal.target_warehouse_name}")
            lines.append(f"Status: {proposal.status.value}\n")
        lines.append("Approve: /supply approve <proposal_id>")
        return "\n".join(lines)
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
    return (
        f"DRY-RUN MODE\n\n"
        f"To create draft, run:\n"
        f"python -m ozon_agent.cli supply create-draft {proposal_id} --execute\n\n"
        f"This action requires explicit owner approval."
    )


def _supply_timeslots(draft_id: str) -> str:
    try:
        client = create_client()
        supply_client = SupplyAPIClient(client)
        timeslots = supply_client.get_timeslots(draft_id)
        
        if not timeslots:
            return f"No timeslots available for draft {draft_id}."
        
        lines = [f"Timeslots for {draft_id}:\n"]
        for ts in timeslots[:5]:
            lines.append(f"  {ts.timeslot_id}: {ts.date} {ts.time_from}-{ts.time_to}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _supply_select_timeslot(proposal_id: str, timeslot_id: str) -> str:
    return (
        f"DRY-RUN MODE\n\n"
        f"To select timeslot, run:\n"
        f"python -m ozon_agent.cli supply select-timeslot {proposal_id} {timeslot_id} --execute\n\n"
        f"This action requires explicit owner approval."
    )


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
    elif cmd == "propose":
        return _supply_propose()
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



