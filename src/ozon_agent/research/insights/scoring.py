from __future__ import annotations

from ozon_agent.research.insights.models import InsightPriority
from ozon_agent.research.insights.priorities import priority_from_score
from ozon_agent.research.knowledge.models import MarketInsightRecord, MarketTrend


def score_change(change: MarketInsightRecord) -> float:
    delta_percent = _float_metric(change, "delta_percent")
    delta = abs(_float_metric(change, "delta") or 0.0)
    if delta_percent is not None:
        magnitude = min(abs(delta_percent) * 4.0, 80.0)
    else:
        magnitude = min(delta, 60.0)
    competitor_bonus = 10.0 if change.competitor_key else 0.0
    recency_bonus = 5.0
    return _bounded(magnitude + competitor_bonus + recency_bonus)


def score_trend(trend: MarketTrend) -> float:
    delta_percent = abs(trend.delta_percent or 0.0)
    magnitude = min(delta_percent * 3.0, 70.0)
    history_bonus = min(max(trend.snapshot_count - 1, 0) * 7.5, 20.0)
    return _bounded(magnitude + history_bonus + 10.0)


def score_count(count: int, base: float = 25.0) -> float:
    return _bounded(base + min(count * 10.0, 60.0))


def priority_for_change(change: MarketInsightRecord) -> InsightPriority:
    return priority_from_score(score_change(change))


def _float_metric(change: MarketInsightRecord, key: str) -> float | None:
    value = change.metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded(value: float) -> float:
    return max(0.0, min(float(value), 100.0))
