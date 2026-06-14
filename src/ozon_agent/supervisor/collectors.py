"""Data collectors for audit report."""
import subprocess
from typing import Any


def get_git_status() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "clean"
    except Exception:
        return "unknown"


def get_changed_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True, text=True, timeout=10,
            )
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [f for f in files if f]
    except Exception:
        return []


def get_test_results() -> dict[str, Any]:
    results: dict[str, Any] = {
        "total": 0, "passed": 0, "failed": 0,
        "lint_status": "unknown", "type_status": "unknown",
    }

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True, text=True, timeout=120,
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
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "src/", "tests/", "-q"],
            capture_output=True, text=True, timeout=60,
        )
        results["lint_status"] = "pass" if result.returncode == 0 else "fail"
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["python", "-m", "mypy", "src/"],
            capture_output=True, text=True, timeout=60,
        )
        results["type_status"] = "pass" if result.returncode == 0 else "fail"
    except Exception:
        pass

    return results


ROADMAP = {
    "phases": [
        {"id": 1, "name": "Data Warehouse", "status": "done"},
        {"id": 2, "name": "Analytics & Diagnostics", "status": "done"},
        {"id": 3, "name": "Forecasting", "status": "done"},
        {"id": 4, "name": "Decision Engine", "status": "pending"},
        {"id": 5, "name": "Autonomous Experiments", "status": "pending"},
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
        result = subprocess.run(
            ["python", "-c", "from ozon_agent.db.connection import get_pool"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0 and "DATABASE_URL" in result.stderr:
            risks.append("DATABASE_URL not configured — DB features will fail")
    except Exception:
        pass

    return risks


def recommend_next_task(completed_phases: list[str]) -> str:
    if "Forecasting" in completed_phases:
        return (
            "Phase 4: Decision Engine — "
            "Build recommendation engine that generates actionable decisions "
            "(increase/decrease budget, pause campaigns, restock) "
            "with confidence scores and approval workflow."
        )
    if "Analytics & Diagnostics" in completed_phases:
        return "Phase 3: Forecasting — Build prediction models."
    if "Data Warehouse" in completed_phases:
        return "Phase 2: Analytics & Diagnostics — Add factor analysis."
    return "Phase 1: Data Warehouse — Set up PostgreSQL schema and ETL."
