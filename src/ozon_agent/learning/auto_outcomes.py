"""Auto Outcome Engine — automatically evaluates recommendation success without manual input."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ozon_agent.learning.models import (
    ExperimentMetric,
    ExperimentOutcome,
    ExperimentResult,
    utc_now_iso,
)
from ozon_agent.learning.outcome_tracker import (
    calculate_delta,
    record_outcome,
)

logger = logging.getLogger(__name__)

SUCCESS_THRESHOLDS = {
    "revenue_delta_min_pct": -5.0,
    "profit_delta_min_pct": 5.0,
    "drr_delta_max_pct": 20.0,
    "orders_delta_min_pct": -10.0,
}

WINDOWS = [7, 14, 30]


@dataclass(frozen=True)
class RecommendationSnapshot:
    recommendation_id: str
    sku: str
    action: str
    created_at: str
    metrics_before: dict[str, float]
    window_days: int = 14


@dataclass(frozen=True)
class AutoOutcomeResult:
    recommendation_id: str
    sku: str
    action: str
    result: str
    success_score: float
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    deltas: dict[str, float | None]
    evaluated_at: str
    window_days: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactRecord:
    recommendation_id: str
    sku: str
    action: str
    revenue_before: float
    revenue_after: float
    profit_before: float
    profit_after: float
    orders_before: float
    orders_after: float
    drr_before: float
    drr_after: float
    revenue_delta_pct: float | None
    profit_delta_pct: float | None
    orders_delta_pct: float | None
    drr_delta_pct: float | None
    window_days: int
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SUCCESS_DB_PATH = Path("data/recommendation_outcomes")
IMPACT_DB_PATH = Path("data/recommendation_impact")


def _load_metrics_snapshot(metrics: dict[str, float]) -> list[ExperimentMetric]:
    """Convert flat metrics dict to ExperimentMetric list."""
    result = []
    for name, value in metrics.items():
        higher_is_better = name.lower() not in {"drr", "position", "stockout_probability"}
        result.append(ExperimentMetric(
            name=name,
            baseline=None,
            actual=value,
            expected_delta_pct=None,
            actual_delta_pct=None,
            weight=1.0,
            higher_is_better=higher_is_better,
        ))
    return result


def _calculate_deltas(
    before: dict[str, float],
    after: dict[str, float],
) -> dict[str, float | None]:
    """Calculate percentage deltas between before and after metrics."""
    deltas: dict[str, float | None] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        b = before.get(key)
        a = after.get(key)
        if b is not None and a is not None:
            deltas[key] = calculate_delta(b, a)
        else:
            deltas[key] = None
    return deltas


def _evaluate_auto_outcome(
    deltas: dict[str, float | None],
) -> tuple[ExperimentResult, float]:
    """Evaluate outcome based on deltas."""
    profit_delta = deltas.get("profit")
    revenue_delta = deltas.get("revenue")
    drr_delta = deltas.get("drr")
    orders_delta = deltas.get("orders")

    if profit_delta is not None and profit_delta < SUCCESS_THRESHOLDS["profit_delta_min_pct"] * -1:
        return ExperimentResult.FAILURE, 0.0

    if orders_delta is not None and orders_delta < SUCCESS_THRESHOLDS["orders_delta_min_pct"]:
        return ExperimentResult.FAILURE, 0.2

    scores = []
    if profit_delta is not None:
        scores.append(min(1.0, max(0.0, profit_delta / 20.0)))
    if revenue_delta is not None:
        scores.append(min(1.0, max(0.0, (revenue_delta + 10) / 30.0)))
    if drr_delta is not None:
        scores.append(min(1.0, max(0.0, (20 - drr_delta) / 40.0)))
    if orders_delta is not None:
        scores.append(min(1.0, max(0.0, (orders_delta + 10) / 30.0)))

    if not scores:
        return ExperimentResult.UNKNOWN, 0.0

    avg_score = sum(scores) / len(scores)

    if avg_score >= 0.7:
        return ExperimentResult.SUCCESS, avg_score
    if avg_score >= 0.4:
        return ExperimentResult.PARTIAL_SUCCESS, avg_score
    return ExperimentResult.FAILURE, avg_score


def evaluate_recommendation(
    snapshot: RecommendationSnapshot,
    metrics_after: dict[str, float],
) -> AutoOutcomeResult:
    """Evaluate a recommendation's outcome automatically."""
    deltas = _calculate_deltas(snapshot.metrics_before, metrics_after)
    result, score = _evaluate_auto_outcome(deltas)

    return AutoOutcomeResult(
        recommendation_id=snapshot.recommendation_id,
        sku=snapshot.sku,
        action=snapshot.action,
        result=result.value,
        success_score=score,
        metrics_before=snapshot.metrics_before,
        metrics_after=metrics_after,
        deltas=deltas,
        evaluated_at=utc_now_iso(),
        window_days=snapshot.window_days,
    )


def record_auto_outcome(
    result: AutoOutcomeResult,
    root: str | Path | None = None,
) -> ExperimentOutcome:
    """Record auto-evaluated outcome to the learning system."""
    metrics = []
    for name, after_val in result.metrics_after.items():
        before_val = result.metrics_before.get(name)
        delta = result.deltas.get(name)
        higher_is_better = name.lower() not in {"drr", "position"}
        metrics.append(ExperimentMetric(
            name=name,
            baseline=before_val,
            actual=after_val,
            expected_delta_pct=None,
            actual_delta_pct=delta,
            weight=1.0,
            higher_is_better=higher_is_better,
        ))

    outcome = record_outcome(
        experiment_id=result.recommendation_id,
        metrics=metrics,
        notes=f"Auto-evaluated after {result.window_days}d window. Result: {result.result}",
        root=root,
    )
    return outcome


def save_impact_record(
    snapshot: RecommendationSnapshot,
    metrics_after: dict[str, float],
    root: str | Path | None = None,
) -> ImpactRecord:
    """Save detailed impact record for a recommendation."""
    path = Path(root) if root else IMPACT_DB_PATH
    path.mkdir(parents=True, exist_ok=True)

    deltas = _calculate_deltas(snapshot.metrics_before, metrics_after)

    record = ImpactRecord(
        recommendation_id=snapshot.recommendation_id,
        sku=snapshot.sku,
        action=snapshot.action,
        revenue_before=snapshot.metrics_before.get("revenue", 0),
        revenue_after=metrics_after.get("revenue", 0),
        profit_before=snapshot.metrics_before.get("profit", 0),
        profit_after=metrics_after.get("profit", 0),
        orders_before=snapshot.metrics_before.get("orders", 0),
        orders_after=metrics_after.get("orders", 0),
        drr_before=snapshot.metrics_before.get("drr", 0),
        drr_after=metrics_after.get("drr", 0),
        revenue_delta_pct=deltas.get("revenue"),
        profit_delta_pct=deltas.get("profit"),
        orders_delta_pct=deltas.get("orders"),
        drr_delta_pct=deltas.get("drr"),
        window_days=snapshot.window_days,
        recorded_at=utc_now_iso(),
    )

    file_path = path / f"{record.recommendation_id}.json"
    file_path.write_text(
        json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Impact record saved: %s", file_path)
    return record


def load_impact_records(
    root: str | Path | None = None,
) -> list[ImpactRecord]:
    """Load all impact records."""
    path = Path(root) if root else IMPACT_DB_PATH
    if not path.exists():
        return []

    records = []
    for file_path in sorted(path.glob("*.json")):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            records.append(ImpactRecord(**data))
        except Exception as e:
            logger.warning("Failed to load impact record %s: %s", file_path, e)

    return records
