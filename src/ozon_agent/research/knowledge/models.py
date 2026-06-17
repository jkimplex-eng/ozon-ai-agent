from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ozon_agent.research.models import ResearchObservation, ResearchSnapshot


@dataclass(frozen=True)
class MarketKnowledgeSnapshot:
    id: str
    query: str
    source_name: str
    captured_at: datetime
    observations: list[ResearchObservation]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    def to_research_snapshot(self) -> ResearchSnapshot:
        return ResearchSnapshot(
            query=self.query,
            source_name=self.source_name,
            captured_at=self.captured_at,
            observations=list(self.observations),
        )


@dataclass(frozen=True)
class CompetitorHistoryRecord:
    snapshot_id: str
    sku: str
    competitor_key: str
    seller_name: str
    source_url: str
    observed_at: datetime
    price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    position: int | None = None
    available: bool | None = None


@dataclass(frozen=True)
class MarketInsightRecord:
    id: str
    created_at: datetime
    insight_type: str
    sku: str
    message: str
    severity: str
    snapshot_id: str | None = None
    previous_snapshot_id: str | None = None
    current_snapshot_id: str | None = None
    competitor_key: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketTrend:
    sku: str
    competitor_key: str
    metric: str
    direction: str
    first_value: float
    last_value: float
    delta: float
    delta_percent: float | None
    snapshot_count: int
