from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from ozon_agent.decision.models import (
    ConfidenceLevel,
    Recommendation,
    RecommendationAction,
    RiskLevel,
)


class RecommendationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    OBSERVED = "OBSERVED"
    CLOSED = "CLOSED"


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(slots=True)
class OutcomeWindow:
    days: int


@dataclass(slots=True)
class StoredRecommendation:
    id: str
    created_at: datetime
    updated_at: datetime
    sku: str
    action: RecommendationAction
    reason: str
    status: RecommendationStatus
    product_name: str | None = None
    confidence_score: float | None = None
    confidence_level: ConfidenceLevel | None = None
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    expected_effect: dict[str, Any] = field(default_factory=dict)
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    executed_at: datetime | None = None
    observed_at: datetime | None = None
    closed_at: datetime | None = None
    source: str | None = None
    campaign_id: str | None = None


@dataclass(slots=True)
class RecommendationOutcome:
    id: str
    recommendation_id: str
    created_at: datetime
    observation_window_days: int
    expected_effect: dict[str, Any]
    actual_effect: dict[str, Any]
    forecast_error: float | None
    success_score: float | None
    notes: str | None = None


class InvalidRecommendationTransitionError(ValueError):
    def __init__(
        self,
        recommendation_id: str,
        current_status: RecommendationStatus,
        target_status: RecommendationStatus,
    ) -> None:
        super().__init__(
            f"Recommendation {recommendation_id} cannot transition from "
            f"{current_status.value} to {target_status.value}"
        )
        self.recommendation_id = recommendation_id
        self.current_status = current_status
        self.target_status = target_status


class RecommendationNotFoundError(LookupError):
    def __init__(self, recommendation_id: str) -> None:
        super().__init__(f"Recommendation {recommendation_id} not found")
        self.recommendation_id = recommendation_id


def build_stored_recommendation(
    recommendation: Recommendation,
    source: str = "decision_engine",
) -> StoredRecommendation:
    now = datetime.now(UTC)
    expected_effect: dict[str, Any]
    if isinstance(recommendation.expected_effect, dict):
        expected_effect = dict(recommendation.expected_effect)
    else:
        expected_effect = {"summary": recommendation.expected_effect}
    return StoredRecommendation(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        sku=recommendation.sku,
        product_name=str(recommendation.supporting_metrics.get("product_name", "")) or None,
        action=recommendation.action,
        reason=recommendation.reason,
        confidence_score=recommendation.confidence.score,
        confidence_level=recommendation.confidence.level,
        risk_score=recommendation.risk.score,
        risk_level=recommendation.risk.level,
        expected_effect=expected_effect,
        supporting_metrics=dict(recommendation.supporting_metrics),
        status=RecommendationStatus.PENDING,
        source=source,
        campaign_id=recommendation.campaign_id or None,
    )


def build_outcome(
    recommendation_id: str,
    observation_window_days: int,
    expected_effect: dict[str, Any],
    actual_effect: dict[str, Any],
    forecast_error: float | None,
    success_score: float | None,
    notes: str | None = None,
) -> RecommendationOutcome:
    return RecommendationOutcome(
        id=str(uuid4()),
        recommendation_id=recommendation_id,
        created_at=datetime.now(UTC),
        observation_window_days=observation_window_days,
        expected_effect=expected_effect,
        actual_effect=actual_effect,
        forecast_error=forecast_error,
        success_score=success_score,
        notes=notes,
    )
