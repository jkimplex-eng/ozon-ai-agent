"""Ozon AI Agent CLI."""
import logging
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from .api.ozon_client import create_client
from .etl.sync import sync_all, sync_finance, sync_orders, sync_products

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


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


if __name__ == "__main__":
    main()
