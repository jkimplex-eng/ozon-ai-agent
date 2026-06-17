from __future__ import annotations

from collections import Counter, defaultdict
from uuid import uuid4

from ozon_agent.research.insights.models import (
    MarketInsight,
    MarketInsightType,
    MarketOpportunity,
    MarketRisk,
    MarketSignal,
)
from ozon_agent.research.insights.priorities import priority_from_score
from ozon_agent.research.insights.scoring import score_change, score_count, score_trend
from ozon_agent.research.knowledge.history import compare_snapshots, detect_trends
from ozon_agent.research.knowledge.models import (
    MarketInsightRecord,
    MarketKnowledgeSnapshot,
    MarketTrend,
)


def detect_price_changes(changes: list[MarketInsightRecord]) -> list[MarketInsight]:
    insights: list[MarketInsight] = []
    for change in changes:
        if change.insight_type != "PRICE_CHANGED":
            continue
        delta = _float_metric(change, "delta") or 0.0
        insight_type = (
            MarketInsightType.PRICE_DROP if delta < 0 else MarketInsightType.PRICE_INCREASE
        )
        direction = "lowered" if delta < 0 else "raised"
        score = score_change(change)
        insights.append(
            _from_change(
                change,
                insight_type,
                f"Competitor {direction} price by {_format_percent(change)}",
                score,
            )
        )
    return insights


def detect_rating_changes(changes: list[MarketInsightRecord]) -> list[MarketInsight]:
    return [
        _from_change(
            change,
            MarketInsightType.RATING_CHANGE,
            f"Competitor rating changed by {_format_delta(change)}",
            score_change(change),
        )
        for change in changes
        if change.insight_type == "RATING_CHANGED"
    ]


def detect_review_changes(changes: list[MarketInsightRecord]) -> list[MarketInsight]:
    insights: list[MarketInsight] = []
    for change in changes:
        if change.insight_type != "REVIEWS_CHANGED":
            continue
        delta = _float_metric(change, "delta") or 0.0
        insight_type = (
            MarketInsightType.REVIEW_SURGE if delta > 0 else MarketInsightType.REVIEW_DROP
        )
        verb = "gained" if delta > 0 else "lost"
        insights.append(
            _from_change(
                change,
                insight_type,
                f"Competitor {verb} {abs(int(delta))} reviews",
                score_change(change),
            )
        )
    return insights


def detect_competitor_presence(changes: list[MarketInsightRecord]) -> list[MarketInsight]:
    mapped = {
        "NEW_COMPETITOR": MarketInsightType.NEW_COMPETITOR,
        "COMPETITOR_DISAPPEARED": MarketInsightType.COMPETITOR_DISAPPEARED,
    }
    insights: list[MarketInsight] = []
    for change in changes:
        insight_type = mapped.get(change.insight_type)
        if insight_type is None:
            continue
        score = score_count(1, base=45.0)
        insights.append(_from_change(change, insight_type, change.message, score))
    return insights


def detect_assortment_gaps(snapshot: MarketKnowledgeSnapshot) -> list[MarketInsight]:
    values_by_attribute: dict[str, set[str]] = defaultdict(set)
    for observation in snapshot.observations:
        for key in ("size", "brand"):
            value = observation.attributes.get(key)
            if value:
                values_by_attribute[key].add(str(value))
    insights: list[MarketInsight] = []
    for attribute, values in values_by_attribute.items():
        if len(values) < 2:
            continue
        score = score_count(len(values), base=20.0)
        priority = priority_from_score(score)
        values_text = ", ".join(sorted(values)[:6])
        insight_type = MarketInsightType.ASSORTMENT_GAP
        signal = MarketSignal(
            signal_type=insight_type,
            sku="category",
            message=f"Competitors cover {attribute} options: {values_text}",
            score=score,
            priority=priority,
            metrics={"attribute": attribute, "values": sorted(values)},
            snapshot_id=snapshot.id,
        )
        insights.append(
            MarketInsight.now(
                insight_id=_new_id(),
                insight_type=insight_type,
                sku="category",
                message=f"Assortment gap detected for {attribute}: {values_text}",
                score=score,
                priority=priority,
                signals=[signal],
                opportunities=[
                    MarketOpportunity(
                        opportunity_type="ASSORTMENT_COVERAGE",
                        sku="category",
                        message=f"Review missing {attribute} coverage: {values_text}",
                        score=score,
                        priority=priority,
                        metrics={"attribute": attribute, "values": sorted(values)},
                    )
                ],
                metrics={"attribute": attribute, "values": sorted(values)},
                snapshot_id=snapshot.id,
            )
        )
    return insights


def detect_category_pressure(
    changes: list[MarketInsightRecord],
    current: MarketKnowledgeSnapshot,
) -> list[MarketInsight]:
    pressure_events = [
        change
        for change in changes
        if change.insight_type in {"PRICE_CHANGED", "NEW_COMPETITOR"}
    ]
    if len(pressure_events) < 2 and len(current.observations) < 4:
        return []
    score = score_count(len(pressure_events) + len(current.observations), base=25.0)
    priority = priority_from_score(score)
    signal = MarketSignal(
        signal_type=MarketInsightType.CATEGORY_PRESSURE,
        sku="category",
        message="Competitive pressure increased in the observed category",
        score=score,
        priority=priority,
        metrics={
            "pressure_events": len(pressure_events),
            "competitor_count": len(current.observations),
        },
        snapshot_id=current.id,
    )
    return [
        MarketInsight.now(
            insight_id=_new_id(),
            insight_type=MarketInsightType.CATEGORY_PRESSURE,
            sku="category",
            message="Competitive pressure increased in the observed category",
            score=score,
            priority=priority,
            signals=[signal],
            risks=[
                MarketRisk(
                    risk_type="COMPETITIVE_PRESSURE",
                    sku="category",
                    message="Higher competitor count or price movement may pressure positions",
                    score=score,
                    priority=priority,
                    metrics=signal.metrics,
                )
            ],
            metrics=signal.metrics,
            snapshot_id=current.id,
        )
    ]


def detect_market_trend_signals(trends: list[MarketTrend]) -> list[MarketInsight]:
    insights: list[MarketInsight] = []
    for trend in trends:
        if trend.metric == "review_count" and trend.delta > 0:
            insight_type = MarketInsightType.MARKET_GROWTH_SIGNAL
            message = f"Review growth signal: competitor reviews grew by {trend.delta:.0f}"
        elif trend.metric == "price" and trend.delta < 0:
            insight_type = MarketInsightType.MARKET_DECLINE_SIGNAL
            message = f"Market price decline signal: competitor price moved down {trend.delta:.2f}"
        else:
            continue
        score = score_trend(trend)
        priority = priority_from_score(score)
        signal = MarketSignal(
            signal_type=insight_type,
            sku=trend.sku,
            message=message,
            score=score,
            priority=priority,
            metrics={
                "metric": trend.metric,
                "delta": trend.delta,
                "delta_percent": trend.delta_percent,
                "snapshot_count": trend.snapshot_count,
            },
            competitor_key=trend.competitor_key,
        )
        insights.append(
            MarketInsight.now(
                insight_id=_new_id(),
                insight_type=insight_type,
                sku=trend.sku,
                message=message,
                score=score,
                priority=priority,
                signals=[signal],
                metrics=signal.metrics,
                competitor_key=trend.competitor_key,
            )
        )
    return insights


def detect_all_insights(snapshots: list[MarketKnowledgeSnapshot]) -> list[MarketInsight]:
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.captured_at)
    if not ordered:
        return []
    changes = compare_snapshots(ordered[-2], ordered[-1]) if len(ordered) >= 2 else []
    current = ordered[-1]
    insights = [
        *detect_price_changes(changes),
        *detect_rating_changes(changes),
        *detect_review_changes(changes),
        *detect_competitor_presence(changes),
        *detect_assortment_gaps(current),
        *detect_category_pressure(changes, current),
        *detect_market_trend_signals(detect_trends(ordered)),
    ]
    return sorted(insights, key=lambda item: (-item.score, item.insight_type.value, item.sku))


def detect_risk_candidates(insights: list[MarketInsight]) -> list[MarketRisk]:
    risks: list[MarketRisk] = []
    for insight in insights:
        if insight.insight_type in {
            MarketInsightType.PRICE_DROP,
            MarketInsightType.NEW_COMPETITOR,
            MarketInsightType.CATEGORY_PRESSURE,
            MarketInsightType.MARKET_DECLINE_SIGNAL,
        }:
            risks.append(
                MarketRisk(
                    risk_type=_risk_type(insight),
                    sku=insight.sku,
                    message=_risk_message(insight),
                    score=insight.score,
                    priority=insight.priority,
                    metrics=insight.metrics,
                )
            )
    return sorted(risks, key=lambda item: -item.score)


def detect_opportunity_candidates(insights: list[MarketInsight]) -> list[MarketOpportunity]:
    opportunities: list[MarketOpportunity] = []
    for insight in insights:
        if insight.insight_type in {
            MarketInsightType.ASSORTMENT_GAP,
            MarketInsightType.COMPETITOR_DISAPPEARED,
            MarketInsightType.MARKET_GROWTH_SIGNAL,
        }:
            opportunities.append(
                MarketOpportunity(
                    opportunity_type=_opportunity_type(insight),
                    sku=insight.sku,
                    message=_opportunity_message(insight),
                    score=insight.score,
                    priority=insight.priority,
                    metrics=insight.metrics,
                )
            )
    return sorted(opportunities, key=lambda item: -item.score)


def category_counts(insights: list[MarketInsight]) -> Counter[str]:
    return Counter(insight.insight_type.value for insight in insights)


def _from_change(
    change: MarketInsightRecord,
    insight_type: MarketInsightType,
    message: str,
    score: float,
) -> MarketInsight:
    priority = priority_from_score(score)
    signal = MarketSignal(
        signal_type=insight_type,
        sku=change.sku,
        message=message,
        score=score,
        priority=priority,
        metrics=dict(change.metrics),
        competitor_key=change.competitor_key,
        snapshot_id=change.current_snapshot_id,
        previous_snapshot_id=change.previous_snapshot_id,
    )
    return MarketInsight.now(
        insight_id=_new_id(),
        insight_type=insight_type,
        sku=change.sku,
        message=message,
        score=score,
        priority=priority,
        signals=[signal],
        metrics=dict(change.metrics),
        snapshot_id=change.current_snapshot_id,
        previous_snapshot_id=change.previous_snapshot_id,
        competitor_key=change.competitor_key,
    )


def _float_metric(change: MarketInsightRecord, key: str) -> float | None:
    value = change.metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent(change: MarketInsightRecord) -> str:
    delta_percent = _float_metric(change, "delta_percent")
    if delta_percent is None:
        return _format_delta(change)
    return f"{abs(delta_percent):.1f}%"


def _format_delta(change: MarketInsightRecord) -> str:
    delta = _float_metric(change, "delta") or 0.0
    return f"{delta:.2f}"


def _risk_type(insight: MarketInsight) -> str:
    if insight.insight_type is MarketInsightType.PRICE_DROP:
        return "PRICE_WAR"
    if insight.insight_type is MarketInsightType.NEW_COMPETITOR:
        return "POSITION_LOSS"
    if insight.insight_type is MarketInsightType.CATEGORY_PRESSURE:
        return "COMPETITIVE_PRESSURE"
    return "MARKET_DECLINE"


def _risk_message(insight: MarketInsight) -> str:
    if insight.insight_type is MarketInsightType.PRICE_DROP:
        return "High risk of price war from competitor price cuts"
    if insight.insight_type is MarketInsightType.NEW_COMPETITOR:
        return "Risk of position loss from a new competitor"
    if insight.insight_type is MarketInsightType.CATEGORY_PRESSURE:
        return "Competitive pressure is rising in the category"
    return "Market decline signal detected"


def _opportunity_type(insight: MarketInsight) -> str:
    if insight.insight_type is MarketInsightType.ASSORTMENT_GAP:
        return "ASSORTMENT_COVERAGE"
    if insight.insight_type is MarketInsightType.COMPETITOR_DISAPPEARED:
        return "OPEN_SLOT"
    return "MARKET_GROWTH"


def _opportunity_message(insight: MarketInsight) -> str:
    if insight.insight_type is MarketInsightType.ASSORTMENT_GAP:
        return "Assortment coverage gap can be reviewed"
    if insight.insight_type is MarketInsightType.COMPETITOR_DISAPPEARED:
        return "Competitor disappeared, leaving a possible open slot"
    return "Market growth signal can inform future recommendations"


def _new_id() -> str:
    return f"market-insight-{uuid4().hex[:12]}"
