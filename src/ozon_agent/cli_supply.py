"""CLI commands for Supply API discovery and planning."""

import json

import click

from ozon_agent.api.ozon_client import create_client
from ozon_agent.sheets.sync import sync_tab
from ozon_agent.supply.fbo import FboPlanningEngine
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.models import ProposalStatus
from ozon_agent.supply.planning import SupplyPlanningEngine
from ozon_agent.supply.proposals import ProposalManager


@click.group()
def supply() -> None:
    """Supply API commands (warehouses, clusters, planning, proposals)."""
    pass


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


@supply.command()
def warehouses() -> None:
    """List FBO warehouses (READ-ONLY, REAL_DATA)."""
    client = create_client()
    supply_client = SupplyAPIClient(client)

    try:
        warehouses = supply_client.list_fbo_warehouses()

        click.echo("\n📦 FBO Warehouses (REAL_DATA)")
        click.echo("=" * 80)

        for wh in warehouses:
            click.echo(f"\n  ID: {wh.warehouse_id}")
            click.echo(f"  Name: {wh.name}")
            click.echo(f"  Cluster: {wh.cluster_name or 'N/A'}")
            click.echo(f"  Active: {'✅' if wh.is_active else '❌'}")
            click.echo(f"  Data Source: {wh.data_source.value}")

        click.echo(f"\n✅ Total: {len(warehouses)} warehouses")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
def clusters() -> None:
    """List supply clusters (READ-ONLY, REAL_DATA)."""
    client = create_client()
    supply_client = SupplyAPIClient(client)

    try:
        clusters = supply_client.list_clusters()

        click.echo("\n🌍 Supply Clusters (REAL_DATA)")
        click.echo("=" * 80)

        for cl in clusters:
            click.echo(f"\n  ID: {cl.cluster_id}")
            click.echo(f"  Name: {cl.name}")
            click.echo(f"  Type: {cl.cluster_type}")
            click.echo(f"  Warehouses: {cl.warehouses_count}")
            click.echo(f"  Data Source: {cl.data_source.value}")

        click.echo(f"\n✅ Total: {len(clusters)} clusters")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.option("--status", type=str, help="Filter by status")
@click.option("--limit", default=50, help="Max results")
def orders(status: str | None, limit: int) -> None:
    """List supply orders (READ-ONLY, REAL_DATA)."""
    client = create_client()
    supply_client = SupplyAPIClient(client)

    try:
        orders = supply_client.list_supply_orders(status=status, limit=limit)

        click.echo("\n📋 Supply Orders (REAL_DATA)")
        if status:
            click.echo(f"Filter: status={status}")
        click.echo("=" * 80)

        for order in orders:
            click.echo(f"\n  Supply ID: {order.supply_id}")
            click.echo(f"  Status: {order.status}")
            click.echo(f"  Warehouse ID: {order.warehouse_id or 'N/A'}")
            click.echo(f"  Items: {order.items_count}")
            click.echo(f"  Created: {order.created_at or 'N/A'}")
            click.echo(f"  Data Source: {order.data_source.value}")

        click.echo(f"\n✅ Total: {len(orders)} orders")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.option("--sku", type=int, help="Plan for specific SKU")
@click.option("--max-plans", default=10, help="Maximum plans to generate")
def plan(sku: int | None, max_plans: int) -> None:
    """Generate supply plans (NO MUTATION, DERIVED_DATA)."""
    client = create_client()
    engine = SupplyPlanningEngine(client)

    try:
        click.echo("\n📊 Generating Supply Plans...")
        click.echo("Mode: DRY-RUN (safe)")
        click.echo("=" * 80)

        skus = [sku] if sku else None
        plans = engine.generate_plans(skus=skus, max_plans=max_plans)

        if not plans:
            click.echo("\n⚠️  No plans generated (insufficient data or no demand)")
            return

        for i, plan_data in enumerate(plans, 1):
            click.echo(f"\n{i}. SKU: {plan_data['sku']}")
            click.echo(f"   Product: {plan_data['product_name']}")
            click.echo(f"   Quantity: {plan_data['quantity']}")
            click.echo(f"   Warehouse: {plan_data['target_warehouse_name']}")
            click.echo(f"   Cluster: {plan_data['target_cluster_name']}")
            click.echo(f"   Reason: {plan_data['reason']}")
            click.echo(f"   Prevented Loss: ₽{plan_data['expected_prevented_loss']:.2f}")
            click.echo(f"   Confidence: {plan_data['confidence']:.1%}")
            click.echo(f"   Data Sources: {', '.join(plan_data['data_sources'])}")

        click.echo(f"\n✅ Generated {len(plans)} plans (NO MUTATION)")
        click.echo("Next step: python -m ozon_agent.cli supply propose")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command("fbo")
@click.option("--sku", type=str, help="Plan for specific SKU")
@click.option("--max-rows", default=50, help="Maximum rows to show")
@click.option("--sync-sheets", is_flag=True, help="Write calculation to Google Sheets")
def fbo_plan(sku: str | None, max_rows: int, sync_sheets: bool) -> None:
    """Calculate FBO demand by cluster for 30/60/90 days (NO MUTATION)."""
    client = create_client()
    engine = FboPlanningEngine(client)

    try:
        click.echo("\nFBO Demand Plan")
        click.echo("Mode: DRY-RUN (calculation only, no slot booking)")
        click.echo("=" * 80)

        plans = engine.generate_cluster_demand(
            skus=[sku] if sku else None,
            max_rows=max_rows,
        )

        if not plans:
            click.echo("\nNo FBO demand rows generated")
            if sync_sheets:
                rows = sync_tab("FBO Demand")
                click.echo(f"\nGoogle Sheets updated: FBO Demand ({rows} rows)")
            return

        for i, plan_data in enumerate(plans[:max_rows], 1):
            click.echo(f"\n{i}. SKU: {plan_data.sku} - {plan_data.product_name}")
            click.echo(f"   Cluster: {plan_data.cluster_name}")
            click.echo(f"   Warehouse: {plan_data.warehouse_name}")
            click.echo(
                "   Demand 30/60/90: "
                f"{plan_data.demand_30}/{plan_data.demand_60}/{plan_data.demand_90}"
            )
            click.echo(
                "   Recommended 30/60/90: "
                f"{plan_data.recommended_30}/"
                f"{plan_data.recommended_60}/"
                f"{plan_data.recommended_90}"
            )
            click.echo(f"   Stock: {plan_data.current_stock}")
            click.echo(f"   Confidence: {plan_data.confidence:.0%}")

        if sync_sheets:
            rows = sync_tab("FBO Demand")
            click.echo(f"\nGoogle Sheets updated: FBO Demand ({rows} rows)")

        click.echo(f"\nGenerated {len(plans)} FBO rows (NO MUTATION)")
        click.echo("Slot booking remains gated by approval + create-draft/select-timeslot --execute")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@supply.command("fbo-propose")
@click.option("--sku", type=str, help="Create proposal for specific SKU")
@click.option("--max-proposals", default=5, help="Maximum FBO proposals to create")
def fbo_propose(sku: str | None, max_proposals: int) -> None:
    """Create supply proposals from FBO demand rows."""
    client = create_client()
    engine = FboPlanningEngine(client)
    manager = ProposalManager(client)

    try:
        click.echo("\nFBO -> Supply Proposals")
        click.echo("=" * 80)

        fbo_rows = engine.generate_cluster_demand(
            skus=[sku] if sku else None,
            max_rows=max_proposals * 5,
        )
        plans = [p for p in (_fbo_plan_to_supply_plan(row) for row in fbo_rows) if p][:max_proposals]

        if not plans:
            click.echo("\nNo FBO proposals to create")
            return

        proposals = manager.create_proposals_from_plans(plans)
        if not proposals:
            click.echo("\nNo new FBO proposals created (duplicates or no demand)")
            return

        for proposal in proposals:
            click.echo(f"\nProposal ID: {proposal.proposal_id}")
            click.echo(f"   SKU: {proposal.sku}")
            click.echo(f"   Quantity: {proposal.quantity}")
            click.echo(f"   Warehouse: {proposal.target_warehouse_name}")
            click.echo(f"   Status: {proposal.status.value}")

        click.echo(f"\nCreated {len(proposals)} FBO proposals")
        click.echo("Next step: supply approve <proposal_id> --approved-by <name>")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@supply.command()
@click.option("--max-proposals", default=5, help="Maximum proposals to create")
def propose(max_proposals: int) -> None:
    """Create supply proposals from plans (NO MUTATION yet)."""
    client = create_client()
    engine = SupplyPlanningEngine(client)
    manager = ProposalManager(client)

    try:
        click.echo("\n📝 Creating Supply Proposals...")
        click.echo("=" * 80)

        plans = engine.generate_plans(max_plans=max_proposals)
        proposals = manager.create_proposals_from_plans(plans)

        for proposal in proposals:
            click.echo(f"\n✅ Proposal Created: {proposal.proposal_id}")
            click.echo(f"   SKU: {proposal.sku}")
            click.echo(f"   Quantity: {proposal.quantity}")
            click.echo(f"   Warehouse: {proposal.target_warehouse_name}")
            click.echo(f"   Status: {proposal.status.value}")
            click.echo(f"   Draft Payload Ready: {'✅' if proposal.draft_payload else '❌'}")

        click.echo(f"\n✅ Created {len(proposals)} proposals")
        click.echo("Next step: python -m ozon_agent.cli supply proposals")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.option(
    "--status",
    type=click.Choice(
        ["proposed", "owner_approved", "draft_created", "supply_created", "rejected", "failed"]
    ),
)
@click.option("--limit", default=20, help="Max results")
def proposals(status: str | None, limit: int) -> None:
    """List supply proposals."""
    from ozon_agent.supply.repository import list_proposals

    try:
        status_enum = ProposalStatus(status) if status else None
        proposals_list = list_proposals(status=status_enum, limit=limit)

        click.echo("\n📋 Supply Proposals")
        if status:
            click.echo(f"Filter: status={status}")
        click.echo("=" * 80)

        for p in proposals_list:
            click.echo(f"\n  ID: {p.proposal_id}")
            click.echo(f"  SKU: {p.sku} ({p.product_name})")
            click.echo(f"  Quantity: {p.quantity}")
            click.echo(f"  Warehouse: {p.target_warehouse_name}")
            click.echo(f"  Status: {p.status.value}")
            click.echo(f"  Draft ID: {p.draft_id or 'N/A'}")
            click.echo(f"  Supply ID: {p.supply_id or 'N/A'}")
            click.echo(f"  Created: {p.created_at.strftime('%Y-%m-%d %H:%M')}")

        click.echo(f"\n✅ Total: {len(proposals_list)} proposals")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.argument("proposal_id")
def proposal(proposal_id: str) -> None:
    """Show proposal details."""
    from ozon_agent.supply.repository import get_proposal

    try:
        p = get_proposal(proposal_id)
        if not p:
            click.echo(f"❌ Proposal not found: {proposal_id}")
            raise click.Abort()

        click.echo("\n📋 Proposal Details")
        click.echo("=" * 80)
        click.echo(f"ID: {p.proposal_id}")
        click.echo(f"SKU: {p.sku}")
        click.echo(f"Offer ID: {p.offer_id}")
        click.echo(f"Product: {p.product_name}")
        click.echo(f"Quantity: {p.quantity}")
        click.echo(f"Target Warehouse: {p.target_warehouse_name} (ID: {p.target_warehouse_id})")
        click.echo(f"Target Cluster: {p.target_cluster_name} (ID: {p.target_cluster_id})")
        click.echo(f"Reason: {p.reason}")
        click.echo(f"Expected Prevented Loss: ₽{p.expected_prevented_loss:.2f}")
        click.echo(f"Confidence: {p.confidence:.1%}")
        click.echo(f"Data Sources: {', '.join(p.data_sources)}")
        click.echo(f"Status: {p.status.value}")
        click.echo(f"Draft ID: {p.draft_id or 'N/A'}")
        click.echo(f"Supply ID: {p.supply_id or 'N/A'}")
        click.echo(f"Timeslot ID: {p.timeslot_id or 'N/A'}")
        click.echo(f"Created: {p.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if p.approved_at:
            click.echo(
                f"Approved: {p.approved_at.strftime('%Y-%m-%d %H:%M:%S')} by {p.approved_by}"
            )

        if p.rejected_reason:
            click.echo(f"Rejected: {p.rejected_reason}")

        if p.error_message:
            click.echo(f"Error: {p.error_message}")

        if p.draft_payload:
            click.echo("\nDraft Payload:")
            click.echo(json.dumps(p.draft_payload, indent=2))

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.argument("proposal_id")
@click.option("--approved-by", required=True, help="Approver username")
def approve(proposal_id: str, approved_by: str) -> None:
    """Approve proposal (required before mutation)."""
    manager = ProposalManager(create_client())

    try:
        result = manager.approve_proposal(proposal_id, approved_by)
        click.echo(f"\n✅ {result}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.argument("proposal_id")
@click.option("--execute", is_flag=True, help="Required for actual mutation")
def create_draft(proposal_id: str, execute: bool) -> None:
    """Create draft from approved proposal (MUTATION)."""
    client = create_client()
    manager = ProposalManager(client)

    if not execute:
        click.echo("\n⚠️  DRY-RUN MODE")
        click.echo("To execute real mutation, add --execute flag")
        click.echo(f"Command: python -m ozon_agent.cli supply create-draft {proposal_id} --execute")

        from ozon_agent.supply.repository import get_proposal

        p = get_proposal(proposal_id)
        if not p:
            click.echo(f"❌ Proposal not found: {proposal_id}")
            raise click.Abort()

        click.echo("\nWould create draft:")
        click.echo(f"  Warehouse: {p.target_warehouse_name}")
        click.echo(f"  SKU: {p.sku}")
        click.echo(f"  Quantity: {p.quantity}")
        return

    try:
        result = manager.create_draft(proposal_id)
        click.echo(f"\n✅ {result}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.argument("draft_id")
def timeslots(draft_id: str) -> None:
    """Show available timeslots for draft."""
    client = create_client()
    supply_client = SupplyAPIClient(client)

    try:
        timeslots_list = supply_client.get_timeslots(draft_id)

        click.echo(f"\n🕐 Available Timeslots for Draft {draft_id}")
        click.echo("=" * 80)

        for ts in timeslots_list:
            click.echo(f"\n  Timeslot ID: {ts.timeslot_id}")
            click.echo(f"  Date: {ts.date or 'N/A'}")
            click.echo(f"  Time: {ts.time_from or 'N/A'} - {ts.time_to or 'N/A'}")
            click.echo(f"  Data Source: {ts.data_source.value}")

        click.echo(f"\n✅ Total: {len(timeslots_list)} timeslots")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@supply.command()
@click.argument("proposal_id")
@click.argument("timeslot_id")
@click.option("--execute", is_flag=True, help="Required for actual mutation")
def select_timeslot(proposal_id: str, timeslot_id: str, execute: bool) -> None:
    """Select timeslot and create supply (MUTATION)."""
    client = create_client()
    manager = ProposalManager(client)

    if not execute:
        click.echo("\n⚠️  DRY-RUN MODE")
        click.echo("To execute real mutation, add --execute flag")
        click.echo(
            "Command: python -m ozon_agent.cli supply select-timeslot "
            f"{proposal_id} {timeslot_id} --execute"
        )
        return

    try:
        result = manager.create_supply(proposal_id, timeslot_id)
        click.echo(f"\n✅ {result}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()




