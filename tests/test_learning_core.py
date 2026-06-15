from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.approval.models import (
    RecommendationOutcome,
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel
from ozon_agent.learning.outcome_learning import (
    build_learning_samples,
    calculate_action_accuracy,
    calculate_recommendation_accuracy,
    calculate_sku_accuracy,
)


def test_empty_inputs() -> None:
    assert build_learning_samples([], []) == []
    accuracy = calculate_recommendation_accuracy([])
    assert accuracy.total_samples == 0
    assert accuracy.average_percentage_error == 0.0


def test_missing_metrics_are_tolerated() -> None:
    recommendation = _sample_recommendation("rec-1", "SKU-1")
    outcome = RecommendationOutcome(
        id="out-1",
        recommendation_id="rec-1",
        created_at=datetime.now(UTC),
        observation_window_days=7,
        expected_effect={"orders": {"delta_pct": 10.0}},
        actual_effect={},
        forecast_error=None,
        success_score=None,
    )
    samples = build_learning_samples([recommendation], [outcome])
    assert len(samples) == 1
    assert samples[0].percentage_errors == {}


def test_exact_match_expected_vs_actual() -> None:
    recommendation = _sample_recommendation("rec-2", "SKU-2")
    outcome = RecommendationOutcome(
        id="out-2",
        recommendation_id="rec-2",
        created_at=datetime.now(UTC),
        observation_window_days=7,
        expected_effect={"orders": {"delta_pct": 10.0}},
        actual_effect={"orders": 10.0},
        forecast_error=0.0,
        success_score=1.0,
    )
    samples = build_learning_samples([recommendation], [outcome])
    assert samples[0].absolute_errors["orders"] == 0.0
    assert samples[0].direction_matches["orders"] is True


def test_wrong_direction_detected() -> None:
    recommendation = _sample_recommendation("rec-3", "SKU-3")
    outcome = RecommendationOutcome(
        id="out-3",
        recommendation_id="rec-3",
        created_at=datetime.now(UTC),
        observation_window_days=7,
        expected_effect={"orders": {"delta_pct": 10.0}},
        actual_effect={"orders": -5.0},
        forecast_error=150.0,
        success_score=0.0,
    )
    samples = build_learning_samples([recommendation], [outcome])
    assert samples[0].direction_matches["orders"] is False


def test_action_and_sku_accuracy() -> None:
    recommendations = [
        _sample_recommendation("rec-a", "SKU-A"),
        _sample_recommendation("rec-b", "SKU-B"),
    ]
    outcomes = [
        _sample_outcome("out-a", "rec-a", {"orders": 8.0}),
        _sample_outcome("out-b", "rec-b", {"orders": 6.0}),
    ]
    samples = build_learning_samples(recommendations, outcomes)
    action_accuracy = calculate_action_accuracy(samples)
    sku_accuracy = calculate_sku_accuracy(samples)
    assert "INCREASE_BUDGET" in action_accuracy
    assert "SKU-A" in sku_accuracy


def _sample_recommendation(recommendation_id: str, sku: str) -> StoredRecommendation:
    now = datetime.now(UTC)
    return StoredRecommendation(
        id=recommendation_id,
        created_at=now,
        updated_at=now,
        sku=sku,
        product_name="Product",
        action=RecommendationAction.INCREASE_BUDGET,
        reason="Test",
        confidence_score=0.8,
        confidence_level=ConfidenceLevel.HIGH,
        risk_score=0.2,
        risk_level=RiskLevel.LOW,
        expected_effect={"orders": {"delta_pct": 10.0}},
        supporting_metrics={"opportunity_type": "AD_GROWTH"},
        status=RecommendationStatus.OBSERVED,
        source="decision_engine",
    )


def _sample_outcome(
    outcome_id: str,
    recommendation_id: str,
    actual_effect: dict[str, float],
) -> RecommendationOutcome:
    return RecommendationOutcome(
        id=outcome_id,
        recommendation_id=recommendation_id,
        created_at=datetime.now(UTC),
        observation_window_days=7,
        expected_effect={"orders": {"delta_pct": 10.0}},
        actual_effect=actual_effect,
        forecast_error=None,
        success_score=None,
    )
