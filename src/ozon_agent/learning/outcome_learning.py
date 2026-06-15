from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from ozon_agent.approval.models import RecommendationOutcome, StoredRecommendation
from ozon_agent.decision.models import OpportunityType
from ozon_agent.learning.metrics import (
    direction_matches,
    extract_expected_delta,
    safe_percentage_error,
    success_score,
)
from ozon_agent.learning.models import LearningSample, RecommendationAccuracy


def build_learning_samples(
    recommendations: list[StoredRecommendation],
    outcomes: list[RecommendationOutcome],
) -> list[LearningSample]:
    if not recommendations or not outcomes:
        return []

    recommendation_lookup = {
        recommendation.id: recommendation for recommendation in recommendations
    }
    samples: list[LearningSample] = []
    for outcome in outcomes:
        recommendation = recommendation_lookup.get(outcome.recommendation_id)
        if recommendation is None:
            continue
        absolute_errors: dict[str, float] = {}
        percentage_errors: dict[str, float] = {}
        direction_results: dict[str, bool] = {}
        for metric_name, expectation in recommendation.expected_effect.items():
            if not isinstance(expectation, dict):
                continue
            expected_delta = extract_expected_delta(expectation)
            actual_delta = _metric_value(outcome.actual_effect.get(metric_name))
            if expected_delta is None or actual_delta is None:
                continue
            absolute_errors[metric_name] = abs(actual_delta - expected_delta)
            percentage_error = safe_percentage_error(expected_delta, actual_delta)
            if percentage_error is not None:
                percentage_errors[metric_name] = percentage_error
            direction_match = direction_matches(expected_delta, actual_delta)
            if direction_match is not None:
                direction_results[metric_name] = direction_match
        sample_success_score = outcome.success_score
        if sample_success_score is None:
            sample_success_score = success_score(
                recommendation.expected_effect,
                outcome.actual_effect,
            )
        samples.append(
            LearningSample(
                recommendation_id=recommendation.id,
                action=recommendation.action,
                sku=recommendation.sku,
                risk_level=recommendation.risk_level,
                confidence_level=recommendation.confidence_level,
                opportunity_type=_resolve_opportunity_type(recommendation),
                time_window_days=outcome.observation_window_days,
                expected_effect=dict(recommendation.expected_effect),
                actual_effect=dict(outcome.actual_effect),
                absolute_errors=absolute_errors,
                percentage_errors=percentage_errors,
                direction_matches=direction_results,
                success_score=sample_success_score,
                forecast_error=outcome.forecast_error,
            )
        )
    return samples


def calculate_recommendation_accuracy(samples: list[LearningSample]) -> RecommendationAccuracy:
    if not samples:
        return RecommendationAccuracy(
            total_samples=0,
            comparable_metrics=0,
            average_absolute_error=0.0,
            average_percentage_error=0.0,
            direction_accuracy=0.0,
            success_rate=0.0,
        )

    absolute_errors = [value for sample in samples for value in sample.absolute_errors.values()]
    percentage_errors = [value for sample in samples for value in sample.percentage_errors.values()]
    direction_values = [value for sample in samples for value in sample.direction_matches.values()]
    success_values = [
        sample.success_score for sample in samples if sample.success_score is not None
    ]
    success_count = sum(1 for value in success_values if value >= 0.7)
    return RecommendationAccuracy(
        total_samples=len(samples),
        comparable_metrics=len(percentage_errors),
        average_absolute_error=(
            sum(absolute_errors) / len(absolute_errors) if absolute_errors else 0.0
        ),
        average_percentage_error=(
            sum(percentage_errors) / len(percentage_errors) if percentage_errors else 0.0
        ),
        direction_accuracy=(
            sum(1 for value in direction_values if value) / len(direction_values)
            if direction_values
            else 0.0
        ),
        success_rate=(success_count / len(success_values) if success_values else 0.0),
    )


def calculate_action_accuracy(
    samples: list[LearningSample],
) -> dict[str, RecommendationAccuracy]:
    return _calculate_group_accuracy(samples, key_fn=lambda sample: sample.action.value)


def calculate_sku_accuracy(samples: list[LearningSample]) -> dict[str, RecommendationAccuracy]:
    return _calculate_group_accuracy(samples, key_fn=lambda sample: sample.sku)


def _calculate_group_accuracy(
    samples: list[LearningSample],
    key_fn: Callable[[LearningSample], str],
) -> dict[str, RecommendationAccuracy]:
    grouped: dict[str, list[LearningSample]] = defaultdict(list)
    for sample in samples:
        grouped[str(key_fn(sample))].append(sample)
    return {
        key: calculate_recommendation_accuracy(group_samples)
        for key, group_samples in grouped.items()
    }


def _metric_value(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _resolve_opportunity_type(recommendation: StoredRecommendation) -> OpportunityType | None:
    raw_value = recommendation.supporting_metrics.get("opportunity_type")
    if raw_value is None:
        return None
    try:
        return OpportunityType(str(raw_value))
    except ValueError:
        return None
