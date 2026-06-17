from __future__ import annotations

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.decision.models import DecisionFeature, Opportunity, OpportunityType
from ozon_agent.decision.recommendation_engine import generate_recommendation
from ozon_agent.decision.recommendation_summary import (
    format_recommendation_text,
    recommendation_to_dict,
)
from ozon_agent.memory.models import MemoryResult, RecommendationMemoryRecord, utc_now_iso
from ozon_agent.memory.repository import save_memory_record


def test_recommendation_is_enriched_from_memory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_RECOMMENDATION_MEMORY_ROOT", str(tmp_path))
    save_memory_record(_record(), root=tmp_path)

    recommendation = generate_recommendation(_feature(), _opportunity())
    payload = recommendation_to_dict(recommendation)
    text = format_recommendation_text(recommendation)

    assert payload["memory_signals"]
    assert payload["similar_recommendations"]
    assert payload["historical_action_success_rate"] == 1.0
    assert "Recommendation memory" in text


def test_recommendation_memory_cli(tmp_path) -> None:
    save_memory_record(_record(), root=tmp_path)
    runner = CliRunner()
    env = {"OZON_AGENT_RECOMMENDATION_MEMORY_ROOT": str(tmp_path)}

    stats = runner.invoke(main, ["recommendations", "memory", "stats"], env=env)
    search = runner.invoke(main, ["recommendations", "memory", "search", "SKU-1"], env=env)
    refresh = runner.invoke(main, ["recommendations", "memory", "refresh"], env=env)
    insights = runner.invoke(main, ["recommendations", "memory", "insights"], env=env)

    assert stats.exit_code == 0
    assert "Autonomous Recommendation Memory" in stats.output
    assert search.exit_code == 0
    assert "SKU-1" in search.output
    assert refresh.exit_code == 0
    assert "Refreshed" in refresh.output
    assert insights.exit_code == 0
    assert "Recommendation Memory Insights" in insights.output


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


def _record() -> RecommendationMemoryRecord:
    from ozon_agent.decision.models import RecommendationAction

    return RecommendationMemoryRecord(
        id="memory-1",
        created_at=utc_now_iso(),
        sku="SKU-1",
        action=RecommendationAction.INCREASE_BUDGET,
        opportunity_type=OpportunityType.AD_GROWTH,
        reason="high ROAS",
        expected_effect="increase orders",
        supporting_metrics={"category": "Rugs", "price_range": "1000-1500"},
        result=MemoryResult.SUCCESS,
        success_score=0.9,
    )
