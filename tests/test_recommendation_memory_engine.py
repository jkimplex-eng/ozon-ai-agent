from __future__ import annotations

from ozon_agent.decision.models import (
    ConfidenceLevel,
    ConfidenceScore,
    DecisionFeature,
    Opportunity,
    OpportunityType,
    Recommendation,
    RecommendationAction,
    RiskLevel,
    RiskScore,
    utc_now_iso,
)
from ozon_agent.memory.engine import (
    generate_memory_support,
    refresh_memory_insights,
    remember_recommendation,
)
from ozon_agent.memory.models import MemoryResult
from ozon_agent.memory.repository import list_memory_records
from ozon_agent.memory.statistics import build_memory_statistics


def test_remember_recommendation_and_build_stats(tmp_path) -> None:
    record = remember_recommendation(_recommendation(), root=tmp_path)

    assert record.result is MemoryResult.UNKNOWN
    assert list_memory_records(root=tmp_path) == [record]
    stats = build_memory_statistics([record])
    assert stats.total_records == 1


def test_generate_memory_support_uses_similar_records(tmp_path) -> None:
    record = remember_recommendation(_recommendation(), root=tmp_path)
    record.result = MemoryResult.SUCCESS
    record.success_score = 0.9
    from ozon_agent.memory.repository import save_memory_record

    save_memory_record(record, root=tmp_path)
    insights = refresh_memory_insights(root=tmp_path)

    support = generate_memory_support(
        _feature(),
        _opportunity(),
        RecommendationAction.INCREASE_BUDGET,
        root=tmp_path,
    )

    assert insights
    assert support["memory_signals"]
    assert support["similar_recommendations"]
    assert support["historical_action_success_rate"] == 1.0
    assert support["memory_confidence"] > 0.5


def _feature() -> DecisionFeature:
    return DecisionFeature(
        sku="SKU-1",
        supporting_metrics={"category": "Rugs", "price_range": "1000-1500"},
    )


def _opportunity() -> Opportunity:
    return Opportunity(
        opportunity_type=OpportunityType.AD_GROWTH,
        sku="SKU-1",
        severity="high",
        impact_score=0.8,
        reason="high ROAS",
        metrics={},
    )


def _recommendation() -> Recommendation:
    return Recommendation(
        sku="SKU-1",
        action=RecommendationAction.INCREASE_BUDGET,
        expected_effect="increase orders",
        confidence=ConfidenceScore(0.8, ConfidenceLevel.HIGH, []),
        risk=RiskScore(RiskLevel.LOW, 0.2, []),
        reason="high ROAS",
        supporting_metrics={"category": "Rugs", "price_range": "1000-1500"},
        created_at=utc_now_iso(),
        opportunity_type=OpportunityType.AD_GROWTH,
        impact_score=0.8,
    )
