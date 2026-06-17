from __future__ import annotations

from ozon_agent.research.knowledge.history import (
    build_history,
    compare_snapshots,
    detect_changes,
    detect_price_trend,
    detect_rating_trend,
    detect_review_trend,
    detect_trends,
)
from ozon_agent.research.knowledge.models import (
    CompetitorHistoryRecord,
    MarketInsightRecord,
    MarketKnowledgeSnapshot,
    MarketTrend,
)
from ozon_agent.research.knowledge.snapshot_store import (
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)

__all__ = [
    "CompetitorHistoryRecord",
    "MarketInsightRecord",
    "MarketKnowledgeSnapshot",
    "MarketTrend",
    "build_history",
    "compare_snapshots",
    "delete_snapshot",
    "detect_changes",
    "detect_price_trend",
    "detect_rating_trend",
    "detect_review_trend",
    "detect_trends",
    "list_snapshots",
    "load_snapshot",
    "save_snapshot",
]
