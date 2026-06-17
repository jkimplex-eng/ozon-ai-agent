from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ozon_agent.decision.models import DecisionFeature, Opportunity, RecommendationAction
from ozon_agent.learning.experiment_store import list_experiments
from ozon_agent.learning.models import (
    Experiment,
    ExperimentResult,
    ExperimentType,
    LearningInsight,
    SimilarityMatch,
    new_learning_id,
    utc_now_iso,
)
from ozon_agent.learning.repository import list_json, to_jsonable, write_json
from ozon_agent.learning.similarity import find_similar_experiments
from ozon_agent.learning.statistics import build_success_rate


def learn_from_experiment(
    experiment: Experiment,
    root: str | Path | None = None,
) -> LearningInsight:
    related = [
        item
        for item in list_experiments(root=root)
        if item.category == experiment.category
        and item.experiment_type is experiment.experiment_type
    ]
    if experiment.id not in {item.id for item in related}:
        related.append(experiment)
    insight = build_learning_insight(related, experiment.category, experiment.experiment_type)
    write_json("insights", insight.id, to_jsonable(insight), root=root)
    return insight


def aggregate_results(experiments: list[Experiment]) -> dict[str, Any]:
    return {
        "experiment_count": len(experiments),
        "success_rate": build_success_rate(experiments),
        "average_metric_lift": _average_metric_lift(experiments),
    }


def build_learning_insight(
    experiments: list[Experiment],
    category: str,
    experiment_type: ExperimentType,
) -> LearningInsight:
    aggregate = aggregate_results(experiments)
    success_rate = float(aggregate["success_rate"])
    lifts = dict(aggregate["average_metric_lift"])
    message = (
        f"{category or 'UNKNOWN'} / {experiment_type.value}: "
        f"{len(experiments)} experiments, success rate {success_rate:.0%}"
    )
    return LearningInsight(
        id=new_learning_id("insight"),
        created_at=utc_now_iso(),
        category=category or "UNKNOWN",
        experiment_type=experiment_type,
        experiment_count=len(experiments),
        success_rate=success_rate,
        average_metric_lift={str(key): float(value) for key, value in lifts.items()},
        message=message,
        supporting_experiments=[item.id for item in experiments],
    )


def generate_recommendation_support(
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
    action: RecommendationAction | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    target = _experiment_from_recommendation_context(feature, opportunity, action)
    similar = find_similar_experiments(target, root=root)
    historical_success_rate = _historical_success_rate(similar)
    insights = _matching_insights(target, root=root)
    return {
        "learning_signals": _learning_signals(similar, historical_success_rate, insights),
        "similar_experiments": [_match_to_dict(match) for match in similar[:5]],
        "historical_success_rate": historical_success_rate,
        "learning_insights": insights,
        "recommended_confidence": _recommended_confidence(historical_success_rate, similar),
    }


def _experiment_from_recommendation_context(
    feature: DecisionFeature,
    opportunity: Opportunity | None,
    action: RecommendationAction | None,
) -> Experiment:
    experiment_type = _experiment_type_for_action(action)
    return Experiment(
        id="recommendation-context",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        sku=feature.sku,
        experiment_type=experiment_type,
        title=opportunity.reason if opportunity else "",
        category=str(feature.supporting_metrics.get("category", "")),
        subcategory=str(feature.supporting_metrics.get("subcategory", "")),
        product_type=str(feature.supporting_metrics.get("product_type", "")),
        price_range=str(feature.supporting_metrics.get("price_range", "")),
        shop_size=str(feature.supporting_metrics.get("shop_size", "")),
        period=str(feature.supporting_metrics.get("period", "")),
        change_size=_change_size_for_action(action),
        expected_effect={"opportunity": opportunity.opportunity_type.value if opportunity else ""},
    )


def _experiment_type_for_action(action: RecommendationAction | None) -> ExperimentType:
    if action in {
        RecommendationAction.INCREASE_PRICE,
        RecommendationAction.DECREASE_PRICE,
    }:
        return ExperimentType.PRICE_CHANGE
    if action is RecommendationAction.INCREASE_BUDGET:
        return ExperimentType.AD_BUDGET_CHANGE
    if action in {
        RecommendationAction.DECREASE_BUDGET,
        RecommendationAction.PAUSE_CAMPAIGN,
    }:
        return ExperimentType.AD_BUDGET_CHANGE
    if action is RecommendationAction.INCREASE_STOCK:
        return ExperimentType.STOCK_CHANGE
    if action is RecommendationAction.IMPROVE_CONTENT:
        return ExperimentType.CONTENT_CHANGE
    if action is RecommendationAction.BOOST_REVIEWS:
        return ExperimentType.CONTENT_CHANGE
    return ExperimentType.CUSTOM


def _change_size_for_action(action: RecommendationAction | None) -> float | None:
    if action in {RecommendationAction.INCREASE_PRICE, RecommendationAction.DECREASE_PRICE}:
        return 5.0
    if action in {RecommendationAction.INCREASE_BUDGET, RecommendationAction.DECREASE_BUDGET}:
        return 10.0
    return None


def _historical_success_rate(matches: list[SimilarityMatch]) -> float:
    comparable = [match for match in matches if match.result is not ExperimentResult.UNKNOWN]
    if not comparable:
        return 0.0
    score = sum(
        1.0 if match.result is ExperimentResult.SUCCESS else 0.5
        for match in comparable
        if match.result in {ExperimentResult.SUCCESS, ExperimentResult.PARTIAL_SUCCESS}
    )
    return score / len(comparable)


def _matching_insights(target: Experiment, root: str | Path | None) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    for row in list_json("insights", root=root):
        if str(row.get("experiment_type")) != target.experiment_type.value:
            continue
        category = str(row.get("category", ""))
        if category and target.category and category != target.category:
            continue
        insights.append(row)
    return insights[:5]


def _learning_signals(
    matches: list[SimilarityMatch],
    success_rate: float,
    insights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not matches and not insights:
        return []
    return [
        {
            "type": "EXPERIMENT_LEARNING",
            "similar_experiments": len(matches),
            "historical_success_rate": success_rate,
            "insights": len(insights),
            "message": (
                f"{len(matches)} similar experiments, "
                f"historical success rate {success_rate:.0%}"
            ),
        }
    ]


def _recommended_confidence(success_rate: float, matches: list[SimilarityMatch]) -> float:
    if not matches:
        return 0.5
    sample_factor = min(len(matches) / 8.0, 1.0)
    return round(max(0.0, min(1.0, 0.4 + success_rate * 0.4 + sample_factor * 0.2)), 4)


def _match_to_dict(match: SimilarityMatch) -> dict[str, Any]:
    return {
        "experiment_id": match.experiment_id,
        "score": match.score,
        "reasons": match.reasons,
        "result": match.result.value,
        "success_score": match.success_score,
    }


def _average_metric_lift(experiments: list[Experiment]) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for experiment in experiments:
        for key, value in experiment.metrics.items():
            if key.endswith("_delta_pct") and isinstance(value, int | float):
                values[key.removesuffix("_delta_pct")].append(float(value))
    return {
        key: round(sum(metric_values) / len(metric_values), 4)
        for key, metric_values in values.items()
        if metric_values
    }
