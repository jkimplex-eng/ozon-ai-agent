from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.approval.models import (
    RecommendationOutcome,
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel
from ozon_agent.learning.backtesting import (
    backtest_by_action,
    backtest_by_sku,
    backtest_recommendations,
)
from ozon_agent.learning.metrics import (
    bounded_score,
    direction_matches,
    median,
    safe_percentage_error,
)


def test_metric_helpers() -> None:
    assert safe_percentage_error(10.0, 10.0) == 0.0
    assert direction_matches(10.0, -2.0) is False
    assert median([1.0, 3.0, 2.0]) == 2.0
    assert bounded_score(1.4) == 1.0


def test_backtest_summary() -> None:
    recommendations = [
        _recommendation("rec-1", "SKU-1", "INCREASE_BUDGET"),
        _recommendation("rec-2", "SKU-2", "DECREASE_PRICE"),
    ]
    outcomes = [
        _outcome("out-1", "rec-1", {"orders": 9.0, "profit": 5.0}),
        _outcome("out-2", "rec-2", {"orders": -4.0, "profit": -2.0}),
    ]
    result = backtest_recommendations([], recommendations, outcomes)
    assert result.total_recommendations == 2
    assert result.average_error >= 0.0
    assert result.direction_accuracy >= 0.0


def test_backtest_by_action_and_sku() -> None:
    recommendations = [
        _recommendation("rec-1", "SKU-1", "INCREASE_BUDGET"),
        _recommendation("rec-2", "SKU-2", "DECREASE_PRICE"),
    ]
    outcomes = [
        _outcome("out-1", "rec-1", {"orders": 9.0}),
        _outcome("out-2", "rec-2", {"orders": -4.0}),
    ]
    by_action = backtest_by_action([], recommendations, outcomes)
    by_sku = backtest_by_sku([], recommendations, outcomes)
    assert "INCREASE_BUDGET" in by_action
    assert "SKU-1" in by_sku


def _recommendation(
    recommendation_id: str,
    sku: str,
    action: str,
) -> StoredRecommendation:
    now = datetime.now(UTC)
    expected_orders = 10.0 if action == "INCREASE_BUDGET" else -5.0
    return StoredRecommendation(
        id=recommendation_id,
        created_at=now,
        updated_at=now,
        sku=sku,
        product_name="Product",
        action=RecommendationAction(action),
        reason="Test",
        confidence_score=0.7,
        confidence_level=ConfidenceLevel.MEDIUM,
        risk_score=0.3,
        risk_level=RiskLevel.MEDIUM,
        expected_effect={
            "orders": {"delta_pct": expected_orders},
            "profit": {"delta_pct": 4.0},
        },
        supporting_metrics={"opportunity_type": "AD_GROWTH"},
        status=RecommendationStatus.OBSERVED,
        source="decision_engine",
    )


def _outcome(
    outcome_id: str,
    recommendation_id: str,
    actual_effect: dict[str, float],
) -> RecommendationOutcome:
    return RecommendationOutcome(
        id=outcome_id,
        recommendation_id=recommendation_id,
        created_at=datetime.now(UTC),
        observation_window_days=7,
        expected_effect={},
        actual_effect=actual_effect,
        forecast_error=None,
        success_score=None,
    )
