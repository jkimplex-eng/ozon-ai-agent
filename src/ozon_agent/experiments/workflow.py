from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ozon_agent.experiments.models import (
    Experiment,
    ExperimentEvent,
    ExperimentEventType,
    ExperimentNotFoundError,
    ExperimentStatus,
    InvalidExperimentTransitionError,
    create_experiment,
)
from ozon_agent.experiments.repository import (
    get_experiment,
    save_experiment,
    save_experiment_event,
    update_experiment_metrics,
    update_experiment_status,
)


def create_new_experiment(
    sku: str,
    hypothesis: str,
    action: str,
    risk: str | None = None,
    confidence: str | None = None,
    expected_effect: dict[str, Any] | None = None,
    created_by: str = "system",
) -> Experiment:
    experiment = create_experiment(
        sku=sku,
        hypothesis=hypothesis,
        action=action,
        risk=risk,
        confidence=confidence,
        expected_effect=expected_effect,
        created_by=created_by,
    )
    save_experiment(experiment)
    _emit_event(
        experiment.id, ExperimentEventType.CREATED,
        to_status=ExperimentStatus.DRAFT, actor=created_by,
    )
    return experiment


def create_from_recommendation(
    recommendation_id: str,
    sku: str,
    action: str,
    hypothesis: str,
    risk: str | None = None,
    confidence: str | None = None,
    expected_effect: dict[str, Any] | None = None,
) -> Experiment:
    experiment = create_experiment(
        sku=sku,
        hypothesis=hypothesis,
        action=action,
        risk=risk,
        confidence=confidence,
        expected_effect=expected_effect,
        recommendation_id=recommendation_id,
    )
    save_experiment(experiment)
    _emit_event(
        experiment.id,
        ExperimentEventType.CREATED,
        to_status=ExperimentStatus.DRAFT,
        metadata={"recommendation_id": recommendation_id},
    )
    return experiment


def transition_experiment(
    experiment_id: str,
    target_status: ExperimentStatus,
    actor: str = "system",
    reason: str | None = None,
) -> Experiment:
    current = _require_experiment(experiment_id)
    _ensure_transition(current, target_status)

    update_fields: dict[str, Any] = {}
    now = datetime.now(UTC)

    if target_status == ExperimentStatus.RUNNING:
        update_fields["started_at"] = now
    elif target_status == ExperimentStatus.PAUSED:
        update_fields["paused_at"] = now
    elif target_status == ExperimentStatus.COMPLETED:
        update_fields["completed_at"] = now
    elif target_status == ExperimentStatus.CANCELLED:
        update_fields["cancelled_at"] = now
        update_fields["cancel_reason"] = reason
    elif target_status == ExperimentStatus.FAILED:
        update_fields["failed_at"] = now
        update_fields["fail_reason"] = reason

    updated = update_experiment_status(
        experiment_id,
        target_status,
        **update_fields,
    )
    if updated is None:
        raise ExperimentNotFoundError(experiment_id)

    _emit_event(
        experiment_id,
        ExperimentEventType.STATUS_CHANGE,
        from_status=current.status,
        to_status=target_status,
        actor=actor,
        reason=reason,
    )
    return updated


def mark_ready(experiment_id: str, actor: str = "system") -> Experiment:
    return transition_experiment(experiment_id, ExperimentStatus.READY, actor=actor)


def mark_running(experiment_id: str, actor: str = "system") -> Experiment:
    return transition_experiment(experiment_id, ExperimentStatus.RUNNING, actor=actor)


def mark_paused(experiment_id: str, actor: str = "system") -> Experiment:
    return transition_experiment(experiment_id, ExperimentStatus.PAUSED, actor=actor)


def mark_completed(experiment_id: str, actor: str = "system") -> Experiment:
    return transition_experiment(experiment_id, ExperimentStatus.COMPLETED, actor=actor)


def mark_cancelled(
    experiment_id: str,
    reason: str = "cancelled",
    actor: str = "system",
) -> Experiment:
    return transition_experiment(
        experiment_id, ExperimentStatus.CANCELLED, actor=actor, reason=reason,
    )


def mark_failed(
    experiment_id: str,
    reason: str = "failed",
    actor: str = "system",
) -> Experiment:
    return transition_experiment(
        experiment_id, ExperimentStatus.FAILED, actor=actor, reason=reason,
    )


def update_metrics(
    experiment_id: str,
    *,
    baseline_orders: float | None = None,
    baseline_revenue: float | None = None,
    baseline_drr: float | None = None,
    current_orders: float | None = None,
    current_revenue: float | None = None,
    current_drr: float | None = None,
    success_score: float | None = None,
    direction_accuracy: float | None = None,
    actual_effect: dict[str, Any] | None = None,
    summary: str | None = None,
) -> Experiment:
    _require_experiment(experiment_id)
    updated = update_experiment_metrics(
        experiment_id,
        baseline_orders=baseline_orders,
        baseline_revenue=baseline_revenue,
        baseline_drr=baseline_drr,
        current_orders=current_orders,
        current_revenue=current_revenue,
        current_drr=current_drr,
        success_score=success_score,
        direction_accuracy=direction_accuracy,
        actual_effect=actual_effect,
        summary=summary,
    )
    if updated is None:
        raise ExperimentNotFoundError(experiment_id)
    _emit_event(experiment_id, ExperimentEventType.METRICS_UPDATE)
    return updated


def evaluate_experiment(experiment_id: str) -> Experiment:
    exp = _require_experiment(experiment_id)
    if exp.status != ExperimentStatus.RUNNING:
        raise InvalidExperimentTransitionError(
            experiment_id, exp.status, ExperimentStatus.RUNNING,
        )

    direction_accuracy: float | None = None
    success_score: float | None = None

    if exp.baseline_orders > 0 and exp.current_orders > 0:
        if exp.current_orders >= exp.baseline_orders:
            direction_accuracy = 1.0
        else:
            direction_accuracy = 0.0

    if exp.baseline_revenue > 0 and exp.current_revenue > 0:
        revenue_change = (exp.current_revenue - exp.baseline_revenue) / exp.baseline_revenue
        success_score = max(0.0, min(1.0, (revenue_change + 1.0) / 2.0))

    updated = update_experiment_metrics(
        experiment_id,
        success_score=success_score,
        direction_accuracy=direction_accuracy,
    )
    if updated is None:
        raise ExperimentNotFoundError(experiment_id)
    _emit_event(experiment_id, ExperimentEventType.EVALUATED)
    return updated


def _require_experiment(experiment_id: str) -> Experiment:
    experiment = get_experiment(experiment_id)
    if experiment is None:
        raise ExperimentNotFoundError(experiment_id)
    return experiment


def _ensure_transition(
    experiment: Experiment,
    target: ExperimentStatus,
) -> None:
    from ozon_agent.experiments.models import EXPERIMENT_TRANSITIONS

    allowed = EXPERIMENT_TRANSITIONS.get(experiment.status, set())
    if target not in allowed:
        raise InvalidExperimentTransitionError(
            experiment.id, experiment.status, target,
        )


def _emit_event(
    experiment_id: str,
    event_type: ExperimentEventType,
    from_status: ExperimentStatus | None = None,
    to_status: ExperimentStatus | None = None,
    actor: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event = ExperimentEvent(
        id=str(uuid4()),
        experiment_id=experiment_id,
        created_at=datetime.now(UTC),
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        reason=reason,
        metadata=metadata or {},
    )
    save_experiment_event(event)
