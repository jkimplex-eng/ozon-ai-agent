from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
