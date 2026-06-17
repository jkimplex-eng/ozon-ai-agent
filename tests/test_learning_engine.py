from __future__ import annotations

from ozon_agent.decision.models import (
    DecisionFeature,
    Opportunity,
    OpportunityType,
    RecommendationAction,
)
from ozon_agent.learning.experiment_store import save_experiment
from ozon_agent.learning.learning_engine import (
    aggregate_results,
    generate_recommendation_support,
    learn_from_experiment,
)
from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso


def test_learn_from_experiment_builds_insight(tmp_path) -> None:
    experiment = _experiment("exp-1", ExperimentResult.SUCCESS)
    save_experiment(experiment, root=tmp_path)

    insight = learn_from_experiment(experiment, root=tmp_path)

    assert insight.experiment_count == 1
    assert insight.success_rate == 1.0
    assert insight.average_metric_lift["orders"] == 14.0


def test_generate_recommendation_support_uses_similar_experiments(tmp_path) -> None:
    save_experiment(_experiment("exp-1", ExperimentResult.SUCCESS), root=tmp_path)
    feature = DecisionFeature(
        sku="SKU-1",
        supporting_metrics={
            "category": "Rugs",
            "subcategory": "Round",
            "product_type": "Carpet",
            "price_range": "1000-1500",
            "shop_size": "small",
            "period": "2026-06",
        },
    )
    opportunity = Opportunity(
        opportunity_type=OpportunityType.PRICE_CONVERSION,
        sku="SKU-1",
        severity="high",
        impact_score=0.8,
        reason="conversion declined",
        metrics={},
    )

    support = generate_recommendation_support(
        feature,
        opportunity,
        RecommendationAction.DECREASE_PRICE,
        root=tmp_path,
    )

    assert support["similar_experiments"]
    assert support["historical_success_rate"] == 1.0
    assert support["learning_signals"]
    assert support["recommended_confidence"] > 0.5


def test_aggregate_results_handles_empty_inputs() -> None:
    assert aggregate_results([])["success_rate"] == 0.0


def _experiment(experiment_id: str, result: ExperimentResult) -> Experiment:
    now = utc_now_iso()
    return Experiment(
        id=experiment_id,
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        experiment_type=ExperimentType.PRICE_CHANGE,
        category="Rugs",
        subcategory="Round",
        product_type="Carpet",
        price_range="1000-1500",
        shop_size="small",
        period="2026-06",
        change_size=5.0,
        metrics={"orders_delta_pct": 14.0, "profit_delta_pct": 5.8},
        result=result,
    )
