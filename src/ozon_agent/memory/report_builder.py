from __future__ import annotations

from ozon_agent.memory.models import RecommendationMemoryStats
from ozon_agent.memory.repository import list_memory_insights, list_memory_records
from ozon_agent.memory.statistics import build_memory_statistics


def build_memory_report(stats: RecommendationMemoryStats | None = None) -> str:
    payload = stats or build_memory_statistics(list_memory_records())
    lines = [
        "Autonomous Recommendation Memory",
        f"Total records: {payload.total_records}",
        f"Success rate: {payload.success_rate:.0%}",
        f"Average success score: {payload.average_success_score:.2f}",
    ]
    if payload.by_action:
        lines.append("By action:")
        for action, item in sorted(payload.by_action.items()):
            lines.append(
                f"  - {action}: {item['count']} records, "
                f"success {float(item['success_rate']):.0%}"
            )
    return "\n".join(lines)


def build_memory_insights_report() -> str:
    insights = list_memory_insights()
    if not insights:
        return "No recommendation memory insights found."
    lines = ["Recommendation Memory Insights"]
    for insight in insights:
        lines.append(
            f"- {insight.action.value}: {insight.sample_size} records, "
            f"success {insight.success_rate:.0%} | {insight.message}"
        )
    return "\n".join(lines)


def memory_stats_to_dict(stats: RecommendationMemoryStats) -> dict[str, object]:
    return {
        "total_records": stats.total_records,
        "success_rate": stats.success_rate,
        "average_success_score": stats.average_success_score,
        "by_action": stats.by_action,
        "by_sku": stats.by_sku,
    }
