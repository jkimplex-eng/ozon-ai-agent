from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ozon_agent.knowledge.models import KnowledgeRule

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


def rule_matches(
    rule: KnowledgeRule,
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
    market_context: MarketContext | None = None,
) -> bool:
    context = market_context or _EmptyMarketContext()
    signals = {signal.lower() for signal in rule.signals}
    if "missing_title_query" in signals:
        return not feature.product_name or bool(
            feature.supporting_metrics.get("missing_high_frequency_query")
        )
    if "missing_characteristic" in signals:
        return bool(feature.supporting_metrics.get("missing_characteristics"))
    if "low_ctr" in signals:
        return feature.ctr > 0 and feature.ctr < 2.0
    if "high_ctr_low_cr" in signals:
        return feature.ctr >= 2.5 and _conversion_rate(feature) < 1.5
    if "low_cr" in signals:
        return feature.clicks > 0 and _conversion_rate(feature) < 1.5
    if "stock_risk" in signals:
        return (feature.stock_days is not None and feature.stock_days <= 7) or (
            feature.stockout_probability is not None and feature.stockout_probability >= 0.6
        )
    if "price_above_market" in signals:
        return context.price_pressure == "HIGH"
    if "review_pressure" in signals:
        return context.review_pressure == "HIGH"
    if "ranking_drop" in signals:
        return feature.ranking_trend is not None and feature.ranking_trend > 0
    if "experiment_candidate" in signals:
        return opportunity is not None
    return _fallback_text_match(rule, feature, opportunity, context)


def _fallback_text_match(
    rule: KnowledgeRule,
    feature: DecisionFeature,
    opportunity: Opportunity | None,
    context: MarketContext | _EmptyMarketContext,
) -> bool:
    text = " ".join(
        [
            rule.title,
            rule.condition,
            rule.recommendation,
            rule.rationale,
            *(rule.signals),
        ]
    ).lower()
    if "ctr" in text and feature.ctr > 0:
        return True
    if "price" in text and (feature.price > 0 or context.price_pressure != "LOW"):
        return True
    if "review" in text and (feature.review_count > 0 or context.review_pressure != "LOW"):
        return True
    if "stock" in text and feature.has_stock:
        return True
    if "experiment" in text and opportunity is not None:
        return True
    return False


def _conversion_rate(feature: DecisionFeature) -> float:
    if feature.clicks <= 0:
        return 0.0
    numerator = feature.ad_orders if feature.ad_orders > 0 else feature.sales_quantity
    return numerator / feature.clicks * 100.0
