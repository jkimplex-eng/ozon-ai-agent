from __future__ import annotations

from collections.abc import Iterable

from ozon_agent.decision.models import DecisionFeature, Opportunity, RecommendationAction
from ozon_agent.memory.models import MemoryMatch, MemoryResult, RecommendationMemoryRecord
from ozon_agent.memory.repository import list_memory_records


def find_similar_memory(
    feature: DecisionFeature,
    opportunity: Opportunity | None,
    action: RecommendationAction,
    candidates: Iterable[RecommendationMemoryRecord] | None = None,
    limit: int = 10,
) -> list[MemoryMatch]:
    rows = list(candidates) if candidates is not None else list_memory_records()
    matches = [
        calculate_memory_similarity(feature, opportunity, action, record)
        for record in rows
    ]
    matches = [match for match in matches if match.score > 0]
    return rank_memory_matches(matches)[:limit]


def rank_memory_matches(matches: list[MemoryMatch]) -> list[MemoryMatch]:
    return sorted(matches, key=lambda item: item.score, reverse=True)


def calculate_memory_similarity(
    feature: DecisionFeature,
    opportunity: Opportunity | None,
    action: RecommendationAction,
    record: RecommendationMemoryRecord,
) -> MemoryMatch:
    score = 0.0
    reasons: list[str] = []
    if record.sku == feature.sku:
        score += 0.28
        reasons.append("same sku")
    if record.action is action:
        score += 0.28
        reasons.append("same action")
    if opportunity and record.opportunity_type is opportunity.opportunity_type:
        score += 0.20
        reasons.append("same opportunity")
    score += _metric_match(feature, record, "category", 0.08, reasons)
    score += _metric_match(feature, record, "price_range", 0.06, reasons)
    score += _metric_match(feature, record, "product_type", 0.06, reasons)
    if record.result is not MemoryResult.UNKNOWN:
        score += 0.04
        reasons.append("observed outcome")
    return MemoryMatch(
        record_id=record.id,
        score=round(min(score, 1.0), 4),
        reasons=reasons,
        result=record.result,
        success_score=record.success_score,
        action=record.action,
        sku=record.sku,
    )


def _metric_match(
    feature: DecisionFeature,
    record: RecommendationMemoryRecord,
    metric: str,
    weight: float,
    reasons: list[str],
) -> float:
    left = str(feature.supporting_metrics.get(metric, "")).strip().lower()
    right = str(record.supporting_metrics.get(metric, "")).strip().lower()
    if left and right and left == right:
        reasons.append(f"same {metric}")
        return weight
    return 0.0
