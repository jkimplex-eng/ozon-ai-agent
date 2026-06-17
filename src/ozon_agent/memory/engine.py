from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ozon_agent.approval.models import RecommendationOutcome, StoredRecommendation
from ozon_agent.decision.models import (
    DecisionFeature,
    Opportunity,
    Recommendation,
    RecommendationAction,
)
from ozon_agent.memory.models import (
    MemoryInsight,
    MemoryMatch,
    MemoryResult,
    RecommendationMemoryRecord,
    new_memory_id,
    utc_now_iso,
)
from ozon_agent.memory.repository import (
    list_memory_insights,
    list_memory_records,
    save_memory_insight,
    save_memory_record,
)
from ozon_agent.memory.similarity import find_similar_memory


def remember_recommendation(
    recommendation: Recommendation,
    outcome: RecommendationOutcome | None = None,
    source_recommendation_id: str | None = None,
    root: str | Path | None = None,
) -> RecommendationMemoryRecord:
    record = RecommendationMemoryRecord(
        id=new_memory_id("memory"),
        created_at=utc_now_iso(),
        sku=recommendation.sku,
        action=recommendation.action,
        opportunity_type=recommendation.opportunity_type,
        reason=recommendation.reason,
        expected_effect=recommendation.expected_effect,
        actual_effect=dict(outcome.actual_effect) if outcome else {},
        supporting_metrics=dict(recommendation.supporting_metrics),
        confidence_score=recommendation.confidence.score,
        risk_score=recommendation.risk.score,
        result=_result_from_outcome(outcome),
        success_score=float(outcome.success_score or 0.0) if outcome else 0.0,
        source_recommendation_id=source_recommendation_id,
        campaign_id=recommendation.campaign_id,
        tags=_tags_from_recommendation(recommendation),
    )
    save_memory_record(record, root=root)
    return record


def remember_observed_recommendation(
    recommendation: StoredRecommendation,
    outcome: RecommendationOutcome | None = None,
    root: str | Path | None = None,
) -> RecommendationMemoryRecord:
    record = RecommendationMemoryRecord(
        id=new_memory_id("memory"),
        created_at=utc_now_iso(),
        sku=recommendation.sku,
        action=recommendation.action,
        reason=recommendation.reason,
        expected_effect=dict(recommendation.expected_effect),
        actual_effect=dict(outcome.actual_effect) if outcome else {},
        supporting_metrics=dict(recommendation.supporting_metrics),
        confidence_score=float(recommendation.confidence_score or 0.0),
        risk_score=float(recommendation.risk_score or 0.0),
        result=_result_from_outcome(outcome),
        success_score=float(outcome.success_score or 0.0) if outcome else 0.0,
        source_recommendation_id=recommendation.id,
        campaign_id=recommendation.campaign_id or "",
        tags=[recommendation.status.value],
    )
    save_memory_record(record, root=root)
    return record


def build_memory_insight(
    records: list[RecommendationMemoryRecord],
    action: RecommendationAction,
    sku: str | None = None,
) -> MemoryInsight:
    related = [
        record
        for record in records
        if record.action is action and (sku is None or record.sku == sku)
    ]
    success_rate = _success_rate(related)
    average_score = _average_success_score(related)
    label = sku or "all SKUs"
    return MemoryInsight(
        id=new_memory_id("memory-insight"),
        created_at=utc_now_iso(),
        action=action,
        opportunity_type=None,
        sku=sku,
        sample_size=len(related),
        success_rate=success_rate,
        average_success_score=average_score,
        message=(
            f"{action.value} on {label}: {len(related)} records, "
            f"success rate {success_rate:.0%}"
        ),
        supporting_records=[record.id for record in related],
    )


def refresh_memory_insights(root: str | Path | None = None) -> list[MemoryInsight]:
    records = list_memory_records(root=root)
    actions = sorted({record.action for record in records}, key=lambda item: item.value)
    insights = [build_memory_insight(records, action) for action in actions]
    for insight in insights:
        save_memory_insight(insight, root=root)
    return insights


def generate_memory_support(
    feature: DecisionFeature,
    opportunity: Opportunity | None,
    action: RecommendationAction,
    root: str | Path | None = None,
) -> dict[str, Any]:
    records = list_memory_records(root=root)
    matches = find_similar_memory(feature, opportunity, action, candidates=records)
    success_rate = _success_rate_for_matches(matches)
    insights = _matching_insights(action, feature.sku, root=root)
    return {
        "memory_signals": _memory_signals(matches, success_rate, insights),
        "similar_recommendations": [_match_to_dict(match) for match in matches[:5]],
        "historical_action_success_rate": success_rate,
        "memory_insights": [_insight_to_dict(insight) for insight in insights[:5]],
        "memory_confidence": _memory_confidence(success_rate, matches),
    }


def aggregate_memory_by_action(
    records: list[RecommendationMemoryRecord],
) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[RecommendationMemoryRecord]] = defaultdict(list)
    for record in records:
        grouped[record.action.value].append(record)
    return {
        action: {
            "count": len(group),
            "success_rate": _success_rate(group),
            "average_success_score": _average_success_score(group),
        }
        for action, group in grouped.items()
    }


def _result_from_outcome(outcome: RecommendationOutcome | None) -> MemoryResult:
    if outcome is None or outcome.success_score is None:
        return MemoryResult.UNKNOWN
    if outcome.success_score >= 0.75:
        return MemoryResult.SUCCESS
    if outcome.success_score >= 0.4:
        return MemoryResult.PARTIAL_SUCCESS
    return MemoryResult.FAILURE


def _tags_from_recommendation(recommendation: Recommendation) -> list[str]:
    tags = [recommendation.opportunity_type.value, recommendation.action.value]
    if recommendation.campaign_id:
        tags.append("campaign")
    return tags


def _success_rate(records: list[RecommendationMemoryRecord]) -> float:
    comparable = [record for record in records if record.result is not MemoryResult.UNKNOWN]
    if not comparable:
        return 0.0
    score = 0.0
    for record in comparable:
        if record.result is MemoryResult.SUCCESS:
            score += 1.0
        elif record.result is MemoryResult.PARTIAL_SUCCESS:
            score += 0.5
    return score / len(comparable)


def _success_rate_for_matches(matches: list[MemoryMatch]) -> float:
    comparable = [match for match in matches if match.result is not MemoryResult.UNKNOWN]
    if not comparable:
        return 0.0
    score = 0.0
    for match in comparable:
        if match.result is MemoryResult.SUCCESS:
            score += 1.0
        elif match.result is MemoryResult.PARTIAL_SUCCESS:
            score += 0.5
    return score / len(comparable)


def _average_success_score(records: list[RecommendationMemoryRecord]) -> float:
    values = [record.success_score for record in records if record.success_score > 0]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _matching_insights(
    action: RecommendationAction,
    sku: str,
    root: str | Path | None,
) -> list[MemoryInsight]:
    return [
        insight
        for insight in list_memory_insights(root=root)
        if insight.action is action and (insight.sku is None or insight.sku == sku)
    ]


def _memory_signals(
    matches: list[MemoryMatch],
    success_rate: float,
    insights: list[MemoryInsight],
) -> list[dict[str, Any]]:
    if not matches and not insights:
        return []
    return [
        {
            "type": "RECOMMENDATION_MEMORY",
            "similar_recommendations": len(matches),
            "historical_action_success_rate": success_rate,
            "insights": len(insights),
            "message": (
                f"{len(matches)} similar recommendations, "
                f"action success rate {success_rate:.0%}"
            ),
        }
    ]


def _memory_confidence(success_rate: float, matches: list[MemoryMatch]) -> float:
    if not matches:
        return 0.5
    sample_factor = min(len(matches) / 10.0, 1.0)
    return round(max(0.0, min(1.0, 0.35 + success_rate * 0.45 + sample_factor * 0.2)), 4)


def _match_to_dict(match: MemoryMatch) -> dict[str, Any]:
    return {
        "record_id": match.record_id,
        "score": match.score,
        "reasons": match.reasons,
        "result": match.result.value,
        "success_score": match.success_score,
        "action": match.action.value,
        "sku": match.sku,
    }


def _insight_to_dict(insight: MemoryInsight) -> dict[str, Any]:
    return {
        "id": insight.id,
        "action": insight.action.value,
        "opportunity_type": insight.opportunity_type.value
        if insight.opportunity_type
        else "",
        "sku": insight.sku or "",
        "sample_size": insight.sample_size,
        "success_rate": insight.success_rate,
        "average_success_score": insight.average_success_score,
        "message": insight.message,
        "supporting_records": insight.supporting_records,
    }
