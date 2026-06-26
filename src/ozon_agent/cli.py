"""Ozon AI Agent CLI."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

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


@main.group()
def ingest() -> None:
    """Ingest external data into local agent storage."""


@ingest.group("ozon")
def ingest_ozon() -> None:
    """Live read-only Ozon Seller API ingestion."""


@ingest_ozon.command("datasets")
def ingest_ozon_datasets_cmd() -> None:
    """List supported live Ozon ingestion datasets."""
    from .ingestion.endpoints import READ_ONLY_ENDPOINTS

    table = Table(title="Live Ozon Ingestion Datasets")
    table.add_column("Dataset")
    table.add_column("Endpoint")
    table.add_column("Description")
    for dataset, endpoint in READ_ONLY_ENDPOINTS.items():
        table.add_row(dataset.value, endpoint.path, endpoint.description)
    console.print(table)


@ingest_ozon.command("run")
@click.argument("dataset")
@click.option("--date-from", default=None, help="Date from, YYYY-MM-DD")
@click.option("--date-to", default=None, help="Date to, YYYY-MM-DD")
@click.option("--limit", default=1000, help="Page size limit")
@click.option("--dry-run", is_flag=True, help="Build request without calling Ozon")
@click.option("--no-save-raw", is_flag=True, help="Do not save raw payload")
@click.option("--no-save-normalized", is_flag=True, help="Do not save normalized rows")
def ingest_ozon_run_cmd(
    dataset: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    dry_run: bool,
    no_save_raw: bool,
    no_save_normalized: bool,
) -> None:
    """Run one live read-only Ozon ingestion request."""
    from .ingestion.client import LiveOzonCredentialsError
    from .ingestion.models import LiveOzonDataset, LiveOzonIngestionRequest
    from .ingestion.service import ingest_live_ozon_dataset

    try:
        dataset_value = LiveOzonDataset(dataset)
        result = ingest_live_ozon_dataset(
            LiveOzonIngestionRequest(
                dataset=dataset_value,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                dry_run=dry_run,
                save_raw=not no_save_raw,
                save_normalized=not no_save_normalized,
            )
        )
    except (ValueError, LiveOzonCredentialsError) as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title="Live Ozon Ingestion")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Dataset", result.dataset.value)
    table.add_row("Endpoint", result.endpoint)
    table.add_row("Dry run", str(result.dry_run))
    table.add_row("Raw rows", str(result.raw_rows))
    table.add_row("Normalized rows", str(result.normalized_rows))
    table.add_row("Raw path", str(result.raw_path or ""))
    table.add_row("Normalized path", str(result.normalized_path or ""))
    table.add_row("Warnings", str(len(result.warnings)))
    console.print(table)
    for warning in result.warnings:
        console.print(f"[yellow]{escape(warning)}[/]")


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


@main.group("deploy")
def deploy_group() -> None:
    """VPS deployment commands."""


@deploy_group.command("vps")
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
@click.option("--branch", "-b", default="main", help="Git branch to deploy")
@click.option("--execute", is_flag=True, default=False, help="Execute deployment")
@click.option("--output", "-o", default=None, help="Output file path (JSON)")
def deploy_vps(target: str, branch: str, execute: bool, output: str | None) -> None:
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
            console.print(f"  ozon-agent deploy rollback --target {target}")
    else:
        console.print("[bold red]Deployment FAILED![/]")
        for step in deploy_result["steps"]:
            if not step["success"]:
                console.print(f"  Failed: {step['step']} — {step['stderr']}")
        console.print("\n[bold yellow]Rollback command:[/]")
        console.print(f"  ozon-agent deploy rollback --target {target}")


@deploy_group.command("verify")
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
def deploy_verify(target: str) -> None:
    """Verify deployment health on VPS."""
    from .deploy.health_check import format_health_report, run_full_health_check

    console.print(f"[bold blue]Running health checks on {target}...[/]")
    result = run_full_health_check(target)
    console.print(format_health_report(result))


@deploy_group.command("health")
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
def deploy_health(target: str) -> None:
    """Quick health check — env, secrets, CLI, sheets, supervisor."""
    from typing import Any

    from .deploy.health_check import (
        check_cli_available,
        check_dependencies,
        check_env_vars,
        check_git_revision,
        check_python_import,
        check_sheets_sync_dry_run,
        check_sheets_watch_interval,
        check_supervisor_status,
    )

    all_ok = True
    check_pairs: list[tuple[str, Any]] = [
        ("Git revision", check_git_revision),
        ("Python import", check_python_import),
        ("CLI", check_cli_available),
        ("Dependencies", check_dependencies),
        ("Env vars", check_env_vars),
        ("Sheets sync", check_sheets_sync_dry_run),
        ("Supervisor", check_supervisor_status),
        ("Sheets watch interval", check_sheets_watch_interval),
    ]

    for name, check_fn in check_pairs:
        try:
            result: dict[str, Any] = check_fn(target)
            if result["healthy"]:
                console.print(f"[green]OK[/] {name}")
            else:
                console.print(f"[red]FAIL[/] {name}")
                error = result.get("error", result.get("missing", ""))
                if error:
                    console.print(f"      {error}")
                all_ok = False
        except Exception as e:
            console.print(f"[yellow]WARNING[/] {name}: {e}")

    console.print()
    if all_ok:
        console.print("[bold green]All checks passed.[/]")
    else:
        console.print("[bold red]Some checks failed.[/]")


@deploy_group.command("rollback")
@click.option("--target", "-t", default="vps", help="Deployment target (SSH host)")
@click.option("--commits", "-c", default=1, help="Number of commits to roll back")
def deploy_rollback(target: str, commits: int) -> None:
    """Rollback to previous commit on VPS."""
    from .deploy.rollback import execute_rollback, format_rollback_text

    console.print(f"[bold yellow]Rolling back on {target} ({commits} commit(s))...[/]")
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


@learning.command("success-db")
def learning_success_db() -> None:
    """Show recommendation success database statistics."""
    from .learning.success_database import build_success_database, save_database_report

    db = build_success_database()

    if db.total_records == 0:
        console.print("[yellow]No success records found.[/]")
        return

    table = Table(title="Recommendation Success Database")
    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Total Records", str(db.total_records))
    table.add_row("Overall Success Rate", f"{db.overall_success_rate * 100:.1f}%")
    table.add_row("Average Score", f"{db.overall_average_score:.3f}")

    console.print(table)

    if db.by_action:
        action_table = Table(title="By Action Type")
        action_table.add_column("Action")
        action_table.add_column("Total")
        action_table.add_column("Success Rate")
        action_table.add_column("Avg Score")

        for action, stats in sorted(db.by_action.items()):
            action_table.add_row(
                action,
                str(stats.total),
                f"{stats.success_rate * 100:.1f}%",
                f"{stats.average_score:.3f}",
            )
        console.print(action_table)

    path = save_database_report(db)
    console.print(f"[dim]Report saved: {path}[/]")


@learning.command("confidence")
@click.argument("action")
@click.option("--sku", default=None, help="SKU for SKU-specific confidence")
def learning_confidence(action: str, sku: str | None) -> None:
    """Show confidence explanation for an action/SKU combination."""
    from .learning.success_database import get_confidence_explanation

    explanation = get_confidence_explanation(action, sku)
    console.print(explanation)


@learning.command("impact")
def learning_impact() -> None:
    """Show recommendation impact records."""
    from .learning.auto_outcomes import load_impact_records

    records = load_impact_records()

    if not records:
        console.print("[yellow]No impact records found.[/]")
        return

    table = Table(title=f"Recommendation Impact ({len(records)} records)")
    table.add_column("ID")
    table.add_column("SKU")
    table.add_column("Action")
    table.add_column("Revenue Δ")
    table.add_column("Profit Δ")
    table.add_column("DRR Δ")
    table.add_column("Window")

    for rec in records[-20:]:
        rev_delta = f"{rec.revenue_delta_pct:+.1f}%" if rec.revenue_delta_pct is not None else "—"
        prof_delta = f"{rec.profit_delta_pct:+.1f}%" if rec.profit_delta_pct is not None else "—"
        drr_delta = f"{rec.drr_delta_pct:+.1f}%" if rec.drr_delta_pct is not None else "—"
        table.add_row(
            rec.recommendation_id[:12],
            rec.sku,
            rec.action,
            rev_delta,
            prof_delta,
            drr_delta,
            f"{rec.window_days}d",
        )

    console.print(table)


@main.group()
def sku() -> None:
    """SKU intelligence — comparison, history, risk, and opportunities."""


@sku.command("compare")
@click.argument("sku1")
@click.argument("sku2")
def sku_compare(sku1: str, sku2: str) -> None:
    """Compare two SKUs across key metrics."""
    from .intelligence.sku_intelligence import (
        SkuMetrics,
        compare_skus,
        format_comparison,
    )

    metrics1 = SkuMetrics(sku=sku1, name=sku1)
    metrics2 = SkuMetrics(sku=sku2, name=sku2)

    comp = compare_skus(metrics1, metrics2)
    console.print(format_comparison(comp))


@sku.command("history")
@click.argument("sku_name")
@click.option("--days", default=30, help="Number of days to look back")
def sku_history(sku_name: str, days: int) -> None:
    """Show SKU history for the given period."""
    from .intelligence.sku_intelligence import (
        build_sku_history,
        format_history,
    )

    sample_data = [
        {
            "date": f"2026-06-{d:02d}",
            "revenue": 10000 + d * 100,
            "profit": 3000 + d * 30,
            "orders": 50 + d,
            "margin": 35.0,
            "drr": 8.0,
        }
        for d in range(1, min(days + 1, 22))
    ]

    history = build_sku_history(sku_name, sample_data, period_days=days)
    console.print(format_history(history))


@sku.command("risk")
@click.argument("sku_name")
def sku_risk(sku_name: str) -> None:
    """Detect risks for a SKU."""
    from .intelligence.sku_intelligence import (
        SkuMetrics,
        detect_sku_risk,
        format_risk,
    )

    metrics = SkuMetrics(sku=sku_name, name=sku_name, margin=25.0, drr=15.0, stock_days=10)
    risk = detect_sku_risk(sku_name, metrics)
    console.print(format_risk(risk))


@sku.command("opportunity")
@click.argument("sku_name")
def sku_opportunity(sku_name: str) -> None:
    """Detect opportunities for a SKU."""
    from .intelligence.sku_intelligence import (
        SkuMetrics,
        detect_sku_opportunity,
        format_opportunity,
    )

    metrics = SkuMetrics(sku=sku_name, name=sku_name, margin=45.0, drr=5.0, trend_revenue_pct=20.0)
    opp = detect_sku_opportunity(sku_name, metrics)
    console.print(format_opportunity(opp))


@main.group()
def quality() -> None:
    """Data quality monitoring and reporting."""


@quality.command("report")
@click.option("--save", is_flag=True, help="Save report to disk")
def quality_report(save: bool) -> None:
    """Generate data quality report."""
    from .quality.data_quality import (
        build_quality_report,
        format_quality_report,
        save_quality_report,
    )

    console.print("[bold blue]Generating data quality report...[/]")

    daily_data = []
    try:
        from .sheets.file_source import load_sales
        daily_data = load_sales() or []
    except Exception:
        pass

    report = build_quality_report(daily_data=daily_data)
    console.print(format_quality_report(report))

    if save:
        path = save_quality_report(report)
        console.print(f"[dim]Report saved: {path}[/]")


@main.group()
def cockpit() -> None:
    """Management cockpit — executive dashboard."""


@cockpit.command("build")
@click.option("--save", is_flag=True, help="Export to Google Sheets")
def cockpit_build(save: bool) -> None:
    """Build management cockpit from current data."""
    from .sheets.exporters.management_cockpit import (
        build_cockpit_from_data,
    )

    console.print("[bold blue]Building Management Cockpit...[/]")

    daily_data = []
    try:
        from .sheets.file_source import load_sales
        daily_data = load_sales() or []
    except Exception:
        pass

    cockpit = build_cockpit_from_data(daily_summary=daily_data)

    console.print(f"\n[bold]Management Cockpit[/] ({cockpit.generated_at})")
    console.print(f"\nRevenue: {len(cockpit.revenue)} metrics")
    for m in cockpit.revenue:
        console.print(f"  {m.name}: {m.value:,.0f}")

    console.print(f"\nProfit: {len(cockpit.profit)} metrics")
    for m in cockpit.profit:
        console.print(f"  {m.name}: {m.value:,.0f}")

    console.print(f"\nAdvertising: {len(cockpit.advertising)} metrics")
    for m in cockpit.advertising:
        console.print(f"  {m.name}: {m.value:,.0f}")

    console.print(f"\nRisks: {len(cockpit.risks)}")
    for r in cockpit.risks:
        console.print(f"  [{r.severity}] {r.sku}: {r.risk_type}")

    console.print(f"\nOpportunities: {len(cockpit.opportunities)}")
    for o in cockpit.opportunities:
        console.print(f"  {o.sku}: {o.opportunity} (score: {o.score:.0f})")

    console.print(f"\nActions Required: {len(cockpit.actions)}")
    for a in cockpit.actions:
        console.print(f"  [{a.priority}] {a.action} ({a.sku})")


@main.command("system-audit")
@click.option("--save", is_flag=True, help="Save report to disk")
def system_audit(save: bool) -> None:
    """Run full system audit — verify all components are running."""
    from .operations.system_audit import (
        format_audit,
        run_system_audit,
        save_audit_report,
    )

    console.print("[bold blue]Running system audit...[/]")
    audit = run_system_audit()
    console.print(format_audit(audit))

    status_color = "green" if audit.overall_status == "HEALTHY" else "red"
    console.print(f"\n[bold {status_color}]Overall: {audit.overall_status}[/]")

    if save:
        path = save_audit_report(audit)
        console.print(f"[dim]Report saved: {path}[/]")


@main.command("daily-brief")
@click.option("--save", is_flag=True, help="Save briefing to disk")
def daily_brief(save: bool) -> None:
    """Generate daily briefing with risks, opportunities, and actions."""
    from .operations.daily import (
        format_briefing,
        generate_daily_briefing,
        save_briefing,
    )

    console.print("[bold blue]Generating daily briefing...[/]")
    briefing = generate_daily_briefing()
    console.print(format_briefing(briefing))

    if save:
        path = save_briefing(briefing)
        console.print(f"[dim]Briefing saved: {path}[/]")


@main.command("forecast")
@click.argument("sku_name")
@click.option("--save", is_flag=True, help="Save forecast to disk")
def forecast_cmd(sku_name: str, save: bool) -> None:
    """Generate forecast for a SKU."""
    from .operations.forecasting import (
        build_sku_forecast,
        format_forecast,
        save_forecast,
    )

    daily_data = []
    try:
        from .sheets.file_source import load_sales
        daily_data = load_sales() or []
    except Exception:
        pass

    console.print(f"[bold blue]Forecasting {sku_name}...[/]")
    forecast = build_sku_forecast(sku_name, daily_data)
    console.print(format_forecast(forecast))

    if save:
        path = save_forecast(forecast)
        console.print(f"[dim]Forecast saved: {path}[/]")


@main.command("tracking-stats")
def tracking_stats_cmd() -> None:
    """Show recommendation tracking statistics."""
    from .operations.tracking import format_tracking_stats, get_tracking_stats

    stats = get_tracking_stats()
    console.print(format_tracking_stats(stats))


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


@main.group()
def sheets() -> None:
    """Google Sheets operations interface."""


@sheets.command("setup")
@click.option("--title", default="Ozon AI Agent", help="Spreadsheet title")
def sheets_setup(title: str) -> None:
    """Create a new Google Spreadsheet with all configured tabs."""
    from .sheets.setup import setup_spreadsheet

    console.print(f"[bold blue]Creating spreadsheet: {title}...[/]")
    try:
        spreadsheet_id = setup_spreadsheet(title)
        console.print("[bold green]Spreadsheet created![/]")
        console.print(f"  ID: {spreadsheet_id}")
        console.print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        console.print("")
        console.print("[bold yellow]Add to .env:[/]")
        console.print(f"  GOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")


@sheets.command("sync")
@click.option("--tab", default=None, help="Sync single tab (default: all)")
@click.option(
    "--source", default=None,
    type=click.Choice(["auto", "db", "files"]),
    help="Data source: auto (detect), db (PostgreSQL), files (file-based only)",
)
@click.option("--delay", default=None, type=int, help="Delay between tabs in seconds (default: 10)")
def sheets_sync(tab: str | None, source: str | None, delay: int | None) -> None:
    """Sync agent data to Google Sheets."""
    from .sheets.sync import sync_all, sync_tab

    if tab:
        console.print(f"[bold blue]Syncing {tab}...[/]")
        try:
            count = sync_tab(tab, source=source)
            console.print(f"[green]{tab}: {count} rows[/]")
        except Exception as e:
            console.print(f"[red]Failed: {e}[/]")
        return

    console.print("[bold blue]Syncing all tabs...[/]")
    results = sync_all(source=source, delay=delay)

    table = Table(title="Sheets Sync Results")
    table.add_column("Tab")
    table.add_column("Rows")
    table.add_column("Status")

    for tab_name, count in results.items():
        if count >= 0:
            table.add_row(tab_name, str(count), "[green]OK[/]")
        else:
            table.add_row(tab_name, "—", "[red]FAILED[/]")
    console.print(table)

    total = sum(v for v in results.values() if v > 0)
    console.print(f"[bold green]Total: {total} rows synced[/]")


@sheets.command("watch")
@click.option("--interval", default=30, help="Sync interval in minutes")
@click.option(
    "--source",
    type=click.Choice(["db", "files"]),
    default=None,
    help="Data source override",
)
def sheets_watch(interval: int, source: str | None) -> None:
    """Start background auto-refresh sync."""
    from .sheets.scheduler import start_watcher

    console.print(f"[bold blue]Starting sheets watcher (every {interval} min)...[/]")
    console.print("[yellow]Press Ctrl+C to stop[/]")
    start_watcher(interval_minutes=interval, source=source)


@sheets.command("status")
def sheets_status() -> None:
    """Show last sync time per tab."""
    from .sheets.sync import get_sync_status

    status = get_sync_status()
    if not status:
        console.print("[yellow]No sync history. Run 'ozon-agent sheets sync' first.[/]")
        return

    table = Table(title="Sheets Sync Status")
    table.add_column("Tab")
    table.add_column("Last Sync")

    for tab, ts in sorted(status.items()):
        table.add_row(tab, ts)
    console.print(table)


@sheets.command("health")
@click.option("--save", is_flag=True, help="Save report to disk")
def sheets_health(save: bool) -> None:
    """Audit workbook for formula errors and structural issues."""
    from .sheets.health import audit_workbook, save_audit_report

    console.print("[bold blue]Auditing workbook health...[/]")
    try:
        health = audit_workbook()
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")
        return

    table = Table(title=f"Workbook Health: {health.title}")
    table.add_column("Tab")
    table.add_column("Formulas")
    table.add_column("Errors")
    table.add_column("Status")

    for tab in health.tabs:
        if not tab.exists:
            table.add_row(tab.tab, "—", "—", "[red]MISSING[/]")
        else:
            color = "green" if tab.error_count == 0 else "red"
            table.add_row(
                tab.tab,
                str(tab.formula_count),
                str(tab.error_count),
                f"[{color}]{tab.status}[/]",
            )

    console.print(table)
    console.print(f"Total formulas: {health.total_formulas}")
    console.print(f"Total errors: {health.total_errors}")
    if health.error_summary:
        console.print(f"Error breakdown: {health.error_summary}")

    status_color = "green" if health.status == "OK" else "red"
    console.print(f"\n[bold {status_color}]Workbook Status: {health.status}[/]")

    if save:
        path = save_audit_report(health)
        console.print(f"[dim]Report saved: {path}[/]")


@sheets.command("repair")
@click.option("--dry-run", is_flag=True, default=True, help="Preview changes without applying")
@click.option("--apply", "do_apply", is_flag=True, help="Actually apply repairs")
def sheets_repair(dry_run: bool, do_apply: bool) -> None:
    """Check and repair workbook issues (formulas, tabs, references)."""
    from .sheets.repair import repair_workbook

    actually_dry = not do_apply
    mode = "DRY RUN" if actually_dry else "APPLYING"
    console.print(f"[bold blue]Workbook Repair ({mode})...[/]")

    try:
        result = repair_workbook(dry_run=actually_dry)
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")
        return

    if not result.actions:
        console.print("[green]No issues found. Workbook is healthy.[/]")
        return

    table = Table(title="Repair Actions")
    table.add_column("Tab")
    table.add_column("Issue")
    table.add_column("Fix")
    table.add_column("Applied")

    for action in result.actions:
        applied_str = "[green]YES[/]" if action.applied else "[yellow]NO[/]"
        table.add_row(action.tab, action.issue, action.fix, applied_str)

    console.print(table)
    console.print(f"Total actions: {result.total_actions}")
    console.print(f"Applied: {result.applied_count}")


@sheets.command("create-month")
@click.option("--month", default=None, help="Target month YYYY-MM (default: next month)")
def sheets_create_month(month: str | None) -> None:
    """Create next month's Daily Input tab from template."""
    from .sheets.auto_month import create_next_month_tab

    console.print("[bold blue]Creating monthly tab...[/]")

    try:
        result = create_next_month_tab(target_month=month)
    except Exception as e:
        console.print(f"[red]Failed: {e}[/]")
        return

    if result.created:
        console.print(f"[green]{result.message}[/]")
        console.print(f"  Tab: {result.tab_name}")
        console.print(f"  Source: {result.source_tab}")
        console.print(f"  Rows: {result.rows}, Columns: {result.columns}")
    else:
        console.print(f"[yellow]{result.message}[/]")


@main.group()
def cogs() -> None:
    """Manage COGS (sebestoimost) per SKU."""


@cogs.command("status")
def cogs_status() -> None:
    """Show COGS coverage report."""
    from .cogs.coverage import calculate_coverage, format_coverage_report
    from .cogs.service import _load_products

    products = _load_products()
    report = calculate_coverage(products)
    console.print(format_coverage_report(report))


@cogs.command("list")
def cogs_list() -> None:
    """List all COGS entries."""
    from .cogs.service import list_cogs

    records = list_cogs()
    if not records:
        console.print("[yellow]No COGS entries found.[/]")
        return

    table = Table(title=f"COGS ({len(records)} entries)")
    table.add_column("SKU")
    table.add_column("Product")
    table.add_column("Unit Cost")
    table.add_column("Logistics")
    table.add_column("Packaging")
    table.add_column("Source")
    table.add_column("Updated")

    for r in records:
        table.add_row(
            r.sku,
            r.product_name or "—",
            f"{r.unit_cost:.0f}",
            f"{r.logistics_cost:.0f}",
            f"{r.packaging_cost:.0f}",
            r.source,
            r.updated_at.strftime("%Y-%m-%d"),
        )
    console.print(table)


@cogs.command("set")
@click.argument("sku")
@click.argument("unit_cost", type=float)
@click.option("--logistics", default=0.0, type=float, help="Logistics cost per unit")
@click.option("--packaging", default=0.0, type=float, help="Packaging cost per unit")
@click.option("--name", default=None, help="Product name")
def cogs_set(
    sku: str,
    unit_cost: float,
    logistics: float,
    packaging: float,
    name: str | None,
) -> None:
    """Set COGS for a SKU."""
    from .cogs.service import set_cogs

    try:
        record = set_cogs(
            sku=sku,
            unit_cost=unit_cost,
            logistics_cost=logistics,
            packaging_cost=packaging,
            product_name=name,
        )
        console.print("[green]COGS updated[/]")
        console.print(f"  SKU: {record.sku}")
        console.print(f"  Unit cost: {record.unit_cost:.0f}")
        console.print("  This SKU will now be included in Daily P&L.")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")


@cogs.command("missing")
def cogs_missing() -> None:
    """Show products without COGS."""
    from .cogs.service import missing_cogs

    items = missing_cogs()
    if not items:
        console.print("[green]All products have COGS.[/]")
        return

    console.print(f"[yellow]Missing COGS: {len(items)} products[/]")
    for item in items[:20]:
        console.print(f"  - SKU {item['sku']} — {item['name']}")


@cogs.command("import")
@click.argument("path")
def cogs_import(path: str) -> None:
    """Import COGS from CSV file."""
    from .cogs.importer import import_csv

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        count = import_csv(text)
        console.print(f"[green]Imported {count} COGS entries from {path}[/]")
    except FileNotFoundError:
        console.print(f"[red]File not found: {path}[/]")
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/]")


@cogs.command("clear")
def cogs_clear() -> None:
    """Clear all COGS entries."""
    from .cogs.repository import clear_all

    count = clear_all()
    console.print(f"[yellow]Cleared {count} COGS entries.[/]")


@main.group()
def performance() -> None:
    """Read-only Ozon Performance API commands."""


@performance.command("campaigns")
@click.option("--max-pages", default=1, help="Max pages to fetch")
@click.option("--page-delay", default=0.0, help="Delay between pages in seconds")
@click.option("--dry-run", is_flag=True, help="Build request without calling API")
def performance_campaigns(max_pages: int, page_delay: float, dry_run: bool) -> None:
    """Fetch read-only campaign list from Performance API."""
    from .performance.service import fetch_campaigns

    try:
        result = fetch_campaigns(
            max_pages=max_pages,
            page_delay=page_delay,
            dry_run=dry_run,
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title="Performance Campaigns")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Type")
    for campaign in result.campaigns:
        table.add_row(
            str(campaign.id),
            campaign.name,
            campaign.status,
            campaign.campaign_type,
        )
    console.print(table)
    console.print(f"[green]Total: {len(result.campaigns)} campaigns[/]")
    for warning in result.warnings:
        console.print(f"[yellow]{escape(warning)}[/]")


@performance.command("stats")
@click.option("--date-from", required=True, help="Date from, YYYY-MM-DD")
@click.option("--date-to", required=True, help="Date to, YYYY-MM-DD")
@click.option("--campaign-id", default=None, help="Filter by campaign ID")
@click.option("--max-campaigns", default=1, help="Max campaigns to include")
@click.option("--poll-interval", default=60.0, help="Poll interval in seconds")
@click.option("--timeout", default=900.0, help="Total timeout in seconds")
@click.option("--dry-run", is_flag=True, help="Build request without calling API")
def performance_stats(
    date_from: str,
    date_to: str,
    campaign_id: str | None,
    max_campaigns: int,
    poll_interval: float,
    timeout: float,
    dry_run: bool,
) -> None:
    """Create and fetch a Performance Stats report."""
    from .performance.models import PerformanceReportRequest
    from .performance.service import fetch_stats

    campaign_ids: list[int] = []
    if campaign_id:
        try:
            campaign_ids = [int(campaign_id)]
        except ValueError:
            raise click.ClickException(f"Invalid campaign ID: {campaign_id}")

    if max_campaigns > 0 and not campaign_ids:
        from .performance.client import PerformanceClient

        try:
            client = PerformanceClient.from_env()
            page_data = client.get_campaigns_page(page=1, page_size=max_campaigns)
            parsed = client.parse_campaigns_response(page_data)
            campaign_ids = [c.id for c in parsed.campaigns[:max_campaigns]]
            client.close()
        except Exception as exc:
            console.print(f"[yellow]Could not fetch campaigns: {exc}[/]")

    request = PerformanceReportRequest(
        date_from=date_from,
        date_to=date_to,
        campaign_ids=campaign_ids,
    )

    try:
        result = fetch_stats(
            request,
            poll_interval=poll_interval,
            timeout=timeout,
            dry_run=dry_run,
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title="Performance Stats Report")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Report ID", result.report_id)
    table.add_row("Status", result.status.value)
    table.add_row("Rows", str(len(result.rows)))
    console.print(table)
    for warning in result.warnings:
        console.print(f"[yellow]{escape(warning)}[/]")

    if result.rows:
        stats_table = Table(title="Stats Preview")
        stats_table.add_column("Date")
        stats_table.add_column("SKU")
        stats_table.add_column("Spend")
        stats_table.add_column("Orders")
        stats_table.add_column("DRR")
        for row in result.rows[:20]:
            stats_table.add_row(
                row.date,
                row.sku,
                f"{row.spend:.2f}",
                str(row.orders),
                f"{row.drr:.2f}",
            )
        console.print(stats_table)


@performance.command("reports")
def performance_reports() -> None:
    """List locally saved performance stats report files."""
    from .performance.store import list_normalized_stats_files

    files = list_normalized_stats_files()
    table = Table(title="Local Performance Stats Reports")
    table.add_column("File")
    table.add_column("Size")
    table.add_column("Modified")
    for path in files:
        stat = path.stat()
        table.add_row(
            path.name,
            f"{stat.st_size / 1024:.1f} KB",
            f"{stat.st_mtime:.0f}",
        )
    console.print(table)


@performance.command("report-status")
@click.argument("report_id")
@click.option("--download", is_flag=True, help="Download completed report")
def performance_report_status(report_id: str, download: bool) -> None:
    """Check status of a Performance Stats report."""
    from .performance.client import PerformanceClient

    try:
        client = PerformanceClient.from_env()
        body = client.get_report_status(report_id)
        result_data = body.get("result", body)
        status_str = str(result_data.get("status", "UNKNOWN"))
        client.close()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title=f"Report Status: {report_id}")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Report ID", report_id)
    table.add_row("Status", status_str)
    console.print(table)

    if download and status_str.upper() == "DONE":
        from .performance.service import download_report

        try:
            result = download_report(report_id)
            console.print(f"[green]Downloaded {len(result.rows)} rows[/]")
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc


@main.group("retro")
def retro() -> None:
    """Historical data activation and retro learning commands."""


@retro.command("activate")
def retro_activate() -> None:
    """Activate imported ollama-bot historical data into runtime files."""
    from .retro.activation import activate_historical_data

    result = activate_historical_data()
    table = Table(title="Historical Data Activation")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in result.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)


@retro.command("learning-summary")
def retro_learning_summary() -> None:
    """Show historical learning summary."""
    from .retro.activation import load_learning_summary

    summary = load_learning_summary()
    table = Table(title="Historical Learning Summary")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in summary.items():
        table.add_row(str(key), str(value))
    console.print(table)


@retro.command("daily-history")
def retro_daily_history() -> None:
    """Show activated daily history preview."""
    from .retro.historical_aggregator import build_daily_history

    rows = build_daily_history()
    table = Table(title=f"Historical Daily History ({len(rows)} rows)")
    table.add_column("Date")
    table.add_column("Revenue")
    table.add_column("Orders")
    table.add_column("Advertising")
    table.add_column("COGS")
    table.add_column("Profit")
    table.add_column("DRR")
    for row in rows[-20:]:
        table.add_row(
            str(row.get("date", "")),
            f"{float(row.get('revenue') or 0):.2f}",
            str(row.get("orders", 0)),
            f"{float(row.get('advertising') or 0):.2f}",
            f"{float(row.get('cogs') or 0):.2f}",
            f"{float(row.get('profit') or 0):.2f}",
            f"{float(row.get('drr') or 0):.2f}",
        )
    console.print(table)


@main.group("telegram")
def telegram() -> None:
    """Telegram bot runtime."""


@dataclass(frozen=True)
class TelegramRuntimeConfig:
    request_timeout: int
    retry_attempts: int
    retry_backoff_seconds: int
    proxy_url: str | None = None


def _get_env_int(name: str, default: int, minimum: int = 1) -> int:
    import os

    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise click.ClickException(f"{name} must be an integer") from exc
    if value < minimum:
        raise click.ClickException(f"{name} must be >= {minimum}")
    return value


def _telegram_runtime_config_from_env() -> TelegramRuntimeConfig:
    import os

    proxy_url = os.environ.get("TELEGRAM_PROXY_URL", "").strip() or None
    return TelegramRuntimeConfig(
        request_timeout=_get_env_int("TELEGRAM_REQUEST_TIMEOUT", 30, minimum=5),
        retry_attempts=_get_env_int("TELEGRAM_RETRY_ATTEMPTS", 3, minimum=1),
        retry_backoff_seconds=_get_env_int(
            "TELEGRAM_RETRY_BACKOFF_SECONDS",
            10,
            minimum=0,
        ),
        proxy_url=proxy_url,
    )


def _mask_proxy_url(proxy_url: str | None) -> str:
    if not proxy_url:
        return "none"

    import urllib.parse

    parsed = urllib.parse.urlsplit(proxy_url)
    if not parsed.username and not parsed.password:
        return proxy_url

    username = urllib.parse.quote(parsed.username or "")
    password = "***" if parsed.password else ""
    auth = username
    if password:
        auth = f"{auth}:{password}"
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{auth}@{host}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def _build_telegram_opener(proxy_url: str | None) -> Any:
    import urllib.parse
    import urllib.request

    if not proxy_url:
        return urllib.request.build_opener()

    parsed = urllib.parse.urlsplit(proxy_url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise click.ClickException(
            "TELEGRAM_PROXY_URL supports http:// or https:// proxy URLs in this build. "
            "SOCKS5 needs an extra dependency and is intentionally not enabled here."
        )
    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    return urllib.request.build_opener(proxy_handler)


def _telegram_api_json(
    opener: Any,
    url: str,
    *,
    data: bytes | None = None,
    timeout: int,
    attempts: int,
    backoff_seconds: int,
    action: str,
) -> dict[str, Any]:
    import json
    import time
    import urllib.error
    import urllib.request

    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request: str | urllib.request.Request
            request = urllib.request.Request(url, data=data) if data is not None else url
            with opener.open(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last_exc = exc
            console.print(
                "[yellow]Telegram API warning: "
                f"{escape(action)} attempt {attempt}/{attempts} failed: "
                f"{escape(type(exc).__name__)}[/]"
            )
            if attempt < attempts and backoff_seconds > 0:
                time.sleep(backoff_seconds)
    if last_exc is not None:
        raise last_exc
    return {}


def _telegram_send_message(
    opener: Any,
    base_url: str,
    chat_id: Any,
    text: str,
    config: TelegramRuntimeConfig,
) -> bool:
    import urllib.parse

    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        _telegram_api_json(
            opener,
            f"{base_url}/sendMessage",
            data=data,
            timeout=config.request_timeout,
            attempts=config.retry_attempts,
            backoff_seconds=config.retry_backoff_seconds,
            action="sendMessage",
        )
    except Exception as exc:
        console.print(
            "[red]Telegram sendMessage failed after retries: "
            f"{escape(type(exc).__name__)}[/]"
        )
        return False
    console.print("[green]Telegram sendMessage success[/]")
    return True


@telegram.command("run")
@click.option("--dry-run", is_flag=True, help="Validate configuration without polling")
def telegram_run(dry_run: bool) -> None:
    """Run Telegram bot with InlineKeyboard and callback_query support."""
    import os
    import time
    import urllib.parse

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise click.ClickException("TELEGRAM_BOT_TOKEN is not configured")
    config = _telegram_runtime_config_from_env()

    if dry_run:
        console.print("[green]Telegram bot configuration OK[/]")
        console.print(f"Timeout: {config.request_timeout}s")
        console.print(f"Retry attempts: {config.retry_attempts}")
        console.print(f"Proxy: {_mask_proxy_url(config.proxy_url)}")
        return

    # Import callback router and handlers
    from .telegram.callbacks.router import route_callback_data
    from .telegram.callbacks import (  # noqa: F401 — side-effect imports for @register
        main_menu_cb, today_cb, business_cb, logistics_cb, ads_cb,
        finance_cb, risks_cb, tasks_cb, experiments_cb, system_cb,
        store_cb, quick_cb, rec_cb, owner_cb,
    )

    opener = _build_telegram_opener(config.proxy_url)
    base_url = f"https://api.telegram.org/bot{token}"
    offset = 0
    console.print("[green]Telegram bot polling started (urllib + InlineKeyboard)[/]")
    while True:
        try:
            params = urllib.parse.urlencode({"timeout": 30, "offset": offset})
            payload = _telegram_api_json(
                opener,
                f"{base_url}/getUpdates?{params}",
                timeout=config.request_timeout + 10,
                attempts=config.retry_attempts,
                backoff_seconds=config.retry_backoff_seconds,
                action="getUpdates",
            )
            for update in payload.get("result", []):
                offset = max(offset, int(update.get("update_id", 0)) + 1)

                # Handle callback_query (InlineKeyboard button presses)
                callback_query = update.get("callback_query")
                if callback_query:
                    query_id = callback_query.get("id")
                    data = callback_query.get("data", "")
                    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
                    user = str((callback_query.get("from") or {}).get("username") or "telegram")
                    if data and chat_id:
                        console.print(f"[cyan]Callback: {escape(data)}[/]")
                        result = route_callback_data(data)
                        if result:
                            _telegram_send_message(opener, base_url, chat_id, result, config)
                        # Answer the callback query to dismiss loading spinner
                        _telegram_api_json(
                            opener,
                            f"{base_url}/answerCallbackQuery",
                            data=urllib.parse.urlencode({"callback_query_id": query_id}).encode(),
                            timeout=10, attempts=1, backoff_seconds=0,
                            action="answerCallbackQuery",
                        )
                    continue

                # Handle regular messages (text commands)
                message = update.get("message") or {}
                text = str(message.get("text") or "").strip()
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                user = str((message.get("from") or {}).get("username") or "telegram")
                if not text or chat_id is None:
                    continue
                command = text.split(maxsplit=1)[0]
                console.print(f"[cyan]Telegram received command: {escape(command)}[/]")

                if command == "/start":
                    from .telegram.keyboards.main_menu import main_menu_keyboard
                    import json as json_mod
                    kb = main_menu_keyboard()
                    reply_markup = json_mod.dumps({"inline_keyboard": [[{"text": b.text, "callback_data": b.callback_data} for b in row] for row in kb.inline_keyboard]})
                    data = urllib.parse.urlencode({
                        "chat_id": chat_id,
                        "text": "🏪 OZON AI — Панель управления\n\nВыберите раздел:",
                        "reply_markup": reply_markup,
                    }).encode()
                    _telegram_api_json(
                        opener, f"{base_url}/sendMessage",
                        data=data, timeout=config.request_timeout,
                        attempts=config.retry_attempts,
                        backoff_seconds=config.retry_backoff_seconds,
                        action="sendMessage",
                    )
                else:
                    from .telegram.bot import handle_message
                    reply = handle_message(text, user=user)
                    console.print(f"[cyan]Telegram handled command: {escape(command)}[/]")
                    _telegram_send_message(opener, base_url, chat_id, reply, config)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            console.print(
                "[yellow]Telegram polling warning after retries: "
                f"{escape(type(exc).__name__)}[/]"
            )
            time.sleep(max(config.retry_backoff_seconds, 10))


@main.group("reconcile")
def reconcile_group() -> None:
    """Reconcile agent analytics against external financial truth sources."""


@reconcile_group.command("legacy-finance")
@click.option("--legacy-id", required=True, help="Read-only legacy Google spreadsheet ID")
@click.option("--month", required=True, help="Month to reconcile, YYYY-MM")
def reconcile_legacy_finance_cmd(legacy_id: str, month: str) -> None:
    """Compare legacy workbook Daily Input financials with Python unit economics."""
    from .reconciliation.legacy_finance import COMPARE_METRICS, reconcile_legacy_finance

    result = reconcile_legacy_finance(legacy_id=legacy_id, month=month)
    table = Table(title=f"Legacy Finance Reconciliation {month}")
    table.add_column("Metric")
    table.add_column("Legacy", justify="right")
    table.add_column("New", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("Diff %", justify="right")
    table.add_column("Status")
    for row in result.rows:
        color = "green" if row.status == "OK" else "red"
        table.add_row(
            row.metric,
            f"{row.legacy:.2f}",
            f"{row.new:.2f}",
            f"{row.diff:.2f}",
            f"{row.diff_pct:.2f}%",
            f"[{color}]{row.status}[/]",
        )
    console.print(table)
    console.print(f"New period: {result.new_period}")
    console.print(f"Saved: data/reconciliation/legacy_vs_new_{month}.json")
    if not result.pass_threshold:
        failed = ", ".join(
            row.metric for row in result.rows
            if row.metric in COMPARE_METRICS and row.status != "OK"
        )
        raise click.ClickException(
            f"Financial reconciliation failed threshold for: {failed}"
        )


@main.group("ranking")
def ranking() -> None:
    """Ranking Intelligence Engine commands."""


@ranking.command("collect")
def ranking_collect_cmd() -> None:
    """Collect ranking snapshots from local data."""
    from .ranking.cli import ranking_collect

    ranking_collect()


@ranking.command("analyze")
def ranking_analyze_cmd() -> None:
    """Analyze ranking factor correlations."""
    from .ranking.cli import ranking_analyze

    ranking_analyze()


@ranking.command("explain")
@click.argument("sku")
@click.option("--date-from", default=None, help="Date from, YYYY-MM-DD")
@click.option("--date-to", default=None, help="Date to, YYYY-MM-DD")
def ranking_explain_cmd(sku: str, date_from: str | None, date_to: str | None) -> None:
    """Explain position change for SKU."""
    from .ranking.cli import ranking_explain

    ranking_explain(sku, date_from=date_from, date_to=date_to)


@ranking.command("top-factors")
@click.argument("sku")
@click.option("--limit", default=5, help="Number of factors to show")
def ranking_top_factors_cmd(sku: str, limit: int) -> None:
    """Show top ranking factors for SKU."""
    from .ranking.cli import ranking_top_factors

    ranking_top_factors(sku, limit=limit)


if __name__ == "__main__":
    main()
