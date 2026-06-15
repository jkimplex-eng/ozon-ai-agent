from __future__ import annotations

from typing import Any

from ozon_agent.approval.models import RecommendationOutcome, StoredRecommendation
from ozon_agent.learning.metrics import median
from ozon_agent.learning.models import BacktestResult, LearningSample, RecommendationAccuracy
from ozon_agent.learning.outcome_learning import (
    build_learning_samples,
    calculate_action_accuracy,
    calculate_recommendation_accuracy,
    calculate_sku_accuracy,
)


def backtest_recommendations(
    features: list[Any],
    recommendations: list[StoredRecommendation],
    actuals: list[RecommendationOutcome],
) -> BacktestResult:
    del features
    samples = build_learning_samples(recommendations, actuals)
    return _build_backtest_result(samples)


def backtest_by_action(
    features: list[Any],
    recommendations: list[StoredRecommendation],
    actuals: list[RecommendationOutcome],
) -> dict[str, RecommendationAccuracy]:
    del features
    samples = build_learning_samples(recommendations, actuals)
    return calculate_action_accuracy(samples)


def backtest_by_sku(
    features: list[Any],
    recommendations: list[StoredRecommendation],
    actuals: list[RecommendationOutcome],
) -> dict[str, RecommendationAccuracy]:
    del features
    samples = build_learning_samples(recommendations, actuals)
    return calculate_sku_accuracy(samples)


def _build_backtest_result(samples: list[LearningSample]) -> BacktestResult:
    accuracy = calculate_recommendation_accuracy(samples)
    error_values = [value for sample in samples for value in sample.percentage_errors.values()]
    direction_values = [value for sample in samples for value in sample.direction_matches.values()]
    success_values = [
        sample.success_score for sample in samples if sample.success_score is not None
    ]
    profit_lift_values: list[float] = []
    for sample in samples:
        expected_profit = _expected_metric_value(sample.expected_effect, "profit")
        actual_profit = _actual_metric_value(sample.actual_effect, "profit")
        if expected_profit is not None and actual_profit is not None:
            profit_lift_values.append(actual_profit)
    return BacktestResult(
        total_recommendations=len(samples),
        successful_recommendations=sum(1 for score in success_values if score >= 0.7),
        success_rate=accuracy.success_rate,
        average_error=accuracy.average_percentage_error,
        median_error=median(error_values),
        direction_accuracy=(
            sum(1 for value in direction_values if value) / len(direction_values)
            if direction_values
            else 0.0
        ),
        estimated_profit_lift=sum(profit_lift_values),
        by_action=calculate_action_accuracy(samples),
        by_sku=calculate_sku_accuracy(samples),
    )


def _expected_metric_value(expected_effect: dict[str, Any], metric_name: str) -> float | None:
    raw_metric = expected_effect.get(metric_name)
    if not isinstance(raw_metric, dict):
        return None
    for key in ("delta_pct", "expected_delta_pct", "change_pct", "target_pct"):
        raw_value = raw_metric.get(key)
        if raw_value is None:
            continue
        return float(raw_value)
    return None


def _actual_metric_value(actual_effect: dict[str, Any], metric_name: str) -> float | None:
    raw_value = actual_effect.get(metric_name)
    if raw_value is None:
        return None
    return float(raw_value)
