from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ozon_agent.knowledge.models import KnowledgeRecommendation, KnowledgeRule
from ozon_agent.knowledge.repository import load_rules, search_rules
from ozon_agent.knowledge.rules import rule_matches

if TYPE_CHECKING:
    from ozon_agent.decision.market_context import MarketContext
    from ozon_agent.decision.models import DecisionFeature, Opportunity


@dataclass(frozen=True)
class _EmptyMarketContext:
    price_pressure: str = "LOW"
    competitor_growth: str = "LOW"
    review_pressure: str = "LOW"
    rating_pressure: str = "LOW"
    market_risk_score: float = 0.0
    market_opportunity_score: float = 0.0
    market_signals: list[dict[str, Any]] = field(default_factory=list)
    market_risks: list[dict[str, Any]] = field(default_factory=list)
    market_opportunities: list[dict[str, Any]] = field(default_factory=list)


def find_relevant_rules(
    query: str,
    root: str | Path | None = None,
) -> list[KnowledgeRule]:
    return search_rules(query, root=root)


def evaluate_rules(
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
    market_context: MarketContext | None = None,
    root: str | Path | None = None,
) -> list[KnowledgeRecommendation]:
    recommendations: list[KnowledgeRecommendation] = []
    for rule in load_rules(root=root):
        if not rule_matches(rule, feature, opportunity, market_context):
            continue
        recommendations.append(_recommendation_from_rule(rule, feature, market_context))
    return recommendations


def build_knowledge_context(
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
    market_context: MarketContext | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    recommendations = evaluate_rules(
        feature=feature,
        opportunity=opportunity,
        market_context=market_context,
        root=root,
    )
    return {
        "knowledge_signals": [
            {
                "domain": item.domain.value,
                "title": item.title,
                "signal": item.signal,
                "reason": item.reason,
                "priority": item.priority,
            }
            for item in recommendations
        ],
        "knowledge_rules": [
            {
                "rule_id": item.rule_id,
                "domain": item.domain.value,
                "title": item.title,
            }
            for item in recommendations
        ],
        "knowledge_sources": [
            {
                "name": item.source.name if item.source else "",
                "path": item.source.path if item.source else "",
                "type": item.source.source_type if item.source else "",
            }
            for item in recommendations
            if item.source is not None
        ],
        "knowledge_recommendations": recommendations,
    }


def _recommendation_from_rule(
    rule: KnowledgeRule,
    feature: DecisionFeature,
    market_context: MarketContext | None,
) -> KnowledgeRecommendation:
    context = market_context or _EmptyMarketContext()
    return KnowledgeRecommendation(
        rule_id=rule.id,
        domain=rule.domain,
        title=rule.title,
        signal=rule.recommendation,
        reason=_reason(rule, feature, context),
        source=rule.source,
        priority=str(rule.metadata.get("priority", "MEDIUM")),
        metadata={
            "sku": feature.sku,
            "price_pressure": context.price_pressure,
            "review_pressure": context.review_pressure,
            "competitor_growth": context.competitor_growth,
        },
    )


def _reason(
    rule: KnowledgeRule,
    feature: DecisionFeature,
    context: MarketContext | _EmptyMarketContext,
) -> str:
    parts = [rule.rationale]
    if feature.ctr > 0:
        parts.append(f"CTR={feature.ctr:.2f}%")
    if context.price_pressure != "LOW":
        parts.append(f"price pressure={context.price_pressure}")
    if context.review_pressure != "LOW":
        parts.append(f"review pressure={context.review_pressure}")
    return "; ".join(part for part in parts if part)
