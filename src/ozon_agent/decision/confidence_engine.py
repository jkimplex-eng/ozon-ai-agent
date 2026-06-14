from __future__ import annotations

from ozon_agent.decision.models import (
    ConfidenceLevel,
    ConfidenceScore,
    DecisionFeature,
    Opportunity,
)


def score_confidence(
    feature: DecisionFeature,
    opportunity: Opportunity | None = None,
) -> ConfidenceScore:
    score = 0.45
    reasons: list[str] = []

    if feature.data_freshness_days <= 3:
        score += 0.2
        reasons.append("fresh data")
    elif feature.data_freshness_days <= 7:
        score += 0.1
        reasons.append("recent data")
    else:
        score -= 0.15
        reasons.append("stale data")

    if feature.sample_size >= 10:
        score += 0.15
        reasons.append("strong sample size")
    elif feature.sample_size >= 3:
        score += 0.05
        reasons.append("moderate sample size")
    else:
        score -= 0.1
        reasons.append("small sample size")

    if feature.has_forecast:
        score += 0.1
        reasons.append("forecast available")
    else:
        reasons.append("forecast unavailable")

    if _metrics_consistent(feature):
        score += 0.1
        reasons.append("metrics are internally consistent")
    else:
        score -= 0.1
        reasons.append("metrics have weak consistency")

    if feature.sales_rows_matched <= 0:
        score -= 0.2
        reasons.append("sales data missing")
    if feature.cogs_per_unit is None:
        score -= 0.15
        reasons.append("COGS missing")
    if feature.has_stock is False:
        score -= 0.05
        reasons.append("stock data missing")
    if opportunity is not None and opportunity.impact_score >= 0.7 and feature.sample_size < 3:
        score -= 0.05
        reasons.append("high-impact signal rests on thin evidence")

    bounded_score = min(max(score, 0.0), 1.0)
    return ConfidenceScore(
        score=bounded_score,
        level=_level_from_score(bounded_score),
        reasons=reasons,
    )


def _level_from_score(score: float) -> ConfidenceLevel:
    if score >= 0.75:
        return ConfidenceLevel.HIGH
    if score >= 0.45:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _metrics_consistent(feature: DecisionFeature) -> bool:
    if feature.ad_spend > 0 and feature.ad_revenue > 0 and feature.roas <= 0:
        return False
    if feature.ad_revenue > 0 and feature.sales_revenue > 0:
        ratio = feature.ad_revenue / feature.sales_revenue
        return 0.1 <= ratio <= 10.0
    if feature.sales_quantity > 0 and feature.price > 0 and feature.sales_revenue > 0:
        implied_revenue = feature.sales_quantity * feature.price
        if implied_revenue <= 0:
            return True
        delta = abs(implied_revenue - feature.sales_revenue) / implied_revenue
        return delta <= 0.5
    return feature.sales_rows_matched > 0 or feature.ad_spend > 0
