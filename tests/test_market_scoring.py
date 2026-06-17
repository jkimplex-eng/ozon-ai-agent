from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.insights.priorities import InsightPriority, priority_from_score
from ozon_agent.research.insights.scoring import score_change, score_trend
from ozon_agent.research.knowledge.models import MarketInsightRecord, MarketTrend


def test_priority_assignment() -> None:
    assert priority_from_score(10) is InsightPriority.LOW
    assert priority_from_score(35) is InsightPriority.MEDIUM
    assert priority_from_score(65) is InsightPriority.HIGH
    assert priority_from_score(90) is InsightPriority.CRITICAL


def test_score_change_uses_delta_percent() -> None:
    change = MarketInsightRecord(
        id="i",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        insight_type="PRICE_CHANGED",
        sku="SKU-1",
        message="price changed",
        severity="HIGH",
        competitor_key="sku|seller",
        metrics={"delta": -200, "delta_percent": -20},
    )

    assert score_change(change) >= 90


def test_score_trend_uses_history_length() -> None:
    trend = MarketTrend(
        sku="SKU-1",
        competitor_key="sku|seller",
        metric="review_count",
        direction="UP",
        first_value=100,
        last_value=150,
        delta=50,
        delta_percent=50,
        snapshot_count=3,
    )

    assert score_trend(trend) >= 90
