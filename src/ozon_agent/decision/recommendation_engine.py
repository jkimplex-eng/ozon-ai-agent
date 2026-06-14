from __future__ import annotations

from ozon_agent.decision.confidence_engine import score_confidence
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


def generate_recommendation(feature: DecisionFeature, opportunity: Opportunity) -> Recommendation:
    action = _map_action(feature, opportunity)
    confidence = score_confidence(feature, opportunity)
    risk = score_risk(feature, opportunity, action)
    return Recommendation(
        sku=feature.sku,
        action=action,
        expected_effect=_expected_effect(feature, opportunity, action),
        confidence=confidence,
        risk=risk,
        reason=opportunity.reason,
        supporting_metrics={
            **opportunity.metrics,
            "price": feature.price,
            "sales_quantity": feature.sales_quantity,
            "sales_revenue": feature.sales_revenue,
            "gross_profit_estimate": feature.gross_profit_estimate,
        },
        created_at=utc_now_iso(),
        opportunity_type=opportunity.opportunity_type,
        campaign_id=feature.campaign_id,
        impact_score=opportunity.impact_score,
    )


def generate_recommendations(
    features: list[DecisionFeature],
    limit: int | None = None,
) -> list[Recommendation]:
    feature_lookup = {(feature.sku, feature.campaign_id): feature for feature in features}
    recommendations: list[Recommendation] = []
    for opportunity in detect_all_opportunities(features):
        feature = feature_lookup.get((opportunity.sku, opportunity.campaign_id))
        if feature is None:
            continue
        recommendations.append(generate_recommendation(feature, opportunity))

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
) -> str:
    if action is RecommendationAction.INCREASE_STOCK:
        return "reduce stockout risk and preserve revenue continuity"
    if action is RecommendationAction.INCREASE_BUDGET:
        return "capture incremental demand from efficient traffic"
    if action is RecommendationAction.DECREASE_BUDGET:
        return "reduce inefficient ad spend and improve unit economics"
    if action is RecommendationAction.PAUSE_CAMPAIGN:
        return "stop loss-making spend until attribution or conversion improves"
    if action is RecommendationAction.INCREASE_PRICE:
        return "improve margin while demand remains stable"
    if action is RecommendationAction.DECREASE_PRICE:
        return "restore conversion by lowering price pressure"
    if action is RecommendationAction.IMPROVE_CONTENT:
        return "improve listing quality to protect ranking and conversion"
    if action is RecommendationAction.BOOST_REVIEWS:
        return "improve social proof to stabilize ranking"
    return f"monitor {opportunity.opportunity_type.value.lower()} without immediate action"
