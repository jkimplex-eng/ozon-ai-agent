from __future__ import annotations

from pathlib import Path

from ozon_agent.research.insights.detectors import (
    detect_all_insights,
    detect_opportunity_candidates,
    detect_risk_candidates,
)
from ozon_agent.research.insights.models import MarketInsight, MarketOpportunity, MarketRisk
from ozon_agent.research.knowledge.insight_store import save_insights
from ozon_agent.research.knowledge.models import MarketInsightRecord, MarketKnowledgeSnapshot
from ozon_agent.research.knowledge.snapshot_store import list_snapshots


def generate_market_insights(
    snapshots: list[MarketKnowledgeSnapshot] | None = None,
    storage_dir: str | Path | None = None,
    persist: bool = True,
) -> list[MarketInsight]:
    source_snapshots = (
        snapshots if snapshots is not None else list_snapshots(storage_dir=storage_dir)
    )
    insights = detect_all_insights(source_snapshots)
    if persist:
        save_insights(
            [_to_market_insight_record(insight) for insight in insights],
            storage_dir=storage_dir,
        )
    return insights


def detect_risks(insights: list[MarketInsight] | None = None) -> list[MarketRisk]:
    return detect_risk_candidates(insights or [])


def detect_opportunities(
    insights: list[MarketInsight] | None = None,
) -> list[MarketOpportunity]:
    return detect_opportunity_candidates(insights or [])


def _to_market_insight_record(insight: MarketInsight) -> MarketInsightRecord:
    return MarketInsightRecord(
        id=insight.id,
        created_at=insight.created_at,
        insight_type=insight.insight_type.value,
        sku=insight.sku,
        message=insight.message,
        severity=insight.priority.value,
        snapshot_id=insight.snapshot_id,
        previous_snapshot_id=insight.previous_snapshot_id,
        current_snapshot_id=insight.snapshot_id,
        competitor_key=insight.competitor_key,
        metrics={
            **insight.metrics,
            "score": insight.score,
            "priority": insight.priority.value,
            "risk_count": len(insight.risks),
            "opportunity_count": len(insight.opportunities),
            "signal_count": len(insight.signals),
        },
    )
