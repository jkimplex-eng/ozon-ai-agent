"""Stub service for SKU intelligence used by telegram bot."""
from __future__ import annotations

from ozon_agent.intelligence.sku_stubs import (
    HealthStatus,
    HealthInfo,
    RecommendationInfo,
    RootCause,
    SkuMetrics,
    TrendDirection,
    TrendInfo,
    analyze_sku,
    get_top_skus,
    get_worst_skus,
)

__all__ = [
    "HealthStatus",
    "HealthInfo",
    "RecommendationInfo",
    "RootCause",
    "SkuMetrics",
    "TrendDirection",
    "TrendInfo",
    "analyze_sku",
    "get_top_skus",
    "get_worst_skus",
]
