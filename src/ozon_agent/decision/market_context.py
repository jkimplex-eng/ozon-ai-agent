from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ozon_agent.research.insights.engine import detect_opportunities, detect_risks
from ozon_agent.research.insights.models import (
    MarketInsight,
    MarketInsightType,
    MarketOpportunity,
    MarketRisk,
)
from ozon_agent.research.knowledge.insight_store import list_insights
from ozon_agent.research.knowledge.models import MarketInsightRecord


@dataclass(frozen=True)
class MarketContext:
    price_pressure: str = "LOW"
    competitor_growth: str = "LOW"
    review_pressure: str = "LOW"
    rating_pressure: str = "LOW"
    market_risk_score: float = 0.0
    market_opportunity_score: float = 0.0
    market_signals: list[dict[str, Any]] = field(default_factory=list)
    market_risks: list[dict[str, Any]] = field(default_factory=list)
    market_opportunities: list[dict[str, Any]] = field(default_factory=list)


def load_market_insights(storage_dir: str | Path | None = None) -> list[MarketInsight]:
    return [_record_to_insight(record) for record in list_insights(storage_dir=storage_dir)]


def load_market_risks(storage_dir: str | Path | None = None) -> list[dict[str, Any]]:
    insights = load_market_insights(storage_dir=storage_dir)
    return [_risk_to_dict(risk) for risk in detect_risks(insights)]


def load_market_opportunities(storage_dir: str | Path | None = None) -> list[dict[str, Any]]:
    insights = load_market_insights(storage_dir=storage_dir)
    return [_opportunity_to_dict(item) for item in detect_opportunities(insights)]


def build_market_context(
    sku: str | None = None,
    storage_dir: str | Path | None = None,
    insights: list[MarketInsight] | None = None,
) -> MarketContext:
    source_insights = insights if insights is not None else load_market_insights(storage_dir)
    filtered = _filter_insights(source_insights, sku)
    risks = [_risk_to_dict(risk) for risk in detect_risks(filtered)]
    opportunities = [_opportunity_to_dict(item) for item in detect_opportunities(filtered)]
    signals = [_insight_to_signal_dict(insight) for insight in filtered]
    return MarketContext(
        price_pressure=_pressure_for(filtered, {MarketInsightType.PRICE_DROP}),
        competitor_growth=_pressure_for(filtered, {MarketInsightType.NEW_COMPETITOR}),
        review_pressure=_pressure_for(filtered, {MarketInsightType.REVIEW_SURGE}),
        rating_pressure=_pressure_for(filtered, {MarketInsightType.RATING_CHANGE}),
        market_risk_score=_max_score(risks),
        market_opportunity_score=_max_score(opportunities),
        market_signals=signals,
        market_risks=risks,
        market_opportunities=opportunities,
    )


def _filter_insights(insights: list[MarketInsight], sku: str | None) -> list[MarketInsight]:
    if not sku:
        return insights
    normalized = sku.strip().lower()
    return [
        insight
        for insight in insights
        if insight.sku.strip().lower() in {normalized, "category"}
    ]


def _pressure_for(
    insights: list[MarketInsight],
    insight_types: set[MarketInsightType],
) -> str:
    matching = [insight for insight in insights if insight.insight_type in insight_types]
    if not matching:
        return "LOW"
    max_score = max(insight.score for insight in matching)
    count = len(matching)
    if max_score >= 65 or count >= 3:
        return "HIGH"
    if max_score >= 45 or count >= 2:
        return "MEDIUM"
    return "LOW"


def _record_to_insight(record: MarketInsightRecord) -> MarketInsight:
    insight_type = _safe_insight_type(record.insight_type)
    score = _float_metric(record.metrics, "score")
    priority = str(record.metrics.get("priority") or record.severity or "LOW")
    from ozon_agent.research.insights.models import InsightPriority

    try:
        priority_value = InsightPriority(priority)
    except ValueError:
        priority_value = InsightPriority.LOW
    return MarketInsight(
        id=record.id,
        created_at=record.created_at,
        insight_type=insight_type,
        sku=record.sku,
        message=record.message,
        score=score,
        priority=priority_value,
        metrics=dict(record.metrics),
        snapshot_id=record.snapshot_id,
        previous_snapshot_id=record.previous_snapshot_id,
        competitor_key=record.competitor_key,
    )


def _safe_insight_type(value: str) -> MarketInsightType:
    try:
        return MarketInsightType(value)
    except ValueError:
        return MarketInsightType.CATEGORY_PRESSURE


def _insight_to_signal_dict(insight: MarketInsight) -> dict[str, Any]:
    return {
        "type": insight.insight_type.value,
        "sku": insight.sku,
        "message": insight.message,
        "score": insight.score,
        "priority": insight.priority.value,
        "metrics": dict(insight.metrics),
    }


def _risk_to_dict(risk: MarketRisk) -> dict[str, Any]:
    return {
        "type": risk.risk_type,
        "sku": risk.sku,
        "message": risk.message,
        "score": risk.score,
        "priority": risk.priority.value,
        "metrics": dict(risk.metrics),
    }


def _opportunity_to_dict(opportunity: MarketOpportunity) -> dict[str, Any]:
    return {
        "type": opportunity.opportunity_type,
        "sku": opportunity.sku,
        "message": opportunity.message,
        "score": opportunity.score,
        "priority": opportunity.priority.value,
        "metrics": dict(opportunity.metrics),
    }


def _max_score(rows: list[dict[str, Any]]) -> float:
    return max((float(row.get("score", 0.0)) for row in rows), default=0.0)


def _float_metric(metrics: dict[str, Any], key: str) -> float:
    try:
        return float(metrics.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
