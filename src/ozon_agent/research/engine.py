from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.comparator import compare_marketplace
from ozon_agent.research.insight_engine import detect_research_insights
from ozon_agent.research.models import (
    MarketplaceResearchReport,
    ResearchObservation,
)
from ozon_agent.research.source_registry import list_sources


def generate_marketplace_research_report(
    query: str,
    own_observations: list[ResearchObservation] | None = None,
    competitor_observations: list[ResearchObservation] | None = None,
) -> MarketplaceResearchReport:
    own_rows = own_observations or []
    competitor_rows = competitor_observations or []
    comparisons = compare_marketplace(own_rows, competitor_rows)
    insights = detect_research_insights(comparisons)
    return MarketplaceResearchReport(
        query=query.strip(),
        generated_at=datetime.now(UTC),
        summary={
            "own_observations": len(own_rows),
            "competitor_observations": len(competitor_rows),
            "compared_skus": len(comparisons),
            "insights": len(insights),
            "execution": "disabled",
        },
        comparisons=comparisons,
        insights=insights,
        sources=list_sources(),
    )
