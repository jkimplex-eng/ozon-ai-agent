"""Outcome tracking for recommendation results."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_OUTCOMES_DIR = Path("data") / "outcomes"
_OUTCOMES_FILE = _OUTCOMES_DIR / "outcomes.json"


def _ensure_dir() -> None:
    _OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)


def _load_outcomes() -> list[dict[str, Any]]:
    if not _OUTCOMES_FILE.exists():
        return []
    try:
        data = json.loads(_OUTCOMES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _save_outcomes(outcomes: list[dict[str, Any]]) -> None:
    _ensure_dir()
    _OUTCOMES_FILE.write_text(json.dumps(outcomes, ensure_ascii=False, indent=2), encoding="utf-8")


def record_outcome(
    recommendation_id: str,
    sku: str,
    action: str,
    result: str,
    user: str,
) -> dict[str, Any]:
    outcomes = _load_outcomes()
    entry: dict[str, Any] = {
        "id": str(uuid4()),
        "recommendation_id": recommendation_id,
        "sku": sku,
        "action": action,
        "result": result,
        "user": user,
        "created_at": datetime.now(UTC).isoformat(),
    }
    outcomes.append(entry)
    _save_outcomes(outcomes)
    return entry


def list_outcomes(limit: int = 50) -> list[dict[str, Any]]:
    outcomes = _load_outcomes()
    return outcomes[-limit:]


def get_outcome_stats() -> dict[str, int]:
    outcomes = _load_outcomes()
    success = sum(1 for o in outcomes if o.get("result") == "SUCCESS")
    failure = sum(1 for o in outcomes if o.get("result") == "FAILURE")
    observing = sum(1 for o in outcomes if o.get("result") == "OBSERVING")
    pending = sum(1 for o in outcomes if o.get("result") == "PENDING")
    total = len(outcomes)
    decided = success + failure
    accuracy = round(success / decided * 100) if decided > 0 else 0
    return {
        "success": success,
        "failure": failure,
        "observing": observing,
        "pending": pending,
        "total": total,
        "accuracy": accuracy,
    }


def load_success_patterns() -> list[dict[str, Any]]:
    outcomes = _load_outcomes()
    by_action: dict[str, dict[str, int]] = {}
    for o in outcomes:
        action = o.get("action", "")
        if not action:
            continue
        if action not in by_action:
            by_action[action] = {"success": 0, "total": 0}
        by_action[action]["total"] += 1
        if o.get("result") == "SUCCESS":
            by_action[action]["success"] += 1

    patterns: list[dict[str, Any]] = []
    for action, counts in by_action.items():
        rate = counts["success"] / counts["total"] * 100 if counts["total"] > 0 else 0
        patterns.append({
            "problem": action,
            "success_rate": round(rate, 1),
            "total_cases": counts["total"],
        })
    return patterns
