from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.learning.models import (
    ExperimentMetric,
    ExperimentOutcome,
    ExperimentResult,
    new_learning_id,
    utc_now_iso,
)
from ozon_agent.learning.repository import read_json, to_jsonable, write_json

LOWER_IS_BETTER = {"drr", "position", "stockout_probability"}


def record_outcome(
    experiment_id: str,
    metrics: list[ExperimentMetric],
    notes: str = "",
    root: str | Path | None = None,
) -> ExperimentOutcome:
    result = evaluate_success(metrics)
    outcome = ExperimentOutcome(
        id=new_learning_id("outcome"),
        experiment_id=experiment_id,
        created_at=utc_now_iso(),
        metrics=metrics,
        result=result,
        success_score=_success_score(metrics),
        notes=notes,
    )
    write_json("outcomes", outcome.id, to_jsonable(outcome), root=root)
    return outcome


def update_outcome(
    outcome_id: str,
    root: str | Path | None = None,
    **fields: Any,
) -> ExperimentOutcome | None:
    payload = read_json("outcomes", outcome_id, root=root)
    if payload is None:
        return None
    payload.update({key: value for key, value in fields.items() if value is not None})
    outcome = _outcome_from_dict(payload)
    write_json("outcomes", outcome.id, to_jsonable(outcome), root=root)
    return outcome


def evaluate_success(metrics: list[ExperimentMetric]) -> ExperimentResult:
    comparable = [metric for metric in metrics if metric.expected_delta_pct is not None]
    if not comparable:
        return ExperimentResult.UNKNOWN

    orders = _metric_by_name(metrics, "orders")
    profit = _metric_by_name(metrics, "profit")
    if orders and orders.actual_delta_pct is not None and orders.actual_delta_pct < 0:
        return ExperimentResult.FAILURE
    if profit and profit.actual_delta_pct is not None and profit.actual_delta_pct < 0:
        positive = any(
            metric.actual_delta_pct is not None and metric.actual_delta_pct > 0
            for metric in metrics
            if metric.name.lower() != "profit"
        )
        return ExperimentResult.PARTIAL_SUCCESS if positive else ExperimentResult.FAILURE

    scores = [_metric_success_ratio(metric) for metric in comparable]
    average = sum(scores) / len(scores)
    if average >= 0.9:
        return ExperimentResult.SUCCESS
    if average >= 0.45:
        return ExperimentResult.PARTIAL_SUCCESS
    return ExperimentResult.FAILURE


def calculate_delta(baseline: float | None, actual: float | None) -> float | None:
    if baseline is None or actual is None or baseline == 0:
        return None
    return (actual - baseline) / abs(baseline) * 100.0


def _success_score(metrics: list[ExperimentMetric]) -> float:
    comparable = [metric for metric in metrics if metric.expected_delta_pct is not None]
    if not comparable:
        return 0.0
    average = sum(_metric_success_ratio(metric) for metric in comparable) / len(comparable)
    return max(0.0, min(1.0, average))


def _metric_success_ratio(metric: ExperimentMetric) -> float:
    if metric.expected_delta_pct is None or metric.actual_delta_pct is None:
        return 0.0
    expected = metric.expected_delta_pct
    actual = metric.actual_delta_pct
    if not metric.higher_is_better or metric.name.lower() in LOWER_IS_BETTER:
        expected = -expected
        actual = -actual
    if expected == 0:
        return 1.0 if actual >= 0 else 0.0
    if expected > 0 and actual <= 0:
        return 0.0
    return max(0.0, min(1.0, actual / expected))


def _metric_by_name(metrics: list[ExperimentMetric], name: str) -> ExperimentMetric | None:
    normalized = name.lower()
    for metric in metrics:
        if metric.name.lower() == normalized:
            return metric
    return None


def _outcome_from_dict(row: dict[str, Any]) -> ExperimentOutcome:
    metrics = [
        ExperimentMetric(
            name=str(item.get("name", "")),
            baseline=_optional_float(item.get("baseline")),
            actual=_optional_float(item.get("actual")),
            expected_delta_pct=_optional_float(item.get("expected_delta_pct")),
            actual_delta_pct=_optional_float(item.get("actual_delta_pct")),
            weight=_optional_float(item.get("weight")) or 1.0,
            higher_is_better=bool(item.get("higher_is_better", True)),
        )
        for item in row.get("metrics", [])
        if isinstance(item, dict)
    ]
    return ExperimentOutcome(
        id=str(row["id"]),
        experiment_id=str(row.get("experiment_id", "")),
        created_at=str(row.get("created_at", "")),
        metrics=metrics,
        result=_coerce_result(row.get("result", ExperimentResult.UNKNOWN.value)),
        success_score=_optional_float(row.get("success_score")) or 0.0,
        notes=str(row.get("notes", "")),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_result(value: object) -> ExperimentResult:
    try:
        return ExperimentResult(str(value))
    except ValueError:
        return ExperimentResult.UNKNOWN
