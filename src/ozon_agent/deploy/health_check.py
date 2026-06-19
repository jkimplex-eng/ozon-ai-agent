"""Post-deployment health checks."""
from __future__ import annotations

import logging
from typing import Any

from .vps_deployer import run_ssh_command

logger = logging.getLogger(__name__)


def check_git_revision(target: str, expected_rev: str | None = None) -> dict[str, Any]:
    """Check git revision on VPS."""
    result = run_ssh_command(
        target,
        "cd /root/ozon-ai-agent && git rev-parse --short HEAD",
        timeout=15,
    )
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    remote_rev = result["stdout"].strip()
    match = expected_rev is None or remote_rev == expected_rev
    return {
        "healthy": match,
        "remote_revision": remote_rev,
        "expected_revision": expected_rev,
    }


def check_python_import(target: str) -> dict[str, Any]:
    """Check Python import works."""
    result = run_ssh_command(
        target,
        "cd /root/ozon-ai-agent && source .venv/bin/activate "
        "&& python -c 'import ozon_agent; print(ozon_agent.__version__)'",
        timeout=15,
    )
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}
    return {"healthy": True, "version": result["stdout"].strip()}


def check_cli_available(target: str) -> dict[str, Any]:
    """Check CLI is available."""
    result = run_ssh_command(
        target,
        "cd /root/ozon-ai-agent && source .venv/bin/activate "
        "&& python -m ozon_agent.cli --help >/dev/null 2>&1 && echo OK",
        timeout=15,
    )
    return {"healthy": result["success"] and "OK" in result["stdout"]}


def check_dependencies(target: str) -> dict[str, Any]:
    """Check key Python dependencies are installed."""
    deps = ["gspread", "gspread_formatting", "apscheduler", "pandas", "psycopg"]
    missing = []
    for dep in deps:
        result = run_ssh_command(
            target,
            "cd /root/ozon-ai-agent && source .venv/bin/activate "
            f"&& python -c 'import {dep}' 2>/dev/null",
            timeout=10,
        )
        if not result["success"]:
            missing.append(dep)

    return {
        "healthy": len(missing) == 0,
        "missing": missing,
        "checked": deps,
    }


def check_env_vars(target: str) -> dict[str, Any]:
    """Check critical environment variables are set."""
    vars_to_check = [
        "DATABASE_URL",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
    ]
    missing = []
    for var in vars_to_check:
        result = run_ssh_command(
            target,
            "cd /root/ozon-ai-agent && set -a && [ -f .env ] && . ./.env; "
            f"set +a; test -n \"${{{var}:-}}\" && echo OK || echo MISSING",
            timeout=10,
        )
        if "MISSING" in result["stdout"] or not result["success"]:
            missing.append(var)

    # Check service account file
    result = run_ssh_command(
        target,
        "test -f /root/ozon-ai-agent/secrets/"
        "google-service-account.json && echo OK || echo MISSING",
        timeout=10,
    )
    if "MISSING" in result["stdout"]:
        missing.append("GOOGLE_SERVICE_ACCOUNT_JSON (file)")

    return {
        "healthy": len(missing) == 0,
        "missing": missing,
    }


def check_sheets_sync_dry_run(target: str) -> dict[str, Any]:
    """Run sheets sync dry run."""
    cmd = (
        "cd /root/ozon-ai-agent && "
        "SHEETS_DATA_SOURCE=files "
        "python -m ozon_agent.cli sheets sync --source files --delay 5 2>&1 | tail -15"
    )
    result = run_ssh_command(target, cmd, timeout=120)
    output = result["stdout"]
    has_failed = "FAILED" in output
    return {
        "healthy": result["success"] and not has_failed,
        "output": output,
    }


def check_supervisor_status(target: str) -> dict[str, Any]:
    """Check supervisor-managed Ozon services."""
    result = run_ssh_command(target, "supervisorctl status ozon-sheets-watch", timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    output = result["stdout"].strip()
    return {
        "healthy": "RUNNING" in output,
        "services": {"ozon-sheets-watch": output},
    }


def check_sheets_watch_interval(target: str) -> dict[str, Any]:
    """Verify sheets watcher is configured for a 30-minute interval."""
    cmd = "grep -q 'sheets watch --interval 30' /etc/supervisor/conf.d/ozon-sheets-watch.conf"
    result = run_ssh_command(target, cmd, timeout=10)
    return {"healthy": result["success"]}


def check_http_health(target: str, url: str = "http://localhost:3000/health") -> dict[str, Any]:
    """Check HTTP health endpoint."""
    result = run_ssh_command(target, f"curl -s -o /dev/null -w '%{{http_code}}' {url}", timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    status_code = result["stdout"].strip().strip("'")
    return {
        "healthy": status_code == "200",
        "status_code": status_code,
    }


def check_logs_errors(target: str, lines: int = 20) -> dict[str, Any]:
    """Check recent logs for errors."""
    cmd = f"tail -{lines} /root/ozon-ai-agent/logs/ozon-sheets-watch.log 2>&1"
    result = run_ssh_command(target, cmd, timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    output = result["stdout"].lower()
    error_indicators = ["error", "fatal", "panic", "exception", "traceback"]
    found_errors = [ind for ind in error_indicators if ind in output]

    return {
        "healthy": len(found_errors) == 0,
        "errors_found": found_errors,
        "log_lines": lines,
    }


def run_full_health_check(target: str) -> dict[str, Any]:
    """Run all health checks and return combined result."""
    checks: dict[str, dict[str, Any]] = {
        "git_revision": check_git_revision(target),
        "python_import": check_python_import(target),
        "cli_available": check_cli_available(target),
        "dependencies": check_dependencies(target),
        "env_vars": check_env_vars(target),
        "sheets_sync": check_sheets_sync_dry_run(target),
        "supervisor": check_supervisor_status(target),
        "sheets_watch_interval": check_sheets_watch_interval(target),
        "logs": check_logs_errors(target),
    }

    all_healthy = all(check["healthy"] for check in checks.values())

    return {
        "healthy": all_healthy,
        "checks": checks,
    }


def format_health_report(result: dict[str, Any]) -> str:
    """Format health check result as readable text."""
    lines = ["=" * 50, "VPS HEALTH CHECK", "=" * 50, ""]

    for name, check in result["checks"].items():
        status = "✓" if check["healthy"] else "✗"
        lines.append(f"  {status} {name}")
        if not check["healthy"]:
            error = check.get("error", check.get("missing", ""))
            if error:
                lines.append(f"    {error}")

    lines.append("")
    if result["healthy"]:
        lines.append("[bold green]All checks passed.[/]")
    else:
        lines.append("[bold red]Some checks failed.[/]")

    return "\n".join(lines)
