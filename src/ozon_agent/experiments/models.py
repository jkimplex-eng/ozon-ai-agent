from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from ozon_agent.decision.models import RecommendationAction, RiskLevel


class ExperimentStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass(slots=True)
class Experiment:
    id: str
    created_at: datetime
    updated_at: datetime
    sku: str
    title: str
    hypothesis: str
    action: RecommendationAction
    status: ExperimentStatus
    recommendation_id: str | None = None
    risk_level: RiskLevel | None = None
    confidence_score: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_by: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class ExperimentMetric:
    id: str
    experiment_id: str
    period: str
    metric_name: str
    metric_value: float | None
    created_at: datetime


@dataclass(slots=True)
class ExperimentEvent:
    id: str
    experiment_id: str
    created_at: datetime
    event_type: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExperimentOutcome:
    id: str
    experiment_id: str
    created_at: datetime
    success_score: float | None
    direction_accuracy: float | None
    actual_effect: dict[str, Any]
    expected_effect: dict[str, Any]
    summary: str


@dataclass(slots=True)
class ExperimentEvaluation:
    success_score: float | None
    direction_accuracy: float | None
    actual_effect: dict[str, float]
    expected_effect: dict[str, Any]
    summary: str


@dataclass(slots=True)
class ExperimentCreateRequest:
    sku: str
    title: str
    hypothesis: str
    action: RecommendationAction
    recommendation_id: str | None = None
    risk_level: RiskLevel | None = None
    confidence_score: float | None = None
    created_by: str | None = None
    notes: str | None = None


class InvalidExperimentTransitionError(ValueError):
    def __init__(
        self,
        experiment_id: str,
        current_status: ExperimentStatus,
        target_status: ExperimentStatus,
    ) -> None:
        super().__init__(
            f"Experiment {experiment_id} cannot transition from "
            f"{current_status.value} to {target_status.value}"
        )
        self.experiment_id = experiment_id
        self.current_status = current_status
        self.target_status = target_status


class ExperimentNotFoundError(LookupError):
    def __init__(self, experiment_id: str) -> None:
        super().__init__(f"Experiment {experiment_id} not found")
        self.experiment_id = experiment_id


def build_experiment(request: ExperimentCreateRequest) -> Experiment:
    now = datetime.now(UTC)
    return Experiment(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        recommendation_id=request.recommendation_id,
        sku=request.sku,
        title=request.title,
        hypothesis=request.hypothesis,
        action=request.action,
        status=ExperimentStatus.DRAFT,
        risk_level=request.risk_level,
        confidence_score=request.confidence_score,
        created_by=request.created_by,
        notes=request.notes,
    )


def build_experiment_metric(
    experiment_id: str,
    period: str,
    metric_name: str,
    metric_value: float | None,
) -> ExperimentMetric:
    return ExperimentMetric(
        id=str(uuid4()),
        experiment_id=experiment_id,
        period=period,
        metric_name=metric_name,
        metric_value=metric_value,
        created_at=datetime.now(UTC),
    )


def build_experiment_event(
    experiment_id: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> ExperimentEvent:
    return ExperimentEvent(
        id=str(uuid4()),
        experiment_id=experiment_id,
        created_at=datetime.now(UTC),
        event_type=event_type,
        message=message,
        metadata=dict(metadata or {}),
    )


def build_experiment_outcome(
    experiment_id: str,
    success_score: float | None,
    direction_accuracy: float | None,
    actual_effect: dict[str, Any],
    expected_effect: dict[str, Any],
    summary: str,
) -> ExperimentOutcome:
    return ExperimentOutcome(
        id=str(uuid4()),
        experiment_id=experiment_id,
        created_at=datetime.now(UTC),
        success_score=success_score,
        direction_accuracy=direction_accuracy,
        actual_effect=dict(actual_effect),
        expected_effect=dict(expected_effect),
        summary=summary,
    )
