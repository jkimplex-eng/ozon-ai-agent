from __future__ import annotations

from typing import Any

from ozon_agent.approval.models import RecommendationOutcome, StoredRecommendation, build_outcome


def calculate_outcome(
    recommendation: StoredRecommendation,
    before_metrics: dict[str, float | int | None],
    after_metrics: dict[str, float | int | None],
    window_days: int,
) -> RecommendationOutcome:
    expected_effect = dict(recommendation.expected_effect)
    actual_effect: dict[str, float] = {}
    metric_errors: list[float] = []
    metric_success_scores: list[float] = []

    for metric_name, expectation in expected_effect.items():
        if not isinstance(expectation, dict):
            continue
        before_value = _metric_value(before_metrics.get(metric_name))
        after_value = _metric_value(after_metrics.get(metric_name))
        if before_value is None or after_value is None:
            continue
        actual_change_pct = _change_pct(before_value, after_value)
        actual_effect[metric_name] = actual_change_pct
        expected_change_pct = _extract_expected_change(expectation)
        if expected_change_pct is None:
            continue
        metric_errors.append(_forecast_error_pct(expected_change_pct, actual_change_pct))
        metric_success_scores.append(_success_score(expected_change_pct, actual_change_pct))

    forecast_error = (
        round(sum(metric_errors) / len(metric_errors), 4) if metric_errors else None
    )
    success_score = (
        round(sum(metric_success_scores) / len(metric_success_scores), 4)
        if metric_success_scores
        else None
    )
    notes = None
    if actual_effect:
        notes = (
            "Outcome uses generic metric deltas and does not include "
            "marketplace-side execution."
        )
    return build_outcome(
        recommendation_id=recommendation.id,
        observation_window_days=window_days,
        expected_effect=expected_effect,
        actual_effect=actual_effect,
        forecast_error=forecast_error,
        success_score=success_score,
        notes=notes,
    )


def _metric_value(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _extract_expected_change(effect: dict[str, Any]) -> float | None:
    for key in ("delta_pct", "expected_delta_pct", "change_pct", "target_pct"):
        value = effect.get(key)
        if value is not None:
            return float(value)
    return None


def _change_pct(before_value: float, after_value: float) -> float:
    if before_value == 0:
        return 0.0 if after_value == 0 else 100.0
    return ((after_value - before_value) / abs(before_value)) * 100.0


def _forecast_error_pct(expected_change_pct: float, actual_change_pct: float) -> float:
    denominator = abs(expected_change_pct)
    if denominator == 0:
        return abs(actual_change_pct)
    return abs(actual_change_pct - expected_change_pct) / denominator * 100.0


def _success_score(expected_change_pct: float, actual_change_pct: float) -> float:
    denominator = max(abs(expected_change_pct), 1.0)
    distance = abs(actual_change_pct - expected_change_pct) / denominator
    return max(0.0, min(1.0, 1.0 - distance))
