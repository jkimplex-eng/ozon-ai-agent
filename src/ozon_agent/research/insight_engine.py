from __future__ import annotations

from ozon_agent.research.models import (
    MarketplaceComparison,
    PricePosition,
    ResearchInsight,
    ResearchInsightType,
)


def detect_research_insights(comparisons: list[MarketplaceComparison]) -> list[ResearchInsight]:
    insights: list[ResearchInsight] = []
    for comparison in comparisons:
        insights.extend(_detect_for_comparison(comparison))
    return sorted(insights, key=lambda item: (item.sku, item.insight_type.value))


def _detect_for_comparison(comparison: MarketplaceComparison) -> list[ResearchInsight]:
    insights: list[ResearchInsight] = []
    source_urls = list(comparison.metrics.get("competitor_urls", []))
    if comparison.competitor_count == 0:
        insights.append(
            ResearchInsight(
                insight_type=ResearchInsightType.ASSORTMENT_GAP,
                sku=comparison.sku,
                severity="MEDIUM",
                reason="No competitor observations are available for this SKU.",
                metrics={"competitor_count": 0},
            )
        )
        return insights
    if comparison.price_position is PricePosition.ABOVE_MARKET:
        insights.append(
            ResearchInsight(
                insight_type=ResearchInsightType.PRICE_POSITION,
                sku=comparison.sku,
                severity="HIGH",
                reason="Own price is more than 10% above the competitor average.",
                metrics={
                    "own_price": comparison.own_price,
                    "avg_competitor_price": comparison.avg_competitor_price,
                },
                source_urls=source_urls,
            )
        )
    if comparison.review_gap is not None and comparison.review_gap <= -20:
        insights.append(
            ResearchInsight(
                insight_type=ResearchInsightType.REVIEW_GAP,
                sku=comparison.sku,
                severity="MEDIUM",
                reason="Own product has materially fewer reviews than observed competitors.",
                metrics={"review_gap": comparison.review_gap},
                source_urls=source_urls,
            )
        )
    if comparison.rating_gap is not None and comparison.rating_gap <= -0.3:
        insights.append(
            ResearchInsight(
                insight_type=ResearchInsightType.RATING_GAP,
                sku=comparison.sku,
                severity="MEDIUM",
                reason="Own rating is materially below observed competitor average.",
                metrics={"rating_gap": comparison.rating_gap},
                source_urls=source_urls,
            )
        )
    if comparison.own_price is None:
        insights.append(
            ResearchInsight(
                insight_type=ResearchInsightType.DATA_QUALITY,
                sku=comparison.sku,
                severity="LOW",
                reason="Own price is unavailable, so price positioning is unknown.",
                metrics={"price_position": comparison.price_position.value},
            )
        )
    return insights
