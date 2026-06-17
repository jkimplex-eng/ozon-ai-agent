from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.decision.market_context import (
    build_market_context,
    load_market_insights,
    load_market_opportunities,
    load_market_risks,
)
from ozon_agent.research.knowledge.insight_store import save_insights
from ozon_agent.research.knowledge.models import MarketInsightRecord


def test_mapping_market_insights_to_context(tmp_path) -> None:
    save_insights(
        [
            _record("PRICE_DROP", "SKU-1", score=90, message="3 competitors dropped price"),
            _record("REVIEW_SURGE", "SKU-1", score=88, message="reviews surged"),
            _record("NEW_COMPETITOR", "SKU-1", score=70, message="new competitor"),
            _record("ASSORTMENT_GAP", "category", score=70, message="missing sizes"),
        ],
        storage_dir=tmp_path,
    )

    context = build_market_context("SKU-1", storage_dir=tmp_path)

    assert context.price_pressure == "HIGH"
    assert context.review_pressure == "HIGH"
    assert context.competitor_growth == "HIGH"
    assert context.market_risk_score >= 70
    assert context.market_opportunity_score >= 70
    assert len(context.market_signals) == 4


def test_load_market_slices(tmp_path) -> None:
    save_insights(
        [
            _record("PRICE_DROP", "SKU-1", score=90),
            _record("ASSORTMENT_GAP", "category", score=70),
        ],
        storage_dir=tmp_path,
    )

    assert len(load_market_insights(storage_dir=tmp_path)) == 2
    assert load_market_risks(storage_dir=tmp_path)
    assert load_market_opportunities(storage_dir=tmp_path)


def _record(
    insight_type: str,
    sku: str,
    score: float,
    message: str = "market insight",
) -> MarketInsightRecord:
    return MarketInsightRecord(
        id=f"{insight_type}-{sku}",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        insight_type=insight_type,
        sku=sku,
        message=message,
        severity="HIGH",
        metrics={"score": score, "priority": "HIGH"},
    )
