"""Data collectors for audit report."""

import os
import subprocess
from typing import Any


def _run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def get_git_status() -> str:
    try:
        result = _run_command(["git", "status", "--short"], timeout=10)
        return result.stdout.strip() or "clean"
    except Exception:
        return "unknown"


def get_changed_files() -> list[str]:
    try:
        result = _run_command(["git", "diff", "--name-only", "HEAD~1"], timeout=10)
        if result.returncode != 0:
            result = _run_command(["git", "diff", "--name-only"], timeout=10)
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [f for f in files if f]
    except Exception:
        return []


def get_test_results() -> dict[str, Any]:
    results: dict[str, Any] = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "lint_status": "unknown",
        "type_status": "unknown",
    }

    if "PYTEST_CURRENT_TEST" not in os.environ:
        try:
            result = _run_command(
                ["python", "-m", "pytest", "tests/", "-q", "--tb=no"], timeout=120
            )
            output = result.stdout
            for line in output.split("\n"):
                if "passed" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "passed" in p:
                            results["passed"] = int(parts[i - 1])
                            results["total"] = results["passed"]
                if "failed" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "failed" in p:
                            results["failed"] = int(parts[i - 1])
                            results["total"] = results["passed"] + results["failed"]
        except Exception:
            pass

    try:
        result = _run_command(["python", "-m", "ruff", "check", "src/", "tests/", "-q"], timeout=60)
        results["lint_status"] = "pass" if result.returncode == 0 else "fail"
    except Exception:
        pass

    try:
        result = _run_command(["python", "-m", "mypy", "src/"], timeout=60)
        results["type_status"] = "pass" if result.returncode == 0 else "fail"
    except Exception:
        pass

    return results


ROADMAP: dict[str, Any] = {
    "phases": [
        {"id": 1, "name": "Data Warehouse", "status": "done"},
        {"id": 2, "name": "Analytics & Diagnostics", "status": "done"},
        {"id": 3, "name": "Forecasting", "status": "done"},
        {"id": 4, "name": "Decision Engine", "status": "done"},
        {"id": 4.5, "name": "Approval Workflow", "status": "done"},
        {"id": 4.6, "name": "Outcome Learning", "status": "done"},
        {"id": 5, "name": "Autonomous Experiments", "status": "done"},
    ],
    "next_after_forecasting": "Decision Engine",
    "decision_engine_scope": [
        "Generate actionable recommendations",
        "Increase/decrease budget, pause campaigns",
        "Restock recommendations",
        "Approval workflow (no auto-mutations)",
    ],
}


def get_roadmap_alignment() -> dict[str, Any]:
    completed = [p["name"] for p in ROADMAP["phases"] if p["status"] == "done"]
    remaining = [p["name"] for p in ROADMAP["phases"] if p["status"] != "done"]
    current = completed[-1] if completed else "None"

    return {
        "current_phase": current,
        "completed": completed,
        "remaining": remaining,
    }


def detect_architecture_risks() -> list[str]:
    risks = []

    try:
        import importlib

        for mod in ["psycopg", "pandas", "xgboost", "lightgbm", "prophet"]:
            try:
                importlib.import_module(mod)
            except ImportError:
                risks.append(f"Missing dependency: {mod}")
    except Exception:
        pass

    try:
        result = _run_command(
            ["python", "-c", "from ozon_agent.db.connection import get_pool"], timeout=10
        )
        if result.returncode != 0 and "DATABASE_URL" in result.stderr:
            risks.append("DATABASE_URL not configured — DB features will fail")
    except Exception:
        pass

    risks.extend(check_decision_engine_safety())
    risks.extend(check_approval_safety())
    risks.extend(check_migration_exists())

    return risks


FORBIDDEN_KEYWORDS = [
    "update_price",
    "change_price",
    "create_campaign",
    "update_bid",
    "pause_campaign_api",
    "create_supply",
    "external_post",
    "requests.post",
    "httpx.post",
]


def check_decision_engine_safety() -> list[str]:
    import os

    risks: list[str] = []
    decision_dir = os.path.join(os.path.dirname(__file__), "..", "decision")
    if not os.path.isdir(decision_dir):
        return risks

    for filename in os.listdir(decision_dir):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(decision_dir, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in content:
                risks.append(
                    f"Decision engine contains forbidden keyword '{keyword}' in {filename}"
                )

    return risks


def recommend_next_task(completed_phases: list[str]) -> str:
    if "Outcome Learning" in completed_phases and "Autonomous Experiments" in completed_phases:
        return (
            "Phase 5.1: Experiment result automation — "
            "Auto-evaluate experiments on completion, guarded auto-approval for low-risk."
        )
    if "Approval Workflow" in completed_phases and "Autonomous Experiments" not in completed_phases:
        return (
            "Phase 5: Autonomous Experiments — "
            "Build A/B testing framework and automated experiment tracking."
        )
    if "Decision Engine" in completed_phases:
        return (
            "Phase 4.5: Approval Workflow — "
            "Complete outcome tracking and notification system. "
            "Current: approval workflow implemented, safety checks active."
        )
    if "Forecasting" in completed_phases:
        return (
            "Phase 4: Decision Engine — "
            "Complete approval workflow and notification system. "
            "Current: recommendations core implemented, safety checks active."
        )
    if "Analytics & Diagnostics" in completed_phases:
        return "Phase 3: Forecasting — Build prediction models."
    if "Data Warehouse" in completed_phases:
        return "Phase 2: Analytics & Diagnostics — Add factor analysis."
    return "Phase 1: Data Warehouse — Set up PostgreSQL schema and ETL."


FORBIDDEN_KEYWORDS_EXTENDED = FORBIDDEN_KEYWORDS + [
    "execute_ozon_action",
]


def check_approval_safety() -> list[str]:
    import os

    risks: list[str] = []
    for module_name in ("approval", "telegram", "learning", "experiments", "sheets"):
        module_dir = os.path.join(os.path.dirname(__file__), "..", module_name)
        if not os.path.isdir(module_dir):
            continue
        for filename in os.listdir(module_dir):
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(module_dir, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            for keyword in FORBIDDEN_KEYWORDS_EXTENDED:
                if keyword in content:
                    risks.append(
                        f"{module_name} module contains forbidden keyword '{keyword}' in {filename}"
                    )
    return risks


def check_migration_exists() -> list[str]:
    import os

    risks: list[str] = []
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations")
    if not os.path.isdir(migrations_dir):
        risks.append("migrations/ directory not found")
        return risks
    has_approval_migration = False
    has_experiments_migration = False
    for filename in os.listdir(migrations_dir):
        if "approval" in filename.lower() or "recommendation" in filename.lower():
            has_approval_migration = True
        if "experiment" in filename.lower():
            has_experiments_migration = True
    if not has_approval_migration:
        risks.append("No approval/recommendation migration found in migrations/")
    if not has_experiments_migration:
        risks.append("No experiments migration found in migrations/ (003_experiments.sql)")
    return risks
