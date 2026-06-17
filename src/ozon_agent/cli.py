"""Ozon AI Agent CLI."""
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from .api.ozon_client import create_client
from .etl.sync import sync_all, sync_finance, sync_orders, sync_products

if TYPE_CHECKING:
    from .decision.models import Recommendation

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from .skills.skill_loader import SkillLoaderError, load_skills

    try:
        load_skills()
    except SkillLoaderError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command()
@click.option("--days", default=7, help="Number of days to sync")
def sync(days: int) -> None:
    """Sync data from Ozon API to database."""
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)

    console.print(f"[bold blue]Syncing data from {date_from.date()} to {date_to.date()}...[/]")
    sync_all(date_from, date_to)
    console.print("[bold green]Sync completed![/]")


@main.command()
def sync_products_cmd() -> None:
    """Sync products only."""
    client = create_client()
    try:
        count = sync_products(client)
        console.print(f"[green]Synced {count} products[/]")
    finally:
        client.close()


@main.command()
@click.argument("date_from", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.argument("date_to", type=click.DateTime(formats=["%Y-%m-%d"]))
def sync_orders_cmd(date_from: datetime, date_to: datetime) -> None:
    """Sync orders for date range."""
    client = create_client()
    try:
        count = sync_orders(client, date_from, date_to)
        console.print(f"[green]Synced {count} orders[/]")
    finally:
        client.close()


@main.command()
@click.argument("date_from", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.argument("date_to", type=click.DateTime(formats=["%Y-%m-%d"]))
def sync_finance_cmd(date_from: datetime, date_to: datetime) -> None:
    """Sync finance for date range."""
    client = create_client()
    try:
        count = sync_finance(client, date_from, date_to)
        console.print(f"[green]Synced {count} finance records[/]")
    finally:
        client.close()


@main.command()
def status() -> None:
    """Show ETL sync status."""
    from .db.connection import execute_query

    rows = execute_query(
        """SELECT source, status, rows_fetched, rows_inserted, started_at, completed_at
           FROM etl_log ORDER BY started_at DESC LIMIT 20"""
    )

    table = Table(title="ETL Status")
    table.add_column("Source")
    table.add_column("Status")
    table.add_column("Fetched")
    table.add_column("Inserted")
    table.add_column("Started")
    table.add_column("Completed")

    for row in rows:
        if row["status"] == "success":
            status_color = "green"
        elif row["status"] == "failed":
            status_color = "red"
        else:
            status_color = "yellow"
        table.add_row(
            row["source"],
            f"[{status_color}]{row['status']}[/]",
            str(row["rows_fetched"] or 0),
            str(row["rows_inserted"] or 0),
            str(row["started_at"] or ""),
            str(row["completed_at"] or ""),
        )

    console.print(table)


@main.command()
@click.option("--output", "-o", default=None, help="Output file path")
def analyze(output: str | None) -> None:
    """Run analytics on synced data."""
    import json

    import pandas as pd

    from .analytics.summary import format_summary_text, generate_analytics_summary
    from .db.connection import execute_query

    console.print("[bold blue]Loading data...[/]")

    products = pd.DataFrame(execute_query("SELECT * FROM products"))
    sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
    advertising = pd.DataFrame(execute_query("SELECT * FROM advertising"))
    finance = pd.DataFrame(execute_query("SELECT * FROM finance"))

    console.print(f"  Products: {len(products)}")
    console.print(f"  Sales: {len(sales)}")
    console.print(f"  Advertising: {len(advertising)}")
    console.print(f"  Finance: {len(finance)}")

    summary = generate_analytics_summary(products, sales, advertising, finance)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Report saved to {output}[/]")
    else:
        console.print(format_summary_text(summary))


@main.command()
def diagnostics() -> None:
    """Run data quality diagnostics."""
    import pandas as pd

    from .analytics.diagnostics import run_full_diagnostics
    from .db.connection import execute_query

    console.print("[bold blue]Running diagnostics...[/]")

    sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
    result = run_full_diagnostics(sales)

    table = Table(title="Data Quality Diagnostics")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")

    for check in result.get("checks", []):
        status = check["status"]
        color = "green" if status == "pass" else "yellow" if status == "warn" else "red"
        table.add_row(
            check["check"],
            f"[{color}]{status}[/]",
            check["message"],
        )

    console.print(table)
    console.print(
        f"\n[bold]Summary: {result['passed']} passed, "
        f"{result['warnings']} warnings, {result['failed']} failed[/]"
    )


@main.command()
@click.option("--target", "-t", default="quantity", help="Target column to forecast")
@click.option("--periods", "-p", default=7, help="Number of days to forecast")
@click.option(
    "--model", "-m", default="prophet",
    type=click.Choice(["prophet", "xgboost", "lightgbm"]),
)
def forecast(target: str, periods: int, model: str) -> None:
    """Forecast sales and metrics."""
    import pandas as pd

    from .db.connection import execute_query
    from .forecast.base import BaseForecaster
    from .forecast.lgbm_forecaster import LGBMForecaster
    from .forecast.prophet_forecaster import ProphetForecaster
    from .forecast.xgb_forecaster import XGBForecaster

    console.print(f"[bold blue]Loading data for {target}...[/]")
    sales = pd.DataFrame(execute_query(
        "SELECT date, SUM(quantity) as quantity, "
        "SUM(revenue) as revenue FROM sales GROUP BY date ORDER BY date"
    ))

    if sales.empty:
        console.print("[red]No sales data found. Run sync first.[/]")
        return

    console.print(f"  Loaded {len(sales)} days of data")

    fitter: BaseForecaster
    if model == "prophet":
        fitter = ProphetForecaster()
        fitter.fit(sales, target=target)
    elif model == "xgboost":
        fitter = XGBForecaster()
        features = [c for c in ["revenue", "spend"] if c in sales.columns]
        fitter.fit(sales, target=target, features=features)
    else:
        fitter = LGBMForecaster()
        features = [c for c in ["revenue", "spend"] if c in sales.columns]
        fitter.fit(sales, target=target, features=features)

    result = fitter.predict(periods=periods)

    console.print(f"\n[bold green]Forecast ({model}, {periods} days):[/]")
    for date, val in zip(result.dates, result.point):
        console.print(f"  {date}: {val:.1f}")


@main.command()
@click.option(
    "--builder", "-b",
    default="manual",
    type=click.Choice(["mimo", "codex", "cursor", "claude", "manual"]),
    help="Builder type that produced the changes",
)
@click.option("--task-goal", "-g", required=True, help="Goal of the task being audited")
@click.option("--output", "-o", default=None, help="Output file path (JSON)")
def supervise(builder: str, task_goal: str, output: str | None) -> None:
    """Run supervisor audit on current project state."""
    import json

    from .supervisor.collectors import (
        detect_architecture_risks,
        get_changed_files,
        get_git_status,
        get_roadmap_alignment,
        get_test_results,
        recommend_next_task,
    )
    from .supervisor.report import AuditReport, format_report_text

    console.print(f"[bold blue]Running supervisor audit (builder={builder})...[/]")

    git_status = get_git_status()
    changed_files = get_changed_files()
    test_results = get_test_results()
    roadmap = get_roadmap_alignment()
    risks = detect_architecture_risks()
    next_task = recommend_next_task(roadmap["completed"])

    report = AuditReport(
        builder_type=builder,
        task_goal=task_goal,
        timestamp=datetime.now().isoformat(),
        git_status=git_status,
        changed_files=changed_files,
        test_results=test_results,
        roadmap_alignment=roadmap,
        architecture_risks=risks,
        recommended_next_task=next_task,
        summary=f"Builder {builder} completed task: {task_goal}",
    )

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        console.print(f"[green]Report saved to {output}[/]")
    else:
        console.print(format_report_text(report))


@main.command()
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
@click.option("--branch", "-b", default="main", help="Git branch to deploy")
@click.option("--execute", is_flag=True, default=False, help="Execute deployment")
@click.option("--output", "-o", default=None, help="Output file path (JSON)")
def deploy(target: str, branch: str, execute: bool, output: str | None) -> None:
    """Deploy to VPS after supervisor checks."""
    import json

    from .deploy.deploy_plan import (
        build_deploy_plan,
        evaluate_deploy_readiness,
        format_plan_text,
    )
    from .deploy.health_check import run_full_health_check
    from .deploy.vps_deployer import execute_deploy

    console.print("[bold blue]Checking deployment readiness...[/]")

    from .supervisor.collectors import get_test_results

    test_results = get_test_results()

    decision = evaluate_deploy_readiness(supervisor_status="pass", test_results=test_results)

    if not decision.deploy_allowed:
        console.print(f"[red]Cannot deploy: {decision.reason}[/]")
        return

    if decision.risk_level == "medium":
        console.print(f"[bold yellow]WARNING: {decision.reason}[/]")

    plan = build_deploy_plan(decision, target=target, branch=branch, dry_run=not execute)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
        console.print(f"[green]Plan saved to {output}[/]")
        return

    console.print(format_plan_text(plan, decision))

    if not execute:
        console.print("\n[bold yellow]DRY RUN — no commands executed.[/]")
        console.print("Use [bold]--execute[/] to deploy for real.")
        return

    console.print("\n[bold green]EXECUTING DEPLOYMENT...[/]")
    deploy_result = execute_deploy(target, branch)

    if deploy_result["success"]:
        console.print("[bold green]Deployment successful![/]")
        console.print("\nRunning health check...")
        health = run_full_health_check(target)
        if health["healthy"]:
            console.print("[bold green]Health check passed![/]")
        else:
            console.print("[bold red]Health check FAILED![/]")
            for name, check in health["checks"].items():
                if not check["healthy"]:
                    console.print(f"  {name}: {check.get('error', 'failed')}")
            console.print("\n[bold yellow]Rollback command:[/]")
            console.print(f"  ozon-agent rollback --target {target}")
    else:
        console.print("[bold red]Deployment FAILED![/]")
        for step in deploy_result["steps"]:
            if not step["success"]:
                console.print(f"  Failed: {step['step']} — {step['stderr']}")
        console.print("\n[bold yellow]Rollback command:[/]")
        console.print(f"  ozon-agent rollback --target {target}")


@main.command()
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
def rollback(target: str) -> None:
    """Rollback to previous commit on VPS."""
    from .deploy.rollback import execute_rollback, format_rollback_text

    console.print(f"[bold yellow]Rolling back on {target}...[/]")
    console.print(format_rollback_text(target))

    result = execute_rollback(target)
    if result["success"]:
        console.print("[bold green]Rollback successful![/]")
    else:
        console.print("[bold red]Rollback failed![/]")
        for step in result["steps"]:
            if not step["success"]:
                console.print(f"  Failed: {step['step']} — {step['stderr']}")


@main.group("recommendations", invoke_without_command=True)
@click.option("--sku", default=None, help="Filter by SKU")
@click.option("--top", default=20, help="Max recommendations to show")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--save-pending", is_flag=True, default=False, help="Save as PENDING approvals")
@click.option("--force", is_flag=True, default=False, help="Force save even if duplicate exists")
@click.option("--calibrated", is_flag=True, default=False, help="Apply historical calibration")
@click.pass_context
def recommendations(
    ctx: click.Context, sku: str | None, top: int, as_json: bool, output: str | None,
    save_pending: bool, force: bool, calibrated: bool,
) -> None:
    """Generate recommendations from current data."""
    if ctx.invoked_subcommand is not None:
        return
    import json

    import pandas as pd

    from .db.connection import execute_query

    console.print("[bold blue]Loading data...[/]")

    products = pd.DataFrame(execute_query("SELECT * FROM products"))
    sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
    advertising = pd.DataFrame(execute_query("SELECT * FROM advertising"))

    forecasts = pd.DataFrame(columns=["sku"])
    stock = pd.DataFrame(columns=["sku"])

    try:
        rows = execute_query("SELECT * FROM forecasts")
        if rows:
            forecasts = pd.DataFrame(rows)
    except Exception:
        pass

    try:
        rows = execute_query("SELECT * FROM stock")
        if rows:
            stock = pd.DataFrame(rows)
    except Exception:
        pass

    from .decision.feature_store import build_decision_features
    from .decision.recommendation_engine import generate_recommendations
    from .decision.recommendation_summary import recommendation_to_dict

    features = build_decision_features(products, sales, advertising, forecasts, stock)

    if sku:
        features = [f for f in features if f.sku == sku]

    if not features:
        console.print("[yellow]No features found for recommendations.[/]")
        return

    recs = generate_recommendations(features, limit=top)

    if not recs:
        console.print("[yellow]No recommendations generated.[/]")
        return

    calibration_factor = None
    if calibrated:
        from .approval.models import RecommendationStatus
        from .approval.repository import list_recommendations as list_stored
        from .learning.confidence_calibration import get_calibration_factor
        from .learning.outcome_learning import build_learning_samples

        stored = list_stored(status=RecommendationStatus.OBSERVED, limit=100)
        outcomes = []
        for s in stored:
            from .approval.repository import list_outcomes
            outcomes.extend(list_outcomes(s.id))
        if stored and outcomes:
            samples = build_learning_samples(stored, outcomes)
            calibration_factor = get_calibration_factor(samples)
            console.print(
                f"[bold blue]Calibration factor: {calibration_factor:.2f}[/]"
            )
        else:
            console.print("[yellow]No observed outcomes for calibration.[/]")

    if save_pending:
        from .approval.models import RecommendationStatus
        from .approval.repository import list_recommendations
        from .approval.workflow import create_pending_recommendation

        saved_ids = []
        for rec in recs:
            if not force:
                existing = list_recommendations(
                    status=RecommendationStatus.PENDING, sku=rec.sku, limit=1
                )
                if existing and existing[0].action.value == rec.action.value:
                    continue
            stored_rec = create_pending_recommendation(rec)
            saved_ids.append(stored_rec.id)

        if saved_ids:
            console.print(f"[green]Saved {len(saved_ids)} pending recommendation(s):[/]")
            for rid in saved_ids:
                console.print(f"  {rid}")
        else:
            console.print("[yellow]No new recommendations to save (duplicates found).[/]")
        return

    if as_json or output:
        data = [recommendation_to_dict(r) for r in recs]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)
            console.print(f"[green]Saved {len(recs)} recommendations to {output}[/]")
        else:
            console.print(text)
    else:
        table = Table(title=f"Recommendations ({len(recs)} total)")
        table.add_column("SKU", max_width=20)
        table.add_column("Action")
        table.add_column("Confidence")
        table.add_column("Risk")
        table.add_column("Expected Effect", max_width=40)

        for rec in recs:
            conf_color = (
                "green" if rec.confidence.level.value == "HIGH"
                else "yellow" if rec.confidence.level.value == "MEDIUM"
                else "red"
            )
            risk_color = (
                "green" if rec.risk.level.value == "LOW"
                else "yellow" if rec.risk.level.value == "MEDIUM"
                else "red"
            )
            table.add_row(
                rec.sku,
                rec.action.value,
                f"[{conf_color}]{rec.confidence.level.value} ({rec.confidence.score:.2f})[/]",
                f"[{risk_color}]{rec.risk.level.value} ({rec.risk.score:.2f})[/]",
                rec.expected_effect,
            )

        console.print(table)


@recommendations.command("market-context")
@click.option("--sku", default=None, help="Filter market context by SKU")
def recommendations_market_context_cmd(sku: str | None) -> None:
    """Show market context used by recommendation enrichment."""
    from .decision.market_context import build_market_context

    context = build_market_context(sku)
    table = Table(title="Recommendation Market Context")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("SKU", sku or "all/category")
    table.add_row("Price pressure", context.price_pressure)
    table.add_row("Competitor growth", context.competitor_growth)
    table.add_row("Review pressure", context.review_pressure)
    table.add_row("Rating pressure", context.rating_pressure)
    table.add_row("Market risk score", f"{context.market_risk_score:.0f}")
    table.add_row("Market opportunity score", f"{context.market_opportunity_score:.0f}")
    table.add_row("Market signals", str(len(context.market_signals)))
    table.add_row("Market risks", str(len(context.market_risks)))
    table.add_row("Market opportunities", str(len(context.market_opportunities)))
    console.print(table)


@recommendations.command("explain")
@click.option("--sku", default=None, help="Filter recommendations by SKU")
@click.option("--top", default=5, help="Max recommendations to explain")
def recommendations_explain_cmd(sku: str | None, top: int) -> None:
    """Explain recommendation reasons including market context."""
    from .decision.recommendation_summary import format_recommendation_text

    recs = _generate_current_recommendations(sku=sku, top=top)
    if not recs:
        console.print("[yellow]No recommendations generated.[/]")
        return

    for index, rec in enumerate(recs, start=1):
        console.print(f"[bold]Recommendation {index}[/]")
        console.print(format_recommendation_text(rec))
        console.print("")


@recommendations.group("memory")
def recommendations_memory() -> None:
    """Inspect autonomous recommendation memory."""


@recommendations_memory.command("stats")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def recommendations_memory_stats(as_json: bool) -> None:
    """Show recommendation memory statistics."""
    import json as json_mod

    from .memory.report_builder import build_memory_report, memory_stats_to_dict
    from .memory.statistics import build_memory_statistics

    stats = build_memory_statistics()
    if as_json:
        console.print(json_mod.dumps(memory_stats_to_dict(stats), ensure_ascii=False, indent=2))
    else:
        console.print(build_memory_report(stats))


@recommendations_memory.command("search")
@click.argument("query")
def recommendations_memory_search(query: str) -> None:
    """Search stored recommendation memory records."""
    from .memory.repository import search_memory_records

    rows = search_memory_records(query)
    table = Table(title=f"Recommendation Memory Search: {query}")
    table.add_column("ID")
    table.add_column("SKU")
    table.add_column("Action")
    table.add_column("Result")
    table.add_column("Success")
    for row in rows[:50]:
        table.add_row(
            row.id,
            row.sku,
            row.action.value,
            row.result.value,
            f"{row.success_score:.2f}",
        )
    console.print(table)


@recommendations_memory.command("insights")
def recommendations_memory_insights() -> None:
    """Show recommendation memory insights."""
    from .memory.report_builder import build_memory_insights_report

    console.print(build_memory_insights_report())


@recommendations_memory.command("refresh")
def recommendations_memory_refresh() -> None:
    """Refresh recommendation memory insights from stored records."""
    from .memory.engine import refresh_memory_insights

    insights = refresh_memory_insights()
    console.print(f"[green]Refreshed {len(insights)} memory insights.[/]")


def _generate_current_recommendations(sku: str | None, top: int) -> list["Recommendation"]:
    import pandas as pd

    from .db.connection import execute_query
    from .decision.feature_store import build_decision_features
    from .decision.recommendation_engine import generate_recommendations

    products = pd.DataFrame(execute_query("SELECT * FROM products"))
    sales = pd.DataFrame(execute_query("SELECT * FROM sales"))
    advertising = pd.DataFrame(execute_query("SELECT * FROM advertising"))
    forecasts = pd.DataFrame(columns=["sku"])
    stock = pd.DataFrame(columns=["sku"])
    try:
        rows = execute_query("SELECT * FROM forecasts")
        if rows:
            forecasts = pd.DataFrame(rows)
    except Exception:
        pass
    try:
        rows = execute_query("SELECT * FROM stock")
        if rows:
            stock = pd.DataFrame(rows)
    except Exception:
        pass
    features = build_decision_features(products, sales, advertising, forecasts, stock)
    if sku:
        features = [feature for feature in features if feature.sku == sku]
    return generate_recommendations(features, limit=top)


@main.group()
def approvals() -> None:
    """Manage recommendation approvals."""


@approvals.command("list")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--limit", default=20, help="Max results")
def approvals_list(status: str | None, limit: int) -> None:
    """List recommendations."""
    from .approval.approval_summary import format_recommendation_list
    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations

    status_enum = RecommendationStatus(status) if status else None
    recs = list_recommendations(status=status_enum, limit=limit)
    console.print(format_recommendation_list(recs))


@approvals.command("show")
@click.argument("rec_id")
def approvals_show(rec_id: str) -> None:
    """Show recommendation details."""
    from .approval.approval_summary import format_recommendation_detail
    from .approval.repository import get_recommendation

    rec = get_recommendation(rec_id)
    if rec is None:
        console.print(f"[red]Recommendation {rec_id} not found.[/]")
        return
    console.print(format_recommendation_detail(rec))


@approvals.command("approve")
@click.argument("rec_id")
@click.option("--by", required=True, help="Approver name")
def approvals_approve(rec_id: str, by: str) -> None:
    """Approve a recommendation."""
    from .approval.workflow import approve_recommendation

    try:
        rec = approve_recommendation(rec_id, approved_by=by)
        console.print(f"[green]Approved {rec.id} by {by}[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@approvals.command("reject")
@click.argument("rec_id")
@click.option("--by", required=True, help="Rejector name")
@click.option("--reason", required=True, help="Rejection reason")
def approvals_reject(rec_id: str, by: str, reason: str) -> None:
    """Reject a recommendation."""
    from .approval.workflow import reject_recommendation

    try:
        rec = reject_recommendation(rec_id, rejected_by=by, reason=reason)
        console.print(f"[yellow]Rejected {rec.id} by {by}: {reason}[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@approvals.command("mark-executed")
@click.argument("rec_id")
def approvals_mark_executed(rec_id: str) -> None:
    """Mark recommendation as executed."""
    from .approval.workflow import mark_executed

    try:
        rec = mark_executed(rec_id)
        console.print(f"[green]Marked {rec.id} as EXECUTED[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@approvals.command("mark-observed")
@click.argument("rec_id")
def approvals_mark_observed(rec_id: str) -> None:
    """Mark recommendation as observed."""
    from .approval.workflow import mark_observed

    try:
        rec = mark_observed(rec_id)
        console.print(f"[green]Marked {rec.id} as OBSERVED[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@approvals.command("close")
@click.argument("rec_id")
def approvals_close(rec_id: str) -> None:
    """Close a recommendation."""
    from .approval.workflow import close_recommendation

    try:
        rec = close_recommendation(rec_id)
        console.print(f"[green]Closed {rec.id}[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@approvals.command("outcomes")
@click.argument("rec_id")
def approvals_outcomes(rec_id: str) -> None:
    """Show outcomes for a recommendation."""
    from .approval.approval_summary import format_outcome_detail
    from .approval.repository import list_outcomes

    outcomes = list_outcomes(rec_id)
    if not outcomes:
        console.print(f"[yellow]No outcomes for {rec_id}[/]")
        return
    for outcome in outcomes:
        console.print(format_outcome_detail(outcome))
        console.print()


@main.command()
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="Show pending migrations without applying",
)
def migrate(dry_run: bool) -> None:
    """Apply pending database migrations."""
    from .db.migrator import migrate as run_migrate
    from .db.migrator import migration_status

    status = migration_status()
    console.print(
        f"[bold blue]Migrations: {status['applied']} applied, "
        f"{status['pending']} pending[/]"
    )

    if status["pending"] == 0:
        console.print("[green]All migrations applied.[/]")
        return

    console.print("[bold blue]Pending:[/]")
    for f in status["pending_files"]:
        console.print(f"  - {f}")

    if dry_run:
        console.print("\n[bold yellow]DRY RUN — no migrations applied.[/]")
        return

    results = run_migrate()
    for r in results:
        if r.applied:
            console.print(f"[green]Applied: {r.filename}[/]")
        else:
            console.print(f"[red]Failed: {r.filename} — {r.error}[/]")
            return

    console.print("[bold green]All pending migrations applied.[/]")


@main.command("migrate-status")
def migrate_status_cmd() -> None:
    """Show migration status."""
    from .db.migrator import migration_status

    status = migration_status()
    table = Table(title="Migration Status")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Total", str(status["total"]))
    table.add_row("Applied", str(status["applied"]))
    table.add_row("Pending", str(status["pending"]))
    if status["applied_versions"]:
        table.add_row("Applied versions", ", ".join(status["applied_versions"]))
    if status["pending_files"]:
        table.add_row("Pending files", ", ".join(status["pending_files"]))
    console.print(table)


@main.group()
def learning() -> None:
    """Outcome learning and confidence calibration."""


@learning.command("summary")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
@click.option("--output", "-o", default=None, help="Output file path")
def learning_summary(as_json: bool, output: str | None) -> None:
    """Show learning summary from observed outcomes."""
    import json as json_mod

    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations as list_stored
    from .learning.learning_summary import format_learning_report, learning_report_to_dict
    from .learning.outcome_learning import (
        build_learning_samples,
        calculate_action_accuracy,
        calculate_recommendation_accuracy,
        calculate_sku_accuracy,
    )

    stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    if not stored:
        console.print("[yellow]No observed recommendations found.[/]")
        return

    outcomes = []
    for s in stored:
        from .approval.repository import list_outcomes
        outcomes.extend(list_outcomes(s.id))

    samples = build_learning_samples(stored, outcomes)
    accuracy = calculate_recommendation_accuracy(samples)
    by_action = calculate_action_accuracy(samples)
    by_sku = calculate_sku_accuracy(samples)

    if as_json or output:
        data = learning_report_to_dict(
            accuracy, by_action=by_action, by_sku=by_sku
        )
        text = json_mod.dumps(data, ensure_ascii=False, indent=2)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)
            console.print(f"[green]Saved to {output}[/]")
        else:
            console.print(text)
    else:
        console.print(format_learning_report(
            accuracy, by_action=by_action, by_sku=by_sku
        ))


@learning.command("calibrate")
def learning_calibrate() -> None:
    """Show confidence calibration from historical outcomes."""
    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations as list_stored
    from .learning.confidence_calibration import calibrate_confidence
    from .learning.learning_summary import format_calibration
    from .learning.outcome_learning import build_learning_samples

    stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    if not stored:
        console.print("[yellow]No observed recommendations found.[/]")
        return

    outcomes = []
    for s in stored:
        from .approval.repository import list_outcomes
        outcomes.extend(list_outcomes(s.id))

    samples = build_learning_samples(stored, outcomes)
    calibration = calibrate_confidence(samples)
    console.print(format_calibration(calibration))


@learning.command("backtest")
def learning_backtest() -> None:
    """Run backtest on observed outcomes."""
    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations as list_stored
    from .learning.backtesting import backtest_recommendations
    from .learning.learning_summary import format_backtest

    stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    if not stored:
        console.print("[yellow]No observed recommendations found.[/]")
        return

    outcomes = []
    for s in stored:
        from .approval.repository import list_outcomes
        outcomes.extend(list_outcomes(s.id))

    bt = backtest_recommendations([], stored, outcomes)
    console.print(format_backtest(bt))


@learning.command("by-action")
def learning_by_action() -> None:
    """Show accuracy grouped by action type."""
    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations as list_stored
    from .learning.learning_summary import format_accuracy
    from .learning.outcome_learning import build_learning_samples, calculate_action_accuracy

    stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    if not stored:
        console.print("[yellow]No observed recommendations found.[/]")
        return

    outcomes = []
    for s in stored:
        from .approval.repository import list_outcomes
        outcomes.extend(list_outcomes(s.id))

    samples = build_learning_samples(stored, outcomes)
    by_action = calculate_action_accuracy(samples)

    if not by_action:
        console.print("[yellow]No action data available.[/]")
        return

    for action, acc in by_action.items():
        console.print(f"\n[bold]{action}[/]:")
        console.print(format_accuracy(acc))


@learning.command("by-sku")
def learning_by_sku() -> None:
    """Show accuracy grouped by SKU."""
    from .approval.models import RecommendationStatus
    from .approval.repository import list_recommendations as list_stored
    from .learning.learning_summary import format_accuracy
    from .learning.outcome_learning import build_learning_samples, calculate_sku_accuracy

    stored = list_stored(status=RecommendationStatus.OBSERVED, limit=200)
    if not stored:
        console.print("[yellow]No observed recommendations found.[/]")
        return

    outcomes = []
    for s in stored:
        from .approval.repository import list_outcomes
        outcomes.extend(list_outcomes(s.id))

    samples = build_learning_samples(stored, outcomes)
    by_sku = calculate_sku_accuracy(samples)

    if not by_sku:
        console.print("[yellow]No SKU data available.[/]")
        return

    for sku, acc in by_sku.items():
        console.print(f"\n[bold]{sku}[/]:")
        console.print(format_accuracy(acc))


@main.group()
def skills() -> None:
    """Manage local skills registry."""


@skills.command("list")
def skills_list_cmd() -> None:
    """List loaded skills."""
    from .skills.skill_loader import list_skills

    loaded_skills = list_skills()
    table = Table(title=f"Skills ({len(loaded_skills)} loaded)")
    table.add_column("Name")
    table.add_column("Path")
    for skill in loaded_skills:
        table.add_row(skill.name, str(skill.path))
    console.print(table)


@skills.command("show")
@click.argument("name")
def skills_show_cmd(name: str) -> None:
    """Show skill files and summary."""
    from .skills.skill_loader import SkillNotFoundError, get_skill

    try:
        skill = get_skill(name)
    except SkillNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title=f"Skill: {skill.name}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Path", str(skill.path))
    table.add_row("SKILL.md", str(skill.skill_md_path))
    table.add_row("rules.md", str(skill.rules_md_path))
    table.add_row("examples.md", str(skill.examples_md_path))
    console.print(table)
    console.print("[bold]Preview[/]")
    console.print(skill.skill_md.strip()[:600] or "(empty)")


@skills.command("reload")
def skills_reload_cmd() -> None:
    """Reload skills from skills/index.yaml."""
    from .skills.skill_loader import reload_skills

    loaded_skills = reload_skills()
    console.print(f"[green]Reloaded {len(loaded_skills)} skills[/]")


@main.group()
def api() -> None:
    """Inspect Ozon API Swagger endpoints."""


@api.command("endpoints")
def api_endpoints_cmd() -> None:
    """List endpoint categories."""
    from .skills.ozon_api.swagger_models import EndpointCategory
    from .skills.ozon_api.swagger_registry import count_endpoints_by_category

    stats = count_endpoints_by_category()
    table = Table(title="Ozon API Endpoint Categories")
    table.add_column("Category")
    table.add_column("Count")
    for category in EndpointCategory:
        if category.value == "Other":
            continue
        table.add_row(category.value, str(stats.get(category, 0)))
    console.print(table)


@api.command("search")
@click.argument("query")
def api_search_cmd(query: str) -> None:
    """Search endpoints by query."""
    from .skills.ozon_api.swagger_registry import search_endpoints

    matches = search_endpoints(query)
    if not matches:
        console.print(f"[yellow]No endpoints found for '{query}'[/]")
        return

    table = Table(title=f"Ozon API Search: {query}")
    table.add_column("Method")
    table.add_column("Path")
    table.add_column("Name")
    table.add_column("Category")
    for endpoint in matches[:25]:
        table.add_row(endpoint.method, endpoint.path, endpoint.name, endpoint.category.value)
    console.print(table)


@api.command("show")
@click.argument("name")
def api_show_cmd(name: str) -> None:
    """Show endpoint details."""
    from .skills.ozon_api.swagger_models import EndpointNotFoundError
    from .skills.ozon_api.swagger_registry import get_endpoint

    try:
        endpoint = get_endpoint(name)
    except EndpointNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title=f"Ozon API Endpoint: {endpoint.name}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Method", endpoint.method)
    table.add_row("Path", escape(endpoint.path))
    table.add_row("Category", endpoint.category.value)
    table.add_row("Summary", endpoint.summary or "-")
    table.add_row("Description", endpoint.description or "-")
    table.add_row("Tags", escape(", ".join(endpoint.tags)) or "-")
    table.add_row(
        "Request schema keys",
        escape(", ".join(sorted(endpoint.request_schema.keys()))) or "-",
    )
    table.add_row(
        "Response schema keys",
        escape(", ".join(sorted(endpoint.response_schema.keys()))) or "-",
    )
    console.print(table)


@api.command("stats")
def api_stats_cmd() -> None:
    """Show Swagger stats."""
    from .skills.ozon_api.swagger_loader import get_swagger_version, load_swagger
    from .skills.ozon_api.swagger_models import EndpointCategory
    from .skills.ozon_api.swagger_registry import count_endpoints, count_endpoints_by_category

    document = load_swagger()
    category_counts = count_endpoints_by_category()
    table = Table(title="Ozon API Swagger Stats")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Title", document.title or "-")
    table.add_row("Swagger version", get_swagger_version())
    table.add_row("Total endpoints", str(count_endpoints()))
    for category in EndpointCategory:
        if category.value == "Other":
            continue
        table.add_row(category.value, str(category_counts.get(category, 0)))
    console.print(table)


@api.command("client")
def api_client_cmd() -> None:
    """Show read-only client generation blueprint."""
    from .integrations.ozon_api.client_generator import generate_client_blueprint

    blueprint = generate_client_blueprint()
    table = Table(title="Ozon API Client Blueprint")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Client name", str(blueprint["client_name"]))
    table.add_row("Source", str(blueprint["source"]))
    table.add_row("Swagger title", str(blueprint["swagger_title"]))
    table.add_row("Swagger version", str(blueprint["swagger_version"]))
    table.add_row("Request execution", str(blueprint["request_execution"]))
    table.add_row("Endpoint count", str(blueprint["endpoint_count"]))
    table.add_row("Module count", str(blueprint["module_count"]))
    console.print(table)

    modules_table = Table(title="Generated Client Modules")
    modules_table.add_column("Module")
    modules_table.add_column("Endpoints")
    modules_table.add_column("Sample methods")
    for module in blueprint["modules"]:
        methods = [str(item["name"]) for item in module["methods"][:3]]
        sample = ", ".join(methods) if methods else "-"
        modules_table.add_row(str(module["name"]), str(module["endpoint_count"]), sample)
    console.print(modules_table)


@api.command("stubs")
@click.option("--category", default=None, help="Filter by category, for example stocks")
def api_stubs_cmd(category: str | None) -> None:
    """Show generated typed read-only client stubs."""
    from .integrations.ozon_api.client_stubs import generate_typed_client_stubs

    client_stubs = generate_typed_client_stubs()
    methods = client_stubs.list_methods(category=category)
    title = "Ozon API Typed Client Stubs"
    if category:
        title = f"{title}: {category}"
    table = Table(title=title)
    table.add_column("Name")
    table.add_column("Method")
    table.add_column("Path")
    table.add_column("Category")
    for method in methods[:30]:
        table.add_row(method.name, method.method, escape(method.path), method.category)
    console.print(table)
    console.print("[yellow]Execution disabled: stubs only prepare request descriptors.[/]")


@api.command("clients")
def api_clients_cmd() -> None:
    """List typed Ozon API clients."""
    from .integrations.ozon_api.client_registry import list_clients

    table = Table(title="Ozon API Typed Clients")
    table.add_column("Client")
    for client_name in list_clients():
        table.add_row(client_name)
    console.print(table)


@api.command("methods")
@click.argument("client")
def api_methods_cmd(client: str) -> None:
    """List methods for a typed Ozon API client."""
    from .integrations.ozon_api.client_registry import list_methods

    try:
        method_names = list_methods(client)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title=f"Ozon API Methods: {client}")
    table.add_column("Method")
    for method_name in method_names:
        table.add_row(method_name)
    console.print(table)


@api.command("describe")
@click.argument("client")
@click.argument("method")
def api_describe_cmd(client: str, method: str) -> None:
    """Describe one typed Ozon API client method."""
    from .integrations.ozon_api.client_registry import get_method
    from .skills.ozon_api.swagger_models import EndpointNotFoundError

    try:
        descriptor = get_method(client, method)
    except (EndpointNotFoundError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc

    description = descriptor.describe()
    table = Table(title=f"Ozon API Describe: {client}.{method}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Name", str(description["name"]))
    table.add_row("Method name", str(description["method_name"]))
    table.add_row("HTTP method", str(description["method"]))
    table.add_row("Path", escape(str(description["path"])))
    table.add_row("Summary", str(description["summary"]) or "-")
    table.add_row("Description", str(description["description"]) or "-")
    table.add_row("Tags", escape(", ".join(description["tags"])) or "-")
    table.add_row("Category", str(description["category"]))
    table.add_row(
        "Request schema keys",
        escape(", ".join(sorted(description["request_schema"].keys()))) or "-",
    )
    table.add_row(
        "Response schema keys",
        escape(", ".join(sorted(description["response_schema"].keys()))) or "-",
    )
    console.print(table)


@main.group()
def mcp() -> None:
    """Inspect Ozon MCP discovery layer."""


@mcp.command("tools")
def mcp_tools_cmd() -> None:
    """List discovered MCP tools."""
    from .mcp.server import MCPServer

    server = MCPServer()
    table = Table(title="Ozon MCP Tools")
    table.add_column("Tool")
    table.add_column("Category")
    table.add_column("Description")
    for tool in server.list_tools()[:50]:
        table.add_row(tool.name, tool.category, tool.description or "-")
    console.print(table)
    console.print("[yellow]Execution disabled: discovery only.[/]")


@mcp.command("show")
@click.argument("name")
def mcp_show_cmd(name: str) -> None:
    """Show MCP tool metadata."""
    from .mcp.server import MCPServer

    server = MCPServer()
    try:
        description = server.describe_tool(name)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc

    metadata = description["endpoint_metadata"]
    request_schema = description["request_schema"]
    response_schema = description["response_schema"]
    table = Table(title=f"Ozon MCP Tool: {name}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Name", str(description["name"]))
    table.add_row("Category", str(description["category"]))
    table.add_row("Description", str(description["description"]) or "-")
    if isinstance(metadata, dict):
        table.add_row("Path", escape(str(metadata.get("path", "-"))))
        table.add_row("HTTP method", str(metadata.get("method", "-")))
        table.add_row("Method name", str(metadata.get("method_name", "-")))
    request_schema_keys = "-"
    if isinstance(request_schema, dict):
        request_schema_keys = escape(", ".join(sorted(request_schema.keys()))) or "-"
    response_schema_keys = "-"
    if isinstance(response_schema, dict):
        response_schema_keys = escape(", ".join(sorted(response_schema.keys()))) or "-"
    table.add_row(
        "Request schema keys",
        request_schema_keys,
    )
    table.add_row(
        "Response schema keys",
        response_schema_keys,
    )
    console.print(table)


@mcp.command("stats")
def mcp_stats_cmd() -> None:
    """Show MCP tool statistics."""
    from .mcp.server import MCPServer

    stats = MCPServer().stats()
    table = Table(title="Ozon MCP Stats")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Tools", str(stats["tools"]))
    categories = stats["categories"]
    if isinstance(categories, dict):
        for category, count in categories.items():
            table.add_row(str(category), str(count))
    console.print(table)


@main.group()
def research() -> None:
    """Inspect marketplace research foundation."""


@research.command("sources")
def research_sources_cmd() -> None:
    """List marketplace research sources."""
    from .research.source_registry import list_sources

    table = Table(title="Marketplace Research Sources")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Network")
    table.add_column("Description")
    for source in list_sources():
        table.add_row(
            source.name,
            source.source_type.value,
            source.status.value,
            "yes" if source.requires_network else "no",
            source.description,
        )
    console.print(table)


@main.group()
def knowledge() -> None:
    """Inspect marketplace expert knowledge."""


@knowledge.command("domains")
def knowledge_domains_cmd() -> None:
    """List knowledge domains."""
    from .knowledge.repository import list_domains

    table = Table(title="Marketplace Knowledge Domains")
    table.add_column("Domain")
    for domain in list_domains():
        table.add_row(domain.value)
    console.print(table)


@knowledge.command("rules")
@click.option("--domain", default=None, help="Filter by knowledge domain")
def knowledge_rules_cmd(domain: str | None) -> None:
    """List marketplace knowledge rules."""
    from .knowledge.repository import list_rules

    rules = list_rules(domain=domain) if domain else list_rules()
    table = Table(title="Marketplace Knowledge Rules")
    table.add_column("ID")
    table.add_column("Domain")
    table.add_column("Title")
    table.add_column("Signals")
    for rule in rules:
        table.add_row(rule.id, rule.domain.value, rule.title, ", ".join(rule.signals))
    console.print(table)


@knowledge.command("search")
@click.argument("query")
def knowledge_search_cmd(query: str) -> None:
    """Search marketplace knowledge rules."""
    from .knowledge.repository import search_rules

    rules = search_rules(query)
    table = Table(title=f"Knowledge Search: {query}")
    table.add_column("ID")
    table.add_column("Domain")
    table.add_column("Title")
    table.add_column("Recommendation")
    for rule in rules:
        table.add_row(rule.id, rule.domain.value, rule.title, rule.recommendation)
    console.print(table)


@knowledge.command("explain")
@click.option("--query", default="CTR", help="Knowledge query to explain")
def knowledge_explain_cmd(query: str) -> None:
    """Explain relevant knowledge rules."""
    from .knowledge.engine import find_relevant_rules

    rules = find_relevant_rules(query)
    if not rules:
        console.print(f"[yellow]No knowledge rules found for {query}[/]")
        return
    for rule in rules[:10]:
        console.print(f"[bold]{rule.domain.value}_RULE: {rule.title}[/]")
        console.print(f"Condition: {rule.condition}")
        console.print(f"Recommendation: {rule.recommendation}")
        console.print(f"Rationale: {rule.rationale}")
        console.print("")


@research.command("sample")
def research_sample_cmd() -> None:
    """Show deterministic marketplace research output shape."""
    from .research.engine import generate_marketplace_research_report
    from .research.models import ResearchObservation

    report = generate_marketplace_research_report(
        query="sample",
        own_observations=[
            ResearchObservation(
                sku="sample-sku",
                product_name="Sample product",
                seller_name="own",
                price=1200,
                rating=4.2,
                review_count=12,
                available=True,
            )
        ],
        competitor_observations=[
            ResearchObservation(
                sku="sample-sku",
                product_name="Competitor product",
                seller_name="competitor",
                source_url="https://example.test/product",
                price=1000,
                rating=4.7,
                review_count=60,
                available=True,
            )
        ],
    )
    table = Table(title="Marketplace Research Sample")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in report.summary.items():
        table.add_row(str(key), str(value))
    console.print(table)

    insights_table = Table(title="Sample Insights")
    insights_table.add_column("SKU")
    insights_table.add_column("Type")
    insights_table.add_column("Severity")
    insights_table.add_column("Reason")
    for insight in report.insights:
        insights_table.add_row(
            insight.sku,
            insight.insight_type.value,
            insight.severity,
            insight.reason,
        )
    console.print(insights_table)
    console.print("[yellow]External collection disabled: foundation only.[/]")


@research.command("ingest")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--query", default=None, help="Research query label")
@click.option("--source", "source_name", default="manual", help="Registered source name")
def research_ingest_cmd(path: str, query: str | None, source_name: str) -> None:
    """Validate and ingest a local competitor snapshot file."""
    from .research.knowledge.snapshot_store import save_snapshot
    from .research.snapshot_ingestion import SnapshotIngestionError, ingest_competitor_snapshot

    try:
        result = ingest_competitor_snapshot(path, query=query, source_name=source_name)
    except SnapshotIngestionError as exc:
        raise click.ClickException(str(exc)) from exc
    saved_snapshot = save_snapshot(result.snapshot)

    table = Table(title="Competitor Snapshot Ingestion")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Snapshot ID", saved_snapshot.id)
    table.add_row("Query", result.snapshot.query)
    table.add_row("Source", result.snapshot.source_name)
    table.add_row("Raw rows", str(result.raw_rows))
    table.add_row("Ingested rows", str(result.ingested_rows))
    table.add_row("Skipped rows", str(result.skipped_rows))
    table.add_row("Warnings", str(len(result.warnings)))
    console.print(table)

    if result.snapshot.observations:
        preview = Table(title="Observation Preview")
        preview.add_column("SKU")
        preview.add_column("Product")
        preview.add_column("Seller")
        preview.add_column("Price")
        preview.add_column("Rating")
        preview.add_column("Reviews")
        for observation in result.snapshot.observations[:10]:
            preview.add_row(
                observation.sku,
                observation.product_name or "-",
                observation.seller_name or "-",
                str(observation.price) if observation.price is not None else "-",
                str(observation.rating) if observation.rating is not None else "-",
                str(observation.review_count) if observation.review_count is not None else "-",
            )
        console.print(preview)

    for warning in result.warnings[:10]:
        console.print(f"[yellow]{escape(warning)}[/]")
    console.print("[yellow]External collection disabled: local snapshot ingestion only.[/]")


@research.group("firecrawl")
def research_firecrawl() -> None:
    """Ingest marketplace snapshots through Firecrawl."""


@research_firecrawl.command("ingest")
@click.argument("url")
@click.option("--query", required=True, help="Research query label")
@click.option("--api-key-env", default="FIRECRAWL_API_KEY", help="Environment variable for API key")
@click.option("--endpoint-url", default=None, help="Override Firecrawl scrape endpoint")
@click.option("--timeout", "timeout_seconds", default=60.0, help="HTTP timeout in seconds")
@click.option("--zero-data-retention", is_flag=True, help="Request Firecrawl zero data retention")
def research_firecrawl_ingest_cmd(
    url: str,
    query: str,
    api_key_env: str,
    endpoint_url: str | None,
    timeout_seconds: float,
    zero_data_retention: bool,
) -> None:
    """Fetch a Firecrawl scrape and save it as a market snapshot."""
    from .research.adapters.firecrawl import (
        FirecrawlConfig,
        FirecrawlIngestionError,
        ingest_firecrawl_snapshot,
    )
    from .research.knowledge.snapshot_store import save_snapshot

    config = FirecrawlConfig(
        api_key_env=api_key_env,
        endpoint_url=endpoint_url or FirecrawlConfig().endpoint_url,
        timeout_seconds=timeout_seconds,
        zero_data_retention=zero_data_retention,
    )
    try:
        result = ingest_firecrawl_snapshot(url=url, query=query, config=config)
    except FirecrawlIngestionError as exc:
        raise click.ClickException(str(exc)) from exc

    saved_snapshot = save_snapshot(result.ingestion.snapshot)
    table = Table(title="Firecrawl Snapshot Ingestion")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Snapshot ID", saved_snapshot.id)
    table.add_row("URL", escape(result.url))
    table.add_row("Query", result.ingestion.snapshot.query)
    table.add_row("Raw rows", str(result.ingestion.raw_rows))
    table.add_row("Ingested rows", str(result.ingestion.ingested_rows))
    table.add_row("Skipped rows", str(result.ingestion.skipped_rows))
    table.add_row("Warnings", str(len(result.ingestion.warnings)))
    if result.warning:
        table.add_row("Firecrawl warning", result.warning)
    console.print(table)


@research.command("snapshots")
def research_snapshots_cmd() -> None:
    """List stored market snapshots."""
    from .research.knowledge.snapshot_store import list_snapshots

    snapshots = list_snapshots()
    table = Table(title="Market Knowledge Snapshots")
    table.add_column("ID")
    table.add_column("Query")
    table.add_column("Source")
    table.add_column("Captured")
    table.add_column("Rows")
    for snapshot in snapshots:
        table.add_row(
            snapshot.id,
            snapshot.query or "-",
            snapshot.source_name,
            snapshot.captured_at.isoformat(),
            str(snapshot.observation_count),
        )
    console.print(table)


@research.command("snapshot")
@click.argument("snapshot_id")
def research_snapshot_cmd(snapshot_id: str) -> None:
    """Show one stored market snapshot."""
    from .research.knowledge.snapshot_store import load_snapshot

    snapshot = load_snapshot(snapshot_id)
    if snapshot is None:
        raise click.ClickException(f"Snapshot not found: {snapshot_id}")

    table = Table(title=f"Market Snapshot: {snapshot.id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Query", snapshot.query or "-")
    table.add_row("Source", snapshot.source_name)
    table.add_row("Captured", snapshot.captured_at.isoformat())
    table.add_row("Rows", str(snapshot.observation_count))
    console.print(table)

    preview = Table(title="Observation Preview")
    preview.add_column("SKU")
    preview.add_column("Seller")
    preview.add_column("Price")
    preview.add_column("Rating")
    preview.add_column("Reviews")
    preview.add_column("Available")
    for observation in snapshot.observations[:20]:
        preview.add_row(
            observation.sku,
            observation.seller_name or "-",
            str(observation.price) if observation.price is not None else "-",
            str(observation.rating) if observation.rating is not None else "-",
            str(observation.review_count) if observation.review_count is not None else "-",
            str(observation.available) if observation.available is not None else "-",
        )
    console.print(preview)


@research.command("compare")
@click.argument("snapshot_a")
@click.argument("snapshot_b")
def research_compare_cmd(snapshot_a: str, snapshot_b: str) -> None:
    """Compare two stored market snapshots and save insights."""
    from .research.knowledge.history import compare_snapshots, detect_trends
    from .research.knowledge.insight_store import save_insights
    from .research.knowledge.snapshot_store import load_snapshot

    previous = load_snapshot(snapshot_a)
    current = load_snapshot(snapshot_b)
    if previous is None:
        raise click.ClickException(f"Snapshot not found: {snapshot_a}")
    if current is None:
        raise click.ClickException(f"Snapshot not found: {snapshot_b}")

    insights = save_insights(compare_snapshots(previous, current))
    trends = detect_trends([previous, current])
    table = Table(title="Market Snapshot Comparison")
    table.add_column("Type")
    table.add_column("SKU")
    table.add_column("Severity")
    table.add_column("Message")
    for insight in insights[:50]:
        table.add_row(insight.insight_type, insight.sku, insight.severity, insight.message)
    console.print(table)

    trend_table = Table(title="Detected Trends")
    trend_table.add_column("SKU")
    trend_table.add_column("Metric")
    trend_table.add_column("Direction")
    trend_table.add_column("Delta")
    for trend in trends[:50]:
        trend_table.add_row(trend.sku, trend.metric, trend.direction, f"{trend.delta:.2f}")
    console.print(trend_table)


@research.group("insights", invoke_without_command=True)
@click.pass_context
def research_insights_cmd(ctx: click.Context) -> None:
    """Generate and inspect market insight engine output."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(research_insights_latest_cmd)


@research_insights_cmd.command("generate")
def research_insights_generate_cmd() -> None:
    """Generate market insights from stored snapshots."""
    from .research.insights.engine import generate_market_insights
    from .research.insights.report_builder import build_market_report

    insights = generate_market_insights()
    console.print(build_market_report(insights))
    console.print(f"[green]Generated and saved {len(insights)} market insights[/]")


@research_insights_cmd.command("latest")
def research_insights_latest_cmd() -> None:
    """List stored market insights."""
    from .research.knowledge.insight_store import list_insights

    insights = list_insights()
    table = Table(title="Market Knowledge Insights")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("SKU")
    table.add_column("Severity")
    table.add_column("Message")
    for insight in insights[:50]:
        table.add_row(
            insight.id,
            insight.insight_type,
            insight.sku,
            insight.severity,
            insight.message,
        )
    console.print(table)


@research_insights_cmd.command("risks")
def research_insights_risks_cmd() -> None:
    """Show market risks inferred from current snapshots."""
    from .research.insights.engine import detect_risks, generate_market_insights

    risks = detect_risks(generate_market_insights(persist=False))
    table = Table(title="Market Risks")
    table.add_column("Risk")
    table.add_column("SKU")
    table.add_column("Priority")
    table.add_column("Score")
    table.add_column("Message")
    for risk in risks[:50]:
        table.add_row(
            risk.risk_type,
            risk.sku,
            risk.priority.value,
            f"{risk.score:.0f}",
            risk.message,
        )
    console.print(table)


@research_insights_cmd.command("opportunities")
def research_insights_opportunities_cmd() -> None:
    """Show market opportunities inferred from current snapshots."""
    from .research.insights.engine import detect_opportunities, generate_market_insights

    opportunities = detect_opportunities(generate_market_insights(persist=False))
    table = Table(title="Market Opportunities")
    table.add_column("Opportunity")
    table.add_column("SKU")
    table.add_column("Priority")
    table.add_column("Score")
    table.add_column("Message")
    for opportunity in opportunities[:50]:
        table.add_row(
            opportunity.opportunity_type,
            opportunity.sku,
            opportunity.priority.value,
            f"{opportunity.score:.0f}",
            opportunity.message,
        )
    console.print(table)


@main.group()
def experiments() -> None:
    """Manage A/B experiments."""


@experiments.command("create")
@click.option("--sku", required=True, help="SKU to experiment on")
@click.option("--hypothesis", required=True, help="Experiment hypothesis")
@click.option("--action", required=True, help="Action to test")
@click.option("--risk", default=None, help="Risk level")
@click.option("--confidence", default=None, help="Confidence level")
def experiments_create(
    sku: str, hypothesis: str, action: str, risk: str | None, confidence: str | None,
) -> None:
    """Create a new experiment."""
    from .experiments.workflow import create_new_experiment

    exp = create_new_experiment(
        sku=sku, hypothesis=hypothesis, action=action, risk=risk, confidence=confidence,
    )
    console.print(f"[green]Created experiment {exp.id[:8]}...[/]")


@experiments.command("list")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--limit", default=20, help="Max results")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def experiments_list(status: str | None, limit: int, as_json: bool) -> None:
    """List experiments."""
    import json as json_mod

    from .experiments.experiment_summary import experiment_to_dict, format_experiment_list
    from .experiments.models import ExperimentStatus
    from .experiments.repository import list_experiments

    status_enum = ExperimentStatus(status) if status else None
    exps = list_experiments(status=status_enum, limit=limit)

    if as_json:
        data = [experiment_to_dict(e) for e in exps]
        console.print(json_mod.dumps(data, ensure_ascii=False, indent=2))
    else:
        console.print(format_experiment_list(exps))


@experiments.command("show")
@click.argument("exp_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def experiments_show(exp_id: str, as_json: bool) -> None:
    """Show experiment details."""
    import json as json_mod

    from .experiments.experiment_summary import experiment_to_dict, format_experiment_detail
    from .experiments.repository import get_experiment

    exp = get_experiment(exp_id)
    if exp is None:
        full_id = _resolve_short_experiment_id(exp_id)
        if full_id:
            exp = get_experiment(full_id)
    if exp is None:
        console.print(f"[red]Experiment {exp_id} not found.[/]")
        return
    if as_json:
        console.print(json_mod.dumps(experiment_to_dict(exp), ensure_ascii=False, indent=2))
    else:
        console.print(format_experiment_detail(exp))


@experiments.command("ready")
@click.argument("exp_id")
def experiments_ready(exp_id: str) -> None:
    """Mark experiment as ready."""
    from .experiments.workflow import mark_ready

    try:
        exp = mark_ready(exp_id, actor="cli")
        console.print(f"[green]Experiment {exp.id[:8]}... marked READY[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("start")
@click.argument("exp_id")
def experiments_start(exp_id: str) -> None:
    """Start an experiment."""
    from .experiments.workflow import mark_running

    try:
        exp = mark_running(exp_id, actor="cli")
        console.print(f"[green]Experiment {exp.id[:8]}... started (RUNNING)[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("pause")
@click.argument("exp_id")
def experiments_pause(exp_id: str) -> None:
    """Pause an experiment."""
    from .experiments.workflow import mark_paused

    try:
        exp = mark_paused(exp_id, actor="cli")
        console.print(f"[yellow]Experiment {exp.id[:8]}... paused (PAUSED)[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("resume")
@click.argument("exp_id")
def experiments_resume(exp_id: str) -> None:
    """Resume a paused experiment."""
    from .experiments.workflow import mark_running

    try:
        exp = mark_running(exp_id, actor="cli")
        console.print(f"[green]Experiment {exp.id[:8]}... resumed (RUNNING)[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("complete")
@click.argument("exp_id")
def experiments_complete(exp_id: str) -> None:
    """Complete an experiment."""
    from .experiments.workflow import mark_completed

    try:
        exp = mark_completed(exp_id, actor="cli")
        console.print(f"[green]Experiment {exp.id[:8]}... completed (COMPLETED)[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("cancel")
@click.argument("exp_id")
@click.option("--reason", required=True, help="Cancellation reason")
def experiments_cancel(exp_id: str, reason: str) -> None:
    """Cancel an experiment."""
    from .experiments.workflow import mark_cancelled

    try:
        exp = mark_cancelled(exp_id, reason=reason, actor="cli")
        console.print(f"[yellow]Experiment {exp.id[:8]}... cancelled: {reason}[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("fail")
@click.argument("exp_id")
@click.option("--reason", required=True, help="Failure reason")
def experiments_fail(exp_id: str, reason: str) -> None:
    """Mark experiment as failed."""
    from .experiments.workflow import mark_failed

    try:
        exp = mark_failed(exp_id, reason=reason, actor="cli")
        console.print(f"[red]Experiment {exp.id[:8]}... failed: {reason}[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("metrics")
@click.argument("exp_id")
@click.option("--baseline-orders", type=float, default=None)
@click.option("--baseline-revenue", type=float, default=None)
@click.option("--baseline-drr", type=float, default=None)
@click.option("--current-orders", type=float, default=None)
@click.option("--current-revenue", type=float, default=None)
@click.option("--current-drr", type=float, default=None)
def experiments_metrics(
    exp_id: str,
    baseline_orders: float | None,
    baseline_revenue: float | None,
    baseline_drr: float | None,
    current_orders: float | None,
    current_revenue: float | None,
    current_drr: float | None,
) -> None:
    """Update experiment metrics."""
    from .experiments.workflow import update_metrics

    try:
        exp = update_metrics(
            exp_id,
            baseline_orders=baseline_orders,
            baseline_revenue=baseline_revenue,
            baseline_drr=baseline_drr,
            current_orders=current_orders,
            current_revenue=current_revenue,
            current_drr=current_drr,
        )
        console.print(f"[green]Updated metrics for {exp.id[:8]}...[/]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("events")
@click.argument("exp_id")
def experiments_events(exp_id: str) -> None:
    """Show experiment events."""
    from .experiments.repository import list_experiment_events

    events = list_experiment_events(exp_id)
    if not events:
        console.print(f"[yellow]No events for {exp_id}[/]")
        return

    table = Table(title=f"Events for {exp_id[:8]}...")
    table.add_column("Time")
    table.add_column("Type")
    table.add_column("From")
    table.add_column("To")
    table.add_column("Actor")
    table.add_column("Reason")

    for event in events:
        table.add_row(
            event.created_at.strftime("%Y-%m-%d %H:%M"),
            event.event_type.value,
            event.from_status.value if event.from_status else "",
            event.to_status.value if event.to_status else "",
            event.actor or "",
            event.reason or "",
        )
    console.print(table)


@experiments.command("evaluate")
@click.argument("exp_id")
def experiments_evaluate(exp_id: str) -> None:
    """Evaluate experiment results."""
    from .experiments.workflow import evaluate_experiment

    try:
        exp = evaluate_experiment(exp_id)
        console.print(f"[green]Evaluated {exp.id[:8]}...[/]")
        if exp.success_score is not None:
            console.print(f"  Success score: {exp.success_score:.4f}")
        if exp.direction_accuracy is not None:
            console.print(f"  Direction accuracy: {exp.direction_accuracy:.4f}")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@experiments.command("report")
@click.argument("exp_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def experiments_report(exp_id: str, as_json: bool) -> None:
    """Show experiment report."""
    import json as json_mod

    from .experiments.experiment_summary import experiment_to_dict, format_experiment_report
    from .experiments.repository import get_experiment

    exp = get_experiment(exp_id)
    if exp is None:
        full_id = _resolve_short_experiment_id(exp_id)
        if full_id:
            exp = get_experiment(full_id)
    if exp is None:
        console.print(f"[red]Experiment {exp_id} not found.[/]")
        return
    if as_json:
        console.print(json_mod.dumps(experiment_to_dict(exp), ensure_ascii=False, indent=2))
    else:
        console.print(format_experiment_report(exp))


@experiments.command("hypotheses")
@click.option("--query", default="", help="Search hypotheses")
def experiments_hypotheses(query: str) -> None:
    """List file-based learning hypotheses."""
    from .learning.hypothesis_engine import list_hypotheses, search_hypotheses

    hypotheses = search_hypotheses(query) if query else list_hypotheses()
    table = Table(title="Experiment Hypotheses")
    table.add_column("ID")
    table.add_column("SKU")
    table.add_column("Type")
    table.add_column("Statement")
    for hypothesis in hypotheses:
        table.add_row(
            hypothesis.id,
            hypothesis.sku,
            hypothesis.experiment_type.value,
            hypothesis.statement,
        )
    console.print(table)


@experiments.command("similar")
@click.argument("exp_id")
@click.option("--limit", default=10, help="Max similar experiments")
def experiments_similar(exp_id: str, limit: int) -> None:
    """Find similar file-based learning experiments."""
    from .learning.similarity import find_similar_experiments_by_id

    matches = find_similar_experiments_by_id(exp_id, limit=limit)
    table = Table(title=f"Similar Experiments: {exp_id}")
    table.add_column("Experiment")
    table.add_column("Score")
    table.add_column("Result")
    table.add_column("Reasons")
    for match in matches:
        table.add_row(
            match.experiment_id,
            f"{match.score:.2f}",
            match.result.value,
            ", ".join(match.reasons),
        )
    console.print(table)


@experiments.command("insights")
def experiments_insights() -> None:
    """List stored experiment learning insights."""
    from .learning.repository import list_json

    rows = list_json("insights")
    table = Table(title="Experiment Learning Insights")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Type")
    table.add_column("Success")
    table.add_column("Message")
    for row in rows:
        table.add_row(
            str(row.get("id", "")),
            str(row.get("category", "")),
            str(row.get("experiment_type", "")),
            f"{float(row.get('success_rate', 0.0)):.0%}",
            str(row.get("message", "")),
        )
    console.print(table)


@experiments.command("stats")
def experiments_stats() -> None:
    """Show file-based experiment learning statistics."""
    from .learning.experiment_store import list_experiments as list_learning_experiments
    from .learning.statistics import build_experiment_statistics

    stats = build_experiment_statistics(list_learning_experiments())
    console.print("[bold]Experiment Learning Statistics[/]")
    console.print(f"Total experiments: {stats.total_experiments}")
    console.print(f"Success rate: {stats.success_rate:.0%}")
    if stats.by_experiment_type:
        console.print("By experiment type:")
        for exp_type, payload in stats.by_experiment_type.items():
            console.print(
                f"  - {exp_type}: {payload['count']} "
                f"experiments, success {float(payload['success_rate']):.0%}"
            )


@experiments.command("create-from-recommendation")
@click.argument("rec_id")
def experiments_create_from_recommendation(rec_id: str) -> None:
    """Create experiment from an approved/executed recommendation."""
    from .approval.models import RecommendationStatus
    from .approval.repository import get_recommendation
    from .experiments.workflow import create_from_recommendation

    rec = get_recommendation(rec_id)
    if rec is None:
        console.print(f"[red]Recommendation {rec_id} not found.[/]")
        return

    if rec.status not in (RecommendationStatus.APPROVED, RecommendationStatus.EXECUTED):
        console.print(
            f"[red]Recommendation must be APPROVED or EXECUTED, "
            f"got {rec.status.value}[/]"
        )
        return

    hypothesis = f"Test recommendation {rec.action.value} for {rec.sku}"
    expected_effect = rec.expected_effect if isinstance(rec.expected_effect, dict) else {}
    risk_val = rec.risk_level.value if rec.risk_level else None
    conf_val = rec.confidence_level.value if rec.confidence_level else None

    exp = create_from_recommendation(
        recommendation_id=rec.id,
        sku=rec.sku,
        action=rec.action.value,
        hypothesis=hypothesis,
        risk=risk_val,
        confidence=conf_val,
        expected_effect=expected_effect,
    )
    console.print(
        f"[green]Created experiment {exp.id[:8]}... "
        f"from recommendation {rec.id[:8]}...[/]"
    )


def _resolve_short_experiment_id(short_id: str) -> str | None:
    if len(short_id) >= 36:
        return short_id
    from .experiments.repository import list_experiments

    exps = list_experiments(limit=100)
    for exp in exps:
        if exp.id.startswith(short_id):
            return exp.id
    return None


if __name__ == "__main__":
    main()
