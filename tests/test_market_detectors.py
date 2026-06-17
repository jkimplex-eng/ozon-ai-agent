from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.insights.detectors import (
    detect_assortment_gaps,
    detect_competitor_presence,
    detect_market_trend_signals,
    detect_price_changes,
    detect_review_changes,
)
from ozon_agent.research.insights.models import MarketInsightType
from ozon_agent.research.knowledge.history import compare_snapshots, detect_trends
from ozon_agent.research.knowledge.models import MarketKnowledgeSnapshot
from ozon_agent.research.models import ResearchObservation


def test_price_drop_detection() -> None:
    changes = compare_snapshots(_snapshot("a", price=1290), _snapshot("b", price=1090))

    insights = detect_price_changes(changes)

    assert insights[0].insight_type is MarketInsightType.PRICE_DROP
    assert "lowered price" in insights[0].message


def test_review_surge_detection() -> None:
    changes = compare_snapshots(
        _snapshot("a", price=1000, reviews=500),
        _snapshot("b", price=1000, reviews=900),
    )

    insights = detect_review_changes(changes)

    assert insights[0].insight_type is MarketInsightType.REVIEW_SURGE
    assert "400 reviews" in insights[0].message


def test_new_competitor_detection() -> None:
    previous = _knowledge_snapshot("a", [])
    current = _knowledge_snapshot(
        "b",
        [ResearchObservation(sku="SKU-1", seller_name="New Seller", source_url="u")],
    )

    insights = detect_competitor_presence(compare_snapshots(previous, current))

    assert insights[0].insight_type is MarketInsightType.NEW_COMPETITOR


def test_assortment_gap_detection() -> None:
    snapshot = _knowledge_snapshot(
        "a",
        [
            ResearchObservation(sku="A", attributes={"size": "160x230"}),
            ResearchObservation(sku="B", attributes={"size": "200x300"}),
        ],
    )

    insights = detect_assortment_gaps(snapshot)

    assert insights[0].insight_type is MarketInsightType.ASSORTMENT_GAP
    assert "160x230" in insights[0].message


def test_market_growth_signal_from_review_trend() -> None:
    snapshots = [
        _snapshot("a", price=1000, reviews=100),
        _snapshot("b", price=1000, reviews=180),
    ]

    insights = detect_market_trend_signals(detect_trends(snapshots))

    assert any(item.insight_type is MarketInsightType.MARKET_GROWTH_SIGNAL for item in insights)


def _snapshot(snapshot_id: str, price: float, reviews: int = 10) -> MarketKnowledgeSnapshot:
    return _knowledge_snapshot(
        snapshot_id,
        [
            ResearchObservation(
                sku="SKU-1",
                seller_name="Seller A",
                source_url="https://example.test/a",
                price=price,
                review_count=reviews,
            )
        ],
    )


def _knowledge_snapshot(
    snapshot_id: str,
    observations: list[ResearchObservation],
) -> MarketKnowledgeSnapshot:
    return MarketKnowledgeSnapshot(
        id=snapshot_id,
        query="query",
        source_name="manual",
        captured_at=datetime(2026, 1, int(snapshot_id, 36) % 28 + 1, tzinfo=UTC),
        observations=observations,
    )
