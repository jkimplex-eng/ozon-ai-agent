from __future__ import annotations

from collections import defaultdict

from ozon_agent.research.insights.models import InsightPriority, MarketInsight
from ozon_agent.research.insights.priorities import priority_sort_value


def build_market_report(insights: list[MarketInsight]) -> str:
    if not insights:
        return "Market Insights\n\nNo market insights generated."

    grouped: dict[InsightPriority, list[MarketInsight]] = defaultdict(list)
    for insight in sorted(
        insights,
        key=lambda item: (priority_sort_value(item.priority), -item.score, item.sku),
    ):
        grouped[insight.priority].append(insight)

    lines = ["Market Insights", ""]
    for priority in (
        InsightPriority.CRITICAL,
        InsightPriority.HIGH,
        InsightPriority.MEDIUM,
        InsightPriority.LOW,
    ):
        items = grouped.get(priority, [])
        if not items:
            continue
        lines.append(priority.value)
        for insight in items:
            lines.append(
                f"- {insight.message} "
                f"(sku={insight.sku}, score={insight.score:.0f}, type={insight.insight_type.value})"
            )
        lines.append("")
    return "\n".join(lines).rstrip()
