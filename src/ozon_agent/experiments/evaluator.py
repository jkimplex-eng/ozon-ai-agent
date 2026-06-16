from __future__ import annotations

from ozon_agent.experiments.metrics import (
    SUPPORTED_METRICS,
    calculate_percent_change,
    compare_metric_direction,
    normalize_expected_delta,
)
from ozon_agent.experiments.models import Experiment, ExperimentEvaluation
from ozon_agent.learning.metrics import bounded_score


def evaluate_experiment(
    experiment: Experiment,
    baseline_metrics: dict[str, float],
    final_metrics: dict[str, float],
    expected_effect: dict[str, object],
) -> ExperimentEvaluation:
    metric_names = set(baseline_metrics) | set(final_metrics) | set(expected_effect)
    comparable_metrics = sorted(
        SUPPORTED_METRICS.intersection(metric_names)
    )
    actual_effect: dict[str, float] = {}
    direction_results: list[bool] = []
    score_parts: list[float] = []

    for metric_name in comparable_metrics:
        actual_delta = calculate_percent_change(
            baseline_metrics.get(metric_name),
            final_metrics.get(metric_name),
        )
        if actual_delta is not None:
            actual_effect[metric_name] = actual_delta
        expected_delta = normalize_expected_delta(metric_name, expected_effect.get(metric_name))
        direction_match = compare_metric_direction(expected_delta, actual_delta)
        if direction_match is not None:
            direction_results.append(direction_match)
        if expected_delta is None or actual_delta is None:
            continue
        denominator = max(abs(expected_delta), 1.0)
        error_ratio = abs(actual_delta - expected_delta) / denominator
        score_parts.append(bounded_score(1.0 - error_ratio))

    success_score = sum(score_parts) / len(score_parts) if score_parts else None
    direction_accuracy = (
        sum(1 for matched in direction_results if matched) / len(direction_results)
        if direction_results
        else None
    )
    summary = _build_summary(
        experiment=experiment,
        comparable_metrics=comparable_metrics,
        baseline_metrics=baseline_metrics,
        final_metrics=final_metrics,
        success_score=success_score,
        direction_accuracy=direction_accuracy,
    )
    return ExperimentEvaluation(
        success_score=success_score,
        direction_accuracy=direction_accuracy,
        actual_effect=actual_effect,
        expected_effect=dict(expected_effect),
        summary=summary,
    )


def _build_summary(
    experiment: Experiment,
    comparable_metrics: list[str],
    baseline_metrics: dict[str, float],
    final_metrics: dict[str, float],
    success_score: float | None,
    direction_accuracy: float | None,
) -> str:
    if not baseline_metrics:
        return f"Experiment {experiment.id} has no baseline metrics for evaluation."
    if not final_metrics:
        return f"Experiment {experiment.id} has no final metrics for evaluation."
    if not comparable_metrics:
        return f"Experiment {experiment.id} has no comparable metrics to evaluate."
    success_text = f"{success_score:.2f}" if success_score is not None else "unknown"
    direction_text = f"{direction_accuracy:.2f}" if direction_accuracy is not None else "unknown"
    metrics_text = ", ".join(comparable_metrics)
    return (
        f"Experiment {experiment.id} evaluated on {metrics_text}; "
        f"success_score={success_text}, direction_accuracy={direction_text}"
    )
