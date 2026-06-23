"""System Audit — verifies all components are implemented, wired, and running."""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    status: str
    details: str = ""
    critical: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemAudit:
    timestamp: str
    overall_status: str
    components: list[ComponentStatus]
    summary: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "components": [c.to_dict() for c in self.components],
            "summary": self.summary,
        }


def _check_workbook() -> ComponentStatus:
    from ozon_agent.sheets.client import get_spreadsheet_id
    try:
        sid = get_spreadsheet_id()
        if sid:
            return ComponentStatus(name="Workbook", status="OK", details=f"ID: {sid}")
        return ComponentStatus(
            name="Workbook", status="MISSING",
            details="GOOGLE_SHEETS_SPREADSHEET_ID not set", critical=True,
        )
    except Exception as e:
        return ComponentStatus(name="Workbook", status="ERROR", details=str(e), critical=True)


def _check_tabs() -> ComponentStatus:
    required = ["Daily Input", "Unit Economics", "COGS", "Daily Summary"]
    try:
        from ozon_agent.sheets.client import get_gspread_client, open_spreadsheet
        client = get_gspread_client()
        spreadsheet = open_spreadsheet(client)
        existing = {ws.title for ws in spreadsheet.worksheets()}
        missing = [t for t in required if t not in existing]
        if missing:
            return ComponentStatus(
                name="Tabs", status="PARTIAL",
                details=f"Missing: {', '.join(missing)}",
            )
        return ComponentStatus(name="Tabs", status="OK", details=f"{len(existing)} tabs")
    except Exception as e:
        return ComponentStatus(name="Tabs", status="SKIPPED", details=str(e), critical=False)


def _check_sync() -> ComponentStatus:
    from ozon_agent.sheets.sync import get_sync_status
    status = get_sync_status()
    if not status:
        return ComponentStatus(
            name="Sheets Sync", status="NO_DATA",
            details="No sync history", critical=False,
        )
    latest = max(status.values())
    return ComponentStatus(name="Sheets Sync", status="OK", details=f"Last: {latest}")


def _check_supervisor() -> ComponentStatus:
    try:
        result = subprocess.run(
            ["supervisorctl", "status"],
            capture_output=True, text=True, timeout=10,
        )
        running = [line for line in result.stdout.splitlines() if "RUNNING" in line]
        return ComponentStatus(
            name="Supervisor", status="OK",
            details=f"{len(running)} services running",
        )
    except FileNotFoundError:
        return ComponentStatus(
            name="Supervisor", status="SKIPPED",
            details="not found", critical=False,
        )
    except Exception as e:
        return ComponentStatus(name="Supervisor", status="ERROR", details=str(e))


def _check_pm2() -> ComponentStatus:
    try:
        result = subprocess.run(
            ["pm2", "status"], capture_output=True, text=True, timeout=10,
        )
        if "online" in result.stdout.lower():
            return ComponentStatus(name="PM2", status="OK", details="ollama-bot online")
        return ComponentStatus(name="PM2", status="ERROR", details=result.stdout[:200])
    except FileNotFoundError:
        return ComponentStatus(name="PM2", status="SKIPPED", details="not found", critical=False)
    except Exception as e:
        return ComponentStatus(name="PM2", status="ERROR", details=str(e))


def _check_fastapi() -> ComponentStatus:
    try:
        import httpx
        r = httpx.get("http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            return ComponentStatus(name="FastAPI", status="OK", details="Health OK")
        return ComponentStatus(name="FastAPI", status="ERROR", details=f"HTTP {r.status_code}")
    except Exception:
        return ComponentStatus(
            name="FastAPI", status="NOT_RUNNING",
            details="Not reachable", critical=False,
        )


def _check_recommendations() -> ComponentStatus:
    d = DATA_DIR / "recommendations"
    if d.exists():
        n = len(list(d.glob("*.json")))
        return ComponentStatus(name="Recommendations", status="OK", details=f"{n} records")
    return ComponentStatus(
        name="Recommendations", status="EMPTY",
        details="No data", critical=False,
    )


def _check_outcomes() -> ComponentStatus:
    d = DATA_DIR / "outcomes"
    if d.exists():
        n = len(list(d.glob("*.json")))
        return ComponentStatus(name="Outcomes", status="OK", details=f"{n} records")
    return ComponentStatus(name="Outcomes", status="EMPTY", details="No data", critical=False)


def _check_success_db() -> ComponentStatus:
    d = DATA_DIR / "recommendation_success"
    if d.exists():
        n = len(list(d.glob("*.json")))
        return ComponentStatus(name="Success DB", status="OK", details=f"{n} records")
    return ComponentStatus(name="Success DB", status="EMPTY", details="No data", critical=False)


def run_system_audit() -> SystemAudit:
    timestamp = datetime.now(UTC).isoformat()
    checks = [
        _check_workbook, _check_tabs, _check_sync,
        _check_supervisor, _check_pm2, _check_fastapi,
        _check_recommendations, _check_outcomes, _check_success_db,
    ]
    components = [c() for c in checks]

    critical_fails = [c for c in components if c.critical and c.status in ("ERROR", "MISSING")]
    if critical_fails:
        overall = "CRITICAL"
    elif any(c.status == "ERROR" for c in components):
        overall = "WARNING"
    elif any(c.status in ("EMPTY", "NO_DATA", "PARTIAL") for c in components):
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    return SystemAudit(
        timestamp=timestamp,
        overall_status=overall,
        components=components,
        summary={c.name: c.status for c in components},
    )


def save_audit_report(audit: SystemAudit) -> Path:
    path = DATA_DIR / "system_audit"
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "audit_report.json"
    report_path.write_text(
        json.dumps(audit.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return report_path


def format_audit(audit: SystemAudit) -> str:
    lines = [
        "SYSTEM STATUS", "=" * 50,
        f"Timestamp: {audit.timestamp}",
        f"Overall: {audit.overall_status}", "",
    ]
    symbols = {
        "OK": "[OK]", "MISSING": "[!!]", "ERROR": "[XX]",
        "EMPTY": "[--]", "NO_DATA": "[--]", "PARTIAL": "[~~]",
        "SKIPPED": "[sk]", "NOT_RUNNING": "[--]",
    }
    for comp in audit.components:
        sym = symbols.get(comp.status, "[??]")
        lines.append(f"  {sym} {comp.name}: {comp.status}")
        if comp.details:
            lines.append(f"      {comp.details}")
    return "\n".join(lines)
