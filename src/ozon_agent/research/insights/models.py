from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MarketInsightType(StrEnum):
    PRICE_DROP = "PRICE_DROP"
    PRICE_INCREASE = "PRICE_INCREASE"
    RATING_CHANGE = "RATING_CHANGE"
    REVIEW_SURGE = "REVIEW_SURGE"
    REVIEW_DROP = "REVIEW_DROP"
    NEW_COMPETITOR = "NEW_COMPETITOR"
    COMPETITOR_DISAPPEARED = "COMPETITOR_DISAPPEARED"
    ASSORTMENT_GAP = "ASSORTMENT_GAP"
    CATEGORY_PRESSURE = "CATEGORY_PRESSURE"
    MARKET_GROWTH_SIGNAL = "MARKET_GROWTH_SIGNAL"
    MARKET_DECLINE_SIGNAL = "MARKET_DECLINE_SIGNAL"


class InsightPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class MarketSignal:
    signal_type: MarketInsightType
    sku: str
    message: str
    score: float
    priority: InsightPriority
    metrics: dict[str, Any] = field(default_factory=dict)
    competitor_key: str | None = None
    snapshot_id: str | None = None
    previous_snapshot_id: str | None = None


@dataclass(frozen=True)
class MarketRisk:
    risk_type: str
    sku: str
    message: str
    score: float
    priority: InsightPriority
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketOpportunity:
    opportunity_type: str
    sku: str
    message: str
    score: float
    priority: InsightPriority
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketInsight:
    id: str
    created_at: datetime
    insight_type: MarketInsightType
    sku: str
    message: str
    score: float
    priority: InsightPriority
    signals: list[MarketSignal] = field(default_factory=list)
    risks: list[MarketRisk] = field(default_factory=list)
    opportunities: list[MarketOpportunity] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    snapshot_id: str | None = None
    previous_snapshot_id: str | None = None
    competitor_key: str | None = None

    @staticmethod
    def now(
        insight_id: str,
        insight_type: MarketInsightType,
        sku: str,
        message: str,
        score: float,
        priority: InsightPriority,
        signals: list[MarketSignal] | None = None,
        risks: list[MarketRisk] | None = None,
        opportunities: list[MarketOpportunity] | None = None,
        metrics: dict[str, Any] | None = None,
        snapshot_id: str | None = None,
        previous_snapshot_id: str | None = None,
        competitor_key: str | None = None,
    ) -> MarketInsight:
        return MarketInsight(
            id=insight_id,
            created_at=datetime.now(UTC),
            insight_type=insight_type,
            sku=sku,
            message=message,
            score=score,
            priority=priority,
            signals=signals or [],
            risks=risks or [],
            opportunities=opportunities or [],
            metrics=metrics or {},
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            competitor_key=competitor_key,
        )
