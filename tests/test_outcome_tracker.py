from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.approval.models import RecommendationStatus, StoredRecommendation
from ozon_agent.approval.outcome_tracker import calculate_outcome
from ozon_agent.approval.serializers import outcome_from_json, outcome_to_json
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel


def test_outcome_calculation() -> None:
    recommendation = _sample_recommendation()
    outcome = calculate_outcome(
        recommendation,
        before_metrics={"orders": 100},
        after_metrics={"orders": 109},
        window_days=7,
    )
    assert outcome.actual_effect["orders"] == 9.0
    assert round(outcome.forecast_error or 0.0, 2) == 25.0
    assert outcome.success_score is not None


def test_outcome_json_serialization() -> None:
    recommendation = _sample_recommendation()
    outcome = calculate_outcome(
        recommendation,
        before_metrics={"orders": 100},
        after_metrics={"orders": 109},
        window_days=7,
    )
    payload = outcome_to_json(outcome)
    restored = outcome_from_json(payload)
    assert restored.recommendation_id == recommendation.id
    assert restored.actual_effect == outcome.actual_effect


def _sample_recommendation() -> StoredRecommendation:
    now = datetime.now(UTC)
    return StoredRecommendation(
        id="rec-42",
        created_at=now,
        updated_at=now,
        sku="SKU-42",
        product_name="Outcome SKU",
        action=RecommendationAction.INCREASE_BUDGET,
        reason="Test outcome",
        confidence_score=0.8,
        confidence_level=ConfidenceLevel.HIGH,
        risk_score=0.3,
        risk_level=RiskLevel.MEDIUM,
        expected_effect={"orders": {"delta_pct": 12.0}, "revenue": {"delta_pct": 10.0}},
        supporting_metrics={"roas": 4.1},
        status=RecommendationStatus.OBSERVED,
        source="decision_engine",
    )
