from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.knowledge.history import (
    build_history,
    compare_snapshots,
    detect_price_trend,
    detect_rating_trend,
    detect_review_trend,
    detect_trends,
)
from ozon_agent.research.knowledge.models import MarketKnowledgeSnapshot
from ozon_agent.research.models import ResearchObservation


def test_build_history_from_snapshots() -> None:
    snapshots = [_snapshot("a", 100, 4.4, 10), _snapshot("b", 110, 4.5, 12)]
    history = build_history(snapshots)
    assert len(history) == 2
    assert history[0].snapshot_id == "a"
    assert history[0].competitor_key == "sku-1|seller a|https://example.test/a"


def test_compare_snapshots_detects_metric_changes() -> None:
    previous = _snapshot("a", 100, 4.4, 10, available=True)
    current = _snapshot("b", 88, 4.1, 35, available=False)

    insight_types = {insight.insight_type for insight in compare_snapshots(previous, current)}

    assert "PRICE_CHANGED" in insight_types
    assert "RATING_CHANGED" in insight_types
    assert "REVIEWS_CHANGED" in insight_types
    assert "AVAILABILITY_CHANGED" in insight_types


def test_compare_snapshots_detects_new_and_disappeared_competitors() -> None:
    previous = _knowledge_snapshot(
        "a",
        [
            ResearchObservation(
                sku="SKU-1",
                seller_name="Old Seller",
                source_url="https://example.test/old",
                price=100,
            )
        ],
    )
    current = _knowledge_snapshot(
        "b",
        [
            ResearchObservation(
                sku="SKU-1",
                seller_name="New Seller",
                source_url="https://example.test/new",
                price=90,
            )
        ],
    )

    insight_types = {insight.insight_type for insight in compare_snapshots(previous, current)}

    assert "NEW_COMPETITOR" in insight_types
    assert "COMPETITOR_DISAPPEARED" in insight_types


def test_detect_metric_trends() -> None:
    snapshots = [
        _snapshot("a", 100, 4.0, 10),
        _snapshot("b", 95, 4.2, 30),
        _snapshot("c", 90, 4.4, 60),
    ]

    price_trends = detect_price_trend(snapshots)
    rating_trends = detect_rating_trend(snapshots)
    review_trends = detect_review_trend(snapshots)
    all_trends = detect_trends(snapshots)

    assert price_trends[0].direction == "DOWN"
    assert rating_trends[0].direction == "UP"
    assert review_trends[0].delta == 50
    assert {trend.metric for trend in all_trends} == {"price", "rating", "review_count"}


def _snapshot(
    snapshot_id: str,
    price: float,
    rating: float,
    reviews: int,
    available: bool | None = True,
) -> MarketKnowledgeSnapshot:
    return _knowledge_snapshot(
        snapshot_id,
        [
            ResearchObservation(
                sku="SKU-1",
                seller_name="Seller A",
                source_url="https://example.test/a",
                observed_at=datetime(2026, 1, int(snapshot_id, 36) % 28 + 1, tzinfo=UTC),
                price=price,
                rating=rating,
                review_count=reviews,
                available=available,
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
