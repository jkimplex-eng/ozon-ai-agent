from __future__ import annotations

from ozon_agent.research.insights.models import InsightPriority


def priority_from_score(score: float) -> InsightPriority:
    bounded = max(0.0, min(float(score), 100.0))
    if bounded >= 85:
        return InsightPriority.CRITICAL
    if bounded >= 65:
        return InsightPriority.HIGH
    if bounded >= 35:
        return InsightPriority.MEDIUM
    return InsightPriority.LOW


def priority_sort_value(priority: InsightPriority) -> int:
    return {
        InsightPriority.CRITICAL: 0,
        InsightPriority.HIGH: 1,
        InsightPriority.MEDIUM: 2,
        InsightPriority.LOW: 3,
    }[priority]
