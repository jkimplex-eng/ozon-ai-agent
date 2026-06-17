from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from ozon_agent.memory.models import (
    MemoryResult,
    RecommendationMemoryRecord,
    RecommendationMemoryStats,
)
from ozon_agent.memory.repository import list_memory_records


def build_memory_statistics(
    records: list[RecommendationMemoryRecord] | None = None,
) -> RecommendationMemoryStats:
    rows = records if records is not None else list_memory_records()
    return RecommendationMemoryStats(
        total_records=len(rows),
        success_rate=build_memory_success_rate(rows),
        average_success_score=_average_success_score(rows),
        by_action=_group_stats(rows, lambda item: item.action.value),
        by_sku=_group_stats(rows, lambda item: item.sku or "UNKNOWN"),
    )


def build_memory_success_rate(records: list[RecommendationMemoryRecord]) -> float:
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


def _group_stats(
    records: list[RecommendationMemoryRecord],
    key_fn: Callable[[RecommendationMemoryRecord], str],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[RecommendationMemoryRecord]] = defaultdict(list)
    for record in records:
        grouped[key_fn(record)].append(record)
    return {
        key: {
            "count": len(group),
            "success_rate": build_memory_success_rate(group),
            "average_success_score": _average_success_score(group),
        }
        for key, group in grouped.items()
    }


def _average_success_score(records: list[RecommendationMemoryRecord]) -> float:
    values = [record.success_score for record in records if record.success_score > 0]
    if not values:
        return 0.0
    return sum(values) / len(values)
