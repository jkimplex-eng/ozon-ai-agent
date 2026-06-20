from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

PERFORMANCE_BASE_URL = "https://performance.ozon.ru"
CAMPAIGN_ENDPOINT = "/api/client/campaign"
STATS_REPORT_ENDPOINT = "/api/client/statistics/report"
STATS_DOWNLOAD_ENDPOINT = "/api/client/statistics/report/download"


class PerformanceReportStatus(StrEnum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class PerformanceCredentials:
    client_id: str
    client_secret: str


@dataclass(slots=True)
class PerformanceCampaign:
    id: int
    name: str
    status: str
    campaign_type: str = ""
    budget: float = 0.0
    daily_budget: float = 0.0
    start_date: str = ""
    end_date: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "campaign_type": self.campaign_type,
            "budget": self.budget,
            "daily_budget": self.daily_budget,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


@dataclass(slots=True)
class PerformanceStatsRow:
    date: str = ""
    campaign_id: str = ""
    campaign_name: str = ""
    sku: str = ""
    product_name: str = ""
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    add_to_cart: int = 0
    cpc: float = 0.0
    spend: float = 0.0
    orders: int = 0
    revenue: float = 0.0
    model_orders: int = 0
    model_revenue: float = 0.0
    drr: float = 0.0
    ordered_amount: int = 0
    total_drr: float = 0.0
    added_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "sku": self.sku,
            "product_name": self.product_name,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "ctr": self.ctr,
            "add_to_cart": self.add_to_cart,
            "cpc": self.cpc,
            "spend": self.spend,
            "orders": self.orders,
            "revenue": self.revenue,
            "model_orders": self.model_orders,
            "model_revenue": self.model_revenue,
            "drr": self.drr,
            "ordered_amount": self.ordered_amount,
            "total_drr": self.total_drr,
            "added_at": self.added_at,
        }


@dataclass(slots=True)
class PerformanceReportRequest:
    date_from: str
    date_to: str
    campaign_ids: list[int] = field(default_factory=list)
    limit: int = 1000


@dataclass(slots=True)
class PerformanceReportResult:
    report_id: str
    status: PerformanceReportStatus
    created_at: str = ""
    rows: list[PerformanceStatsRow] = field(default_factory=list)
    raw_csv: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PerformanceCampaignsResult:
    campaigns: list[PerformanceCampaign] = field(default_factory=list)
    raw_response: dict[str, object] = field(default_factory=dict)
    page: int = 1
    total_pages: int = 1
    warnings: list[str] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
