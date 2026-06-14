from __future__ import annotations

from ozon_agent.decision.models import DecisionFeature, Opportunity, OpportunityType


def detect_stock_opportunities(features: list[DecisionFeature]) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for feature in features:
        reasons: list[str] = []
        impact = 0.0
        if feature.stockout_probability is not None and feature.stockout_probability >= 0.6:
            reasons.append(
                "stockout probability "
                f"{feature.stockout_probability:.2f} indicates likely depletion"
            )
            impact += min(feature.stockout_probability, 1.0) * 0.7
        if feature.stock_days is not None and feature.stock_days <= 7:
            reasons.append(f"stock days {feature.stock_days:.1f} is below safety threshold")
            impact += max(0.0, (7.0 - feature.stock_days) / 7.0) * 0.5
        if not reasons:
            continue
        opportunities.append(
            Opportunity(
                opportunity_type=OpportunityType.STOCK_RISK,
                sku=feature.sku,
                severity=_severity_from_score(impact),
                impact_score=min(impact, 1.0),
                reason="; ".join(reasons),
                metrics={
                    "stockout_probability": feature.stockout_probability,
                    "stock_days": feature.stock_days,
                    "current_stock": feature.current_stock,
                },
                campaign_id=feature.campaign_id,
            )
        )
    return opportunities


def detect_ad_opportunities(features: list[DecisionFeature]) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for feature in features:
        if feature.ad_spend <= 0:
            continue
        if feature.roas >= 4.0 and feature.drr > 0 and feature.drr <= 20.0:
            impact = min(feature.roas / 8.0, 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.AD_GROWTH,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"ROAS {feature.roas:.2f} and DRR {feature.drr:.2f}% "
                        "indicate efficient spend"
                    ),
                    metrics={"roas": feature.roas, "drr": feature.drr, "spend": feature.ad_spend},
                    campaign_id=feature.campaign_id,
                )
            )
            continue
        if feature.roas <= 1.5 and feature.drr >= 35.0:
            impact = min((feature.drr / 100.0) + max(0.0, 1.5 - feature.roas) / 2.0, 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.AD_WASTE,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"ROAS {feature.roas:.2f} and DRR {feature.drr:.2f}% "
                        "indicate wasteful spend"
                    ),
                    metrics={"roas": feature.roas, "drr": feature.drr, "spend": feature.ad_spend},
                    campaign_id=feature.campaign_id,
                )
            )
    return opportunities


def detect_price_opportunities(features: list[DecisionFeature]) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for feature in features:
        if feature.price <= 0:
            continue
        if (
            feature.gross_margin_pct is not None
            and feature.gross_margin_pct >= 35.0
            and feature.sales_quantity > 0
            and feature.sales_trend_pct >= -5.0
        ):
            impact = min(feature.gross_margin_pct / 100.0, 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.PRICE_MARGIN,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"gross margin {feature.gross_margin_pct:.2f}% is strong while sales trend "
                        f"{feature.sales_trend_pct:.2f}% is stable"
                    ),
                    metrics={
                        "gross_margin_pct": feature.gross_margin_pct,
                        "sales_trend_pct": feature.sales_trend_pct,
                        "price": feature.price,
                    },
                    campaign_id=feature.campaign_id,
                )
            )
            continue
        if feature.sales_trend_pct <= -10.0 and feature.price > 0:
            impact = min(abs(feature.sales_trend_pct) / 40.0, 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.PRICE_CONVERSION,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"sales trend {feature.sales_trend_pct:.2f}% is declining while "
                        "current price "
                        f"{feature.price:.2f} may be pressuring conversion"
                    ),
                    metrics={"sales_trend_pct": feature.sales_trend_pct, "price": feature.price},
                    campaign_id=feature.campaign_id,
                )
            )
    return opportunities


def detect_ranking_opportunities(features: list[DecisionFeature]) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for feature in features:
        if feature.ranking_position is None or feature.ranking_trend is None:
            continue
        conversion_rate = _conversion_rate(feature)
        if feature.ranking_trend > 0 and feature.ctr >= 2.5:
            impact = min((feature.ctr / 10.0) + min(feature.ranking_trend / 20.0, 0.5), 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.RANKING_RISK,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"ranking worsened by {feature.ranking_trend:.2f} positions despite CTR "
                        f"{feature.ctr:.2f}%"
                    ),
                    metrics={
                        "ranking_position": feature.ranking_position,
                        "ranking_trend": feature.ranking_trend,
                        "ctr": feature.ctr,
                    },
                    campaign_id=feature.campaign_id,
                )
            )
            continue
        if feature.ranking_position >= 20 and conversion_rate >= 3.0:
            impact = min((conversion_rate / 10.0) + min(feature.ranking_position / 100.0, 0.5), 1.0)
            opportunities.append(
                Opportunity(
                    opportunity_type=OpportunityType.RANKING_GROWTH,
                    sku=feature.sku,
                    severity=_severity_from_score(impact),
                    impact_score=impact,
                    reason=(
                        f"conversion {conversion_rate:.2f}% is healthy while ranking position "
                        f"{feature.ranking_position:.2f} remains weak"
                    ),
                    metrics={
                        "ranking_position": feature.ranking_position,
                        "conversion_rate": conversion_rate,
                        "ctr": feature.ctr,
                    },
                    campaign_id=feature.campaign_id,
                )
            )
    return opportunities


def detect_all_opportunities(features: list[DecisionFeature]) -> list[Opportunity]:
    opportunities = []
    opportunities.extend(detect_stock_opportunities(features))
    opportunities.extend(detect_ad_opportunities(features))
    opportunities.extend(detect_price_opportunities(features))
    opportunities.extend(detect_ranking_opportunities(features))
    return opportunities


def _severity_from_score(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _conversion_rate(feature: DecisionFeature) -> float:
    if feature.clicks <= 0:
        return 0.0
    numerator = feature.ad_orders if feature.ad_orders > 0 else feature.sales_quantity
    return numerator / feature.clicks * 100.0
