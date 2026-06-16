from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ExperimentStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ExperimentEventType(StrEnum):
    CREATED = "CREATED"
    STATUS_CHANGE = "STATUS_CHANGE"
    METRICS_UPDATE = "METRICS_UPDATE"
    EVALUATED = "EVALUATED"


EXPERIMENT_TRANSITIONS: dict[ExperimentStatus, set[ExperimentStatus]] = {
    ExperimentStatus.DRAFT: {ExperimentStatus.READY, ExperimentStatus.CANCELLED},
    ExperimentStatus.READY: {ExperimentStatus.RUNNING, ExperimentStatus.CANCELLED},
    ExperimentStatus.RUNNING: {
        ExperimentStatus.PAUSED,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.CANCELLED,
        ExperimentStatus.FAILED,
    },
    ExperimentStatus.PAUSED: {
        ExperimentStatus.RUNNING,
        ExperimentStatus.CANCELLED,
        ExperimentStatus.FAILED,
    },
    ExperimentStatus.COMPLETED: set(),
    ExperimentStatus.CANCELLED: set(),
    ExperimentStatus.FAILED: set(),
}


@dataclass(slots=True)
class Experiment:
    id: str
    created_at: datetime
    updated_at: datetime
    sku: str
    hypothesis: str
    action: str
    risk: str | None = None
    confidence: str | None = None
    status: ExperimentStatus = ExperimentStatus.DRAFT
    recommendation_id: str | None = None
    baseline_orders: float = 0.0
    baseline_revenue: float = 0.0
    baseline_drr: float = 0.0
    current_orders: float = 0.0
    current_revenue: float = 0.0
    current_drr: float = 0.0
    success_score: float | None = None
    direction_accuracy: float | None = None
    actual_effect: dict[str, Any] = field(default_factory=dict)
    expected_effect: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str | None = None
    started_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    failed_at: datetime | None = None
    cancel_reason: str | None = None
    fail_reason: str | None = None
    created_by: str = "system"


@dataclass(slots=True)
class ExperimentEvent:
    id: str
    experiment_id: str
    created_at: datetime
    event_type: ExperimentEventType
    from_status: ExperimentStatus | None = None
    to_status: ExperimentStatus | None = None
    actor: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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


def create_experiment(
    sku: str,
    hypothesis: str,
    action: str,
    risk: str | None = None,
    confidence: str | None = None,
    expected_effect: dict[str, Any] | None = None,
    recommendation_id: str | None = None,
    created_by: str = "system",
) -> Experiment:
    now = datetime.now(UTC)
    return Experiment(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        sku=sku,
        hypothesis=hypothesis,
        action=action,
        risk=risk,
        confidence=confidence,
        status=ExperimentStatus.DRAFT,
        recommendation_id=recommendation_id,
        expected_effect=expected_effect or {},
        created_by=created_by,
    )
