from __future__ import annotations

from ozon_agent.decision.confidence_engine import score_confidence
from ozon_agent.decision.market_context import MarketContext, build_market_context
from ozon_agent.decision.models import (
    DecisionFeature,
    Opportunity,
    OpportunityType,
    Recommendation,
    RecommendationAction,
    utc_now_iso,
)
from ozon_agent.decision.opportunity_detector import detect_all_opportunities
from ozon_agent.decision.risk_engine import score_risk
from ozon_agent.knowledge.engine import build_knowledge_context


def generate_recommendation(
    feature: DecisionFeature,
    opportunity: Opportunity,
    market_context: MarketContext | None = None,
) -> Recommendation:
    context = market_context or MarketContext()
    action = _map_action(feature, opportunity)
    confidence = score_confidence(feature, opportunity)
    risk = score_risk(feature, opportunity, action)
    knowledge_context = build_knowledge_context(feature, opportunity, context)
    from ozon_agent.learning.learning_engine import generate_recommendation_support

    learning_context = generate_recommendation_support(feature, opportunity, action)
    from ozon_agent.memory.engine import generate_memory_support

    memory_context = generate_memory_support(feature, opportunity, action)
    return Recommendation(
        sku=feature.sku,
        action=action,
        expected_effect=_expected_effect(feature, opportunity, action, context),
        confidence=confidence,
        risk=risk,
        reason=_enriched_reason(
            opportunity.reason,
            context,
            knowledge_context,
            learning_context,
            memory_context,
        ),
        supporting_metrics={
            **opportunity.metrics,
            "price": feature.price,
            "sales_quantity": feature.sales_quantity,
            "sales_revenue": feature.sales_revenue,
            "gross_profit_estimate": feature.gross_profit_estimate,
            "market_context": {
                "price_pressure": context.price_pressure,
                "competitor_growth": context.competitor_growth,
                "review_pressure": context.review_pressure,
                "rating_pressure": context.rating_pressure,
                "market_risk_score": context.market_risk_score,
                "market_opportunity_score": context.market_opportunity_score,
            },
        },
        created_at=utc_now_iso(),
        opportunity_type=opportunity.opportunity_type,
        campaign_id=feature.campaign_id,
        impact_score=opportunity.impact_score,
        market_signals=context.market_signals,
        market_risks=context.market_risks,
        market_opportunities=context.market_opportunities,
        knowledge_signals=knowledge_context["knowledge_signals"],
        knowledge_rules=knowledge_context["knowledge_rules"],
        knowledge_sources=knowledge_context["knowledge_sources"],
        learning_signals=learning_context["learning_signals"],
        similar_experiments=learning_context["similar_experiments"],
        historical_success_rate=float(learning_context["historical_success_rate"]),
        learning_insights=learning_context["learning_insights"],
        recommended_confidence=float(learning_context["recommended_confidence"]),
        memory_signals=memory_context["memory_signals"],
        similar_recommendations=memory_context["similar_recommendations"],
        historical_action_success_rate=float(
            memory_context["historical_action_success_rate"]
        ),
        memory_insights=memory_context["memory_insights"],
        memory_confidence=float(memory_context["memory_confidence"]),
    )


def generate_recommendations(
    features: list[DecisionFeature],
    limit: int | None = None,
    market_contexts: dict[str, MarketContext] | None = None,
    include_market_context: bool = True,
) -> list[Recommendation]:
    feature_lookup = {(feature.sku, feature.campaign_id): feature for feature in features}
    recommendations: list[Recommendation] = []
    for opportunity in detect_all_opportunities(features):
        feature = feature_lookup.get((opportunity.sku, opportunity.campaign_id))
        if feature is None:
            continue
        context = _context_for_feature(feature, market_contexts, include_market_context)
        recommendations.append(generate_recommendation(feature, opportunity, context))

    recommendations.sort(
        key=lambda item: (-item.impact_score, -item.confidence.score, item.risk.score)
    )
    if limit is None:
        return recommendations
    return recommendations[:limit]


def _map_action(feature: DecisionFeature, opportunity: Opportunity) -> RecommendationAction:
    if opportunity.opportunity_type is OpportunityType.STOCK_RISK:
        return RecommendationAction.INCREASE_STOCK
    if opportunity.opportunity_type is OpportunityType.AD_GROWTH:
        return RecommendationAction.INCREASE_BUDGET
    if opportunity.opportunity_type is OpportunityType.AD_WASTE:
        if feature.ad_orders <= 0 or feature.ad_revenue <= 0:
            return RecommendationAction.PAUSE_CAMPAIGN
        return RecommendationAction.DECREASE_BUDGET
    if opportunity.opportunity_type is OpportunityType.PRICE_MARGIN:
        return RecommendationAction.INCREASE_PRICE
    if opportunity.opportunity_type is OpportunityType.PRICE_CONVERSION:
        return RecommendationAction.DECREASE_PRICE
    if opportunity.opportunity_type is OpportunityType.RANKING_RISK:
        if feature.review_count < 20 or (
            feature.review_rating is not None and feature.review_rating < 4.5
        ):
            return RecommendationAction.BOOST_REVIEWS
        return RecommendationAction.IMPROVE_CONTENT
    if opportunity.opportunity_type is OpportunityType.RANKING_GROWTH:
        return RecommendationAction.INCREASE_BUDGET
    return RecommendationAction.NO_ACTION


def _expected_effect(
    feature: DecisionFeature,
    opportunity: Opportunity,
    action: RecommendationAction,
    market_context: MarketContext,
) -> str:
    market_suffix = _market_expected_effect_suffix(market_context)
    if action is RecommendationAction.INCREASE_STOCK:
        return f"reduce stockout risk and preserve revenue continuity{market_suffix}"
    if action is RecommendationAction.INCREASE_BUDGET:
        return f"capture incremental demand from efficient traffic{market_suffix}"
    if action is RecommendationAction.DECREASE_BUDGET:
        return f"reduce inefficient ad spend and improve unit economics{market_suffix}"
    if action is RecommendationAction.PAUSE_CAMPAIGN:
        return f"stop loss-making spend until attribution or conversion improves{market_suffix}"
    if action is RecommendationAction.INCREASE_PRICE:
        return f"improve margin while demand remains stable{market_suffix}"
    if action is RecommendationAction.DECREASE_PRICE:
        return f"restore conversion by lowering price pressure{market_suffix}"
    if action is RecommendationAction.IMPROVE_CONTENT:
        return f"improve listing quality to protect ranking and conversion{market_suffix}"
    if action is RecommendationAction.BOOST_REVIEWS:
        return f"improve social proof to stabilize ranking{market_suffix}"
    return (
        f"monitor {opportunity.opportunity_type.value.lower()} without immediate action"
        f"{market_suffix}"
    )


def _context_for_feature(
    feature: DecisionFeature,
    market_contexts: dict[str, MarketContext] | None,
    include_market_context: bool,
) -> MarketContext:
    if market_contexts is not None:
        return market_contexts.get(feature.sku, market_contexts.get("category", MarketContext()))
    if not include_market_context:
        return MarketContext()
    return build_market_context(feature.sku)


def _enriched_reason(
    reason: str,
    market_context: MarketContext,
    knowledge_context: dict[str, object],
    learning_context: dict[str, object],
    memory_context: dict[str, object],
) -> str:
    market_reasons: list[str] = []
    if market_context.price_pressure == "HIGH":
        market_reasons.append("market price pressure is high")
    if market_context.competitor_growth == "HIGH":
        market_reasons.append("new competitor pressure is high")
    if market_context.review_pressure == "HIGH":
        market_reasons.append("review pressure is high")
    if market_context.rating_pressure == "HIGH":
        market_reasons.append("rating pressure is high")
    knowledge_rules = knowledge_context.get("knowledge_rules", [])
    if isinstance(knowledge_rules, list) and knowledge_rules:
        rule_titles = [
            str(item.get("title", ""))
            for item in knowledge_rules[:3]
            if isinstance(item, dict)
        ]
        if rule_titles:
            market_reasons.append(f"knowledge rules: {', '.join(rule_titles)}")
    learning_signals = learning_context.get("learning_signals", [])
    if isinstance(learning_signals, list) and learning_signals:
        signal = learning_signals[0]
        if isinstance(signal, dict):
            market_reasons.append(str(signal.get("message", "experiment learning available")))
    memory_signals = memory_context.get("memory_signals", [])
    if isinstance(memory_signals, list) and memory_signals:
        signal = memory_signals[0]
        if isinstance(signal, dict):
            market_reasons.append(str(signal.get("message", "recommendation memory available")))
    if not market_reasons:
        return reason
    return f"{reason}; market context: {', '.join(market_reasons)}"


def _market_expected_effect_suffix(market_context: MarketContext) -> str:
    checks: list[str] = []
    if market_context.price_pressure == "HIGH":
        checks.append("price")
    if market_context.review_pressure == "HIGH":
        checks.append("reviews")
    if market_context.competitor_growth == "HIGH":
        checks.append("competitive position")
    if not checks:
        return ""
    return f" while reviewing {'/'.join(checks)} pressure"
