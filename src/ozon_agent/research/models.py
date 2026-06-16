from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MarketplaceSourceType(StrEnum):
    OZON_SEARCH = "OZON_SEARCH"
    OZON_PRODUCT_PAGE = "OZON_PRODUCT_PAGE"
    COMPETITOR_SITE = "COMPETITOR_SITE"
    MANUAL = "MANUAL"
    FIRECRAWL = "FIRECRAWL"


class ResearchSourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    PLANNED = "PLANNED"


class PricePosition(StrEnum):
    BELOW_MARKET = "BELOW_MARKET"
    MARKET_ALIGNED = "MARKET_ALIGNED"
    ABOVE_MARKET = "ABOVE_MARKET"
    UNKNOWN = "UNKNOWN"


class ResearchInsightType(StrEnum):
    PRICE_POSITION = "PRICE_POSITION"
    REVIEW_GAP = "REVIEW_GAP"
    RATING_GAP = "RATING_GAP"
    ASSORTMENT_GAP = "ASSORTMENT_GAP"
    DATA_QUALITY = "DATA_QUALITY"


@dataclass(frozen=True)
class MarketplaceSource:
    name: str
    source_type: MarketplaceSourceType
    status: ResearchSourceStatus
    description: str
    requires_network: bool = False


@dataclass(frozen=True)
class ResearchObservation:
    sku: str
    product_name: str = ""
    seller_name: str = ""
    source_name: str = "manual"
    source_url: str = ""
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    position: int | None = None
    available: bool | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def normalized_sku(self) -> str:
        return self.sku.strip().lower()


@dataclass(frozen=True)
class ResearchSnapshot:
    query: str
    source_name: str
    captured_at: datetime
    observations: list[ResearchObservation]


@dataclass(frozen=True)
class SnapshotIngestionResult:
    snapshot: ResearchSnapshot
    raw_rows: int
    ingested_rows: int
    skipped_rows: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarketplaceComparison:
    sku: str
    product_name: str
    competitor_count: int
    own_price: float | None
    min_competitor_price: float | None
    avg_competitor_price: float | None
    max_competitor_price: float | None
    price_position: PricePosition
    rating_gap: float | None
    review_gap: int | None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchInsight:
    insight_type: ResearchInsightType
    sku: str
    severity: str
    reason: str
    metrics: dict[str, Any] = field(default_factory=dict)
    source_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarketplaceResearchReport:
    query: str
    generated_at: datetime
    summary: dict[str, Any]
    comparisons: list[MarketplaceComparison]
    insights: list[ResearchInsight]
    sources: list[MarketplaceSource]
