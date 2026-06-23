"""Recommendation Execution Tracking — detects if owner acted on recommendations."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRACKING_DIR = Path("data/recommendation_tracking")


class RecommendationStatus:
    NEW = "NEW"
    OBSERVED = "OBSERVED"
    EXECUTED = "EXECUTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ExecutionSignal:
    signal_type: str
    field: str
    before: Any
    after: Any
    detected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationTracking:
    recommendation_id: str
    sku: str
    action: str
    created_at: str
    status: str
    signals: list[ExecutionSignal]
    observed_at: str | None = None
    executed_at: str | None = None
    result: str | None = None
    result_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "sku": self.sku,
            "action": self.action,
            "created_at": self.created_at,
            "status": self.status,
            "signals": [s.to_dict() for s in self.signals],
            "observed_at": self.observed_at,
            "executed_at": self.executed_at,
            "result": self.result,
            "result_at": self.result_at,
        }


def _load_tracking_data() -> list[dict[str, Any]]:
    """Load tracking records."""
    if not TRACKING_DIR.exists():
        return []
    records = []
    for f in sorted(TRACKING_DIR.glob("*.json")):
        try:
            records.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return records


def _save_tracking_record(record: RecommendationTracking) -> Path:
    """Save tracking record."""
    TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACKING_DIR / f"{record.recommendation_id}.json"
    path.write_text(
        json.dumps(record.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return path


def detect_execution_signals(
    rec_id: str,
    sku: str,
    before_metrics: dict[str, Any],
    after_metrics: dict[str, Any],
) -> list[ExecutionSignal]:
    """Detect if metrics changed after a recommendation."""
    signals: list[ExecutionSignal] = []
    now = datetime.now(UTC).isoformat()

    signal_fields = {
        "advertising": "Ad spend changed",
        "stock_days": "Inventory changed",
        "price": "Price changed",
        "review_count": "Reviews changed",
        "review_rating": "Rating changed",
    }

    for field_name, signal_type in signal_fields.items():
        before_val = before_metrics.get(field_name)
        after_val = after_metrics.get(field_name)
        if before_val is not None and after_val is not None:
            if before_val != after_val:
                signals.append(ExecutionSignal(
                    signal_type=signal_type,
                    field=field_name,
                    before=before_val,
                    after=after_val,
                    detected_at=now,
                ))

    return signals


def transition_status(
    tracking: RecommendationTracking,
    new_status: str,
) -> RecommendationTracking:
    """Transition recommendation status."""
    now = datetime.now(UTC).isoformat()

    updated_fields: dict[str, Any] = {
        "status": new_status,
    }

    if new_status == RecommendationStatus.OBSERVED:
        updated_fields["observed_at"] = now
    elif new_status == RecommendationStatus.EXECUTED:
        updated_fields["executed_at"] = now
    elif new_status in (RecommendationStatus.SUCCESS, RecommendationStatus.FAILURE):
        updated_fields["result"] = new_status
        updated_fields["result_at"] = now

    return RecommendationTracking(
        recommendation_id=tracking.recommendation_id,
        sku=tracking.sku,
        action=tracking.action,
        created_at=tracking.created_at,
        status=new_status,
        signals=tracking.signals,
        observed_at=updated_fields.get("observed_at", tracking.observed_at),
        executed_at=updated_fields.get("executed_at", tracking.executed_at),
        result=updated_fields.get("result", tracking.result),
        result_at=updated_fields.get("result_at", tracking.result_at),
    )


def create_tracking(
    recommendation_id: str,
    sku: str,
    action: str,
) -> RecommendationTracking:
    """Create new tracking record."""
    now = datetime.now(UTC).isoformat()
    tracking = RecommendationTracking(
        recommendation_id=recommendation_id,
        sku=sku,
        action=action,
        created_at=now,
        status=RecommendationStatus.NEW,
        signals=[],
    )
    _save_tracking_record(tracking)
    return tracking


def get_tracking_stats() -> dict[str, Any]:
    """Get tracking statistics."""
    records = _load_tracking_data()
    if not records:
        return {"total": 0, "by_status": {}}

    by_status: dict[str, int] = {}
    for r in records:
        status = r.get("status", "UNKNOWN")
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total": len(records),
        "by_status": by_status,
    }


def format_tracking_stats(stats: dict[str, Any]) -> str:
    """Format tracking stats for display."""
    lines = [
        "RECOMMENDATION TRACKING",
        "=" * 40,
        f"Total: {stats['total']}",
        "",
        "By Status:",
    ]
    for status, count in stats.get("by_status", {}).items():
        lines.append(f"  {status}: {count}")
    return "\n".join(lines)
