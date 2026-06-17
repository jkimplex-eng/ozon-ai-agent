from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from ozon_agent.decision.models import (
    ConfidenceLevel,
    OpportunityType,
    RecommendationAction,
    RiskLevel,
)


@dataclass(slots=True)
class LearningSample:
    recommendation_id: str
    action: RecommendationAction
    sku: str
    risk_level: RiskLevel | None
    confidence_level: ConfidenceLevel | None
    opportunity_type: OpportunityType | None
    time_window_days: int
    expected_effect: dict[str, Any]
    actual_effect: dict[str, Any]
    absolute_errors: dict[str, float] = field(default_factory=dict)
    percentage_errors: dict[str, float] = field(default_factory=dict)
    direction_matches: dict[str, bool] = field(default_factory=dict)
    success_score: float | None = None
    forecast_error: float | None = None


@dataclass(slots=True)
class RecommendationAccuracy:
    total_samples: int
    comparable_metrics: int
    average_absolute_error: float
    average_percentage_error: float
    direction_accuracy: float
    success_rate: float


@dataclass(slots=True)
class ActionCalibration:
    dimension: str
    key: str
    sample_size: int
    calibration_factor: float
    direction_accuracy: float
    average_error: float
    reasons: list[str]


@dataclass(slots=True)
class CalibrationResult:
    overall_factor: float
    overall_accuracy: RecommendationAccuracy
    by_action: dict[str, ActionCalibration]
    by_sku: dict[str, ActionCalibration]
    by_risk_level: dict[str, ActionCalibration]
    by_confidence_level: dict[str, ActionCalibration]
    reasons: list[str]


@dataclass(slots=True)
class BacktestResult:
    total_recommendations: int
    successful_recommendations: int
    success_rate: float
    average_error: float
    median_error: float
    direction_accuracy: float
    estimated_profit_lift: float
    by_action: dict[str, RecommendationAccuracy] = field(default_factory=dict)
    by_sku: dict[str, RecommendationAccuracy] = field(default_factory=dict)


class ExperimentType(StrEnum):
    PRICE_CHANGE = "PRICE_CHANGE"
    TITLE_CHANGE = "TITLE_CHANGE"
    IMAGE_CHANGE = "IMAGE_CHANGE"
    DESCRIPTION_CHANGE = "DESCRIPTION_CHANGE"
    SEO_CHANGE = "SEO_CHANGE"
    ATTRIBUTE_CHANGE = "ATTRIBUTE_CHANGE"
    AD_BID_CHANGE = "AD_BID_CHANGE"
    AD_BUDGET_CHANGE = "AD_BUDGET_CHANGE"
    STOCK_CHANGE = "STOCK_CHANGE"
    CONTENT_CHANGE = "CONTENT_CHANGE"
    CUSTOM = "CUSTOM"


class ExperimentResult(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class ExperimentMetric:
    name: str
    baseline: float | None = None
    actual: float | None = None
    expected_delta_pct: float | None = None
    actual_delta_pct: float | None = None
    weight: float = 1.0
    higher_is_better: bool = True


@dataclass(slots=True)
class Hypothesis:
    id: str
    created_at: str
    sku: str
    experiment_type: ExperimentType
    statement: str
    expected_effect: dict[str, Any]
    success_criteria: dict[str, Any] = field(default_factory=dict)
    category: str = ""
    subcategory: str = ""
    product_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Experiment:
    id: str
    created_at: str
    updated_at: str
    sku: str
    experiment_type: ExperimentType
    hypothesis_id: str | None = None
    title: str = ""
    category: str = ""
    subcategory: str = ""
    product_type: str = ""
    price_range: str = ""
    shop_size: str = ""
    period: str = ""
    change_size: float | None = None
    expected_effect: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    result: ExperimentResult = ExperimentResult.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExperimentOutcome:
    id: str
    experiment_id: str
    created_at: str
    metrics: list[ExperimentMetric]
    result: ExperimentResult = ExperimentResult.UNKNOWN
    success_score: float = 0.0
    notes: str = ""


@dataclass(slots=True)
class LearningInsight:
    id: str
    created_at: str
    category: str
    experiment_type: ExperimentType
    experiment_count: int
    success_rate: float
    average_metric_lift: dict[str, float]
    message: str
    supporting_experiments: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SimilarityMatch:
    experiment_id: str
    score: float
    reasons: list[str]
    result: ExperimentResult = ExperimentResult.UNKNOWN
    success_score: float = 0.0


@dataclass(slots=True)
class ExperimentStatistics:
    total_experiments: int
    success_rate: float
    by_category: dict[str, dict[str, Any]]
    by_experiment_type: dict[str, dict[str, Any]]
    average_metric_lift: dict[str, float]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_learning_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"
