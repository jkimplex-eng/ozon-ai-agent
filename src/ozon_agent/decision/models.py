from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RecommendationAction(StrEnum):
    INCREASE_BUDGET = "INCREASE_BUDGET"
    DECREASE_BUDGET = "DECREASE_BUDGET"
    PAUSE_CAMPAIGN = "PAUSE_CAMPAIGN"
    INCREASE_STOCK = "INCREASE_STOCK"
    DECREASE_PRICE = "DECREASE_PRICE"
    INCREASE_PRICE = "INCREASE_PRICE"
    IMPROVE_CONTENT = "IMPROVE_CONTENT"
    BOOST_REVIEWS = "BOOST_REVIEWS"
    NO_ACTION = "NO_ACTION"


class OpportunityType(StrEnum):
    STOCK_RISK = "STOCK_RISK"
    AD_GROWTH = "AD_GROWTH"
    AD_WASTE = "AD_WASTE"
    PRICE_MARGIN = "PRICE_MARGIN"
    PRICE_CONVERSION = "PRICE_CONVERSION"
    RANKING_RISK = "RANKING_RISK"
    RANKING_GROWTH = "RANKING_GROWTH"
    CONTENT_QUALITY = "CONTENT_QUALITY"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(slots=True)
class DecisionFeature:
    sku: str
    offer_id: str = ""
    product_name: str = ""
    campaign_id: str = ""
    date: str = ""
    price: float = 0.0
    sales_quantity: float = 0.0
    sales_revenue: float = 0.0
    sales_rows_matched: int = 0
    sales_trend_pct: float = 0.0
    sales_cv: float = 0.0
    ad_spend: float = 0.0
    impressions: float = 0.0
    clicks: float = 0.0
    ctr: float = 0.0
    cpc: float = 0.0
    ad_orders: float = 0.0
    ad_revenue: float = 0.0
    roas: float = 0.0
    drr: float = 0.0
    gross_profit_estimate: float | None = None
    gross_margin_pct: float | None = None
    cogs_per_unit: float | None = None
    current_stock: float | None = None
    stock_days: float | None = None
    stockout_probability: float | None = None
    forecast_quantity: float | None = None
    forecast_revenue: float | None = None
    ranking_position: float | None = None
    ranking_trend: float | None = None
    review_rating: float | None = None
    review_count: int = 0
    priority_sku: bool = False
    external_traffic: bool = False
    data_freshness_days: float = 999.0
    sample_size: int = 0
    has_forecast: bool = False
    has_stock: bool = False
    has_ranking: bool = False
    has_reviews: bool = False
    supporting_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Opportunity:
    opportunity_type: OpportunityType
    sku: str
    severity: str
    impact_score: float
    reason: str
    metrics: dict[str, Any]
    campaign_id: str = ""


@dataclass(slots=True)
class ConfidenceScore:
    score: float
    level: ConfidenceLevel
    reasons: list[str]


@dataclass(slots=True)
class RiskScore:
    level: RiskLevel
    score: float
    reasons: list[str]


@dataclass(slots=True)
class Recommendation:
    sku: str
    action: RecommendationAction
    expected_effect: str
    confidence: ConfidenceScore
    risk: RiskScore
    reason: str
    supporting_metrics: dict[str, Any]
    created_at: str
    opportunity_type: OpportunityType
    campaign_id: str = ""
    impact_score: float = 0.0
    market_signals: list[dict[str, Any]] = field(default_factory=list)
    market_risks: list[dict[str, Any]] = field(default_factory=list)
    market_opportunities: list[dict[str, Any]] = field(default_factory=list)
    knowledge_signals: list[dict[str, Any]] = field(default_factory=list)
    knowledge_rules: list[dict[str, Any]] = field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)
    learning_signals: list[dict[str, Any]] = field(default_factory=list)
    similar_experiments: list[dict[str, Any]] = field(default_factory=list)
    historical_success_rate: float = 0.0
    learning_insights: list[dict[str, Any]] = field(default_factory=list)
    recommended_confidence: float | None = None
    memory_signals: list[dict[str, Any]] = field(default_factory=list)
    similar_recommendations: list[dict[str, Any]] = field(default_factory=list)
    historical_action_success_rate: float = 0.0
    memory_insights: list[dict[str, Any]] = field(default_factory=list)
    memory_confidence: float | None = None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
