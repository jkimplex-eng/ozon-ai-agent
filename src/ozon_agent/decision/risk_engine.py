from __future__ import annotations

from ozon_agent.decision.models import (
    DecisionFeature,
    Opportunity,
    RecommendationAction,
    RiskLevel,
    RiskScore,
)


def score_risk(
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
    action: RecommendationAction | None = None,
) -> RiskScore:
    score = 0.2
    reasons: list[str] = []

    if feature.gross_profit_estimate is not None and feature.gross_profit_estimate < 0:
        score += 0.25
        reasons.append("negative gross profit estimate")

    if feature.stockout_probability is not None and feature.stockout_probability >= 0.6:
        score += 0.15
        reasons.append("elevated stockout probability")

    if not feature.has_forecast:
        score += 0.1
        reasons.append("forecast unavailable")

    if feature.ranking_trend is not None and feature.ranking_trend > 0:
        score += 0.1
        reasons.append("ranking is deteriorating")

    if feature.sample_size < 3 or feature.sales_rows_matched <= 0 or feature.cogs_per_unit is None:
        score += 0.15
        reasons.append("data quality is limited")

    if opportunity is not None and opportunity.impact_score >= 0.8:
        score += 0.1
        reasons.append("high-severity opportunity")

    score += _action_risk_adjustment(feature, action, reasons)

    bounded_score = min(max(score, 0.0), 1.0)
    return RiskScore(
        level=_risk_level_from_score(bounded_score), score=bounded_score, reasons=reasons
    )


def _risk_level_from_score(score: float) -> RiskLevel:
    if score >= 0.85:
        return RiskLevel.CRITICAL
    if score >= 0.65:
        return RiskLevel.HIGH
    if score >= 0.4:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _action_risk_adjustment(
    feature: DecisionFeature,
    action: RecommendationAction | None,
    reasons: list[str],
) -> float:
    if action is None:
        return 0.0
    if action is RecommendationAction.INCREASE_BUDGET:
        if feature.roas < 3.0:
            reasons.append("budget increase on modest ROAS")
            return 0.15
        return 0.05
    if action is RecommendationAction.DECREASE_BUDGET:
        if feature.roas > 3.5:
            reasons.append("budget cut may constrain efficient campaign")
            return 0.15
        return 0.05
    if action is RecommendationAction.PAUSE_CAMPAIGN:
        reasons.append("pause decision can sharply reduce traffic")
        return 0.2
    if action is RecommendationAction.INCREASE_STOCK:
        if not feature.has_forecast:
            reasons.append("restock without forecast support")
            return 0.2
        return 0.1
    if action is RecommendationAction.INCREASE_PRICE:
        if feature.sales_trend_pct < 0:
            reasons.append("price increase during declining sales")
            return 0.2
        return 0.1
    if action is RecommendationAction.DECREASE_PRICE:
        if feature.gross_margin_pct is not None and feature.gross_margin_pct < 20:
            reasons.append("price cut on thin margin")
            return 0.2
        return 0.1
    if action in {RecommendationAction.IMPROVE_CONTENT, RecommendationAction.BOOST_REVIEWS}:
        return 0.05
    return 0.0
