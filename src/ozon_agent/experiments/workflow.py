from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.experiments.models import (
    Experiment,
    ExperimentCreateRequest,
    ExperimentNotFoundError,
    ExperimentStatus,
    InvalidExperimentTransitionError,
    build_experiment,
    build_experiment_event,
)
from ozon_agent.experiments.repository import (
    get_experiment,
    save_experiment,
    save_experiment_event,
    update_experiment_status,
)


def create_experiment(request: ExperimentCreateRequest) -> Experiment:
    experiment = build_experiment(request)
    save_experiment(experiment)
    save_experiment_event(
        build_experiment_event(
            experiment.id,
            "created",
            f"Experiment created in {experiment.status.value}",
            metadata={"status": experiment.status.value},
        )
    )
    return experiment


def mark_ready(experiment_id: str) -> Experiment:
    return _transition(experiment_id, ExperimentStatus.READY)


def start_experiment(experiment_id: str) -> Experiment:
    return _transition(experiment_id, ExperimentStatus.RUNNING, started_at=datetime.now(UTC))


def pause_experiment(experiment_id: str) -> Experiment:
    return _transition(experiment_id, ExperimentStatus.PAUSED)


def complete_experiment(experiment_id: str) -> Experiment:
    return _transition(experiment_id, ExperimentStatus.COMPLETED, ended_at=datetime.now(UTC))


def cancel_experiment(experiment_id: str, reason: str) -> Experiment:
    return _transition(
        experiment_id,
        ExperimentStatus.CANCELLED,
        ended_at=datetime.now(UTC),
        notes=reason,
    )


def fail_experiment(experiment_id: str, reason: str) -> Experiment:
    return _transition(
        experiment_id,
        ExperimentStatus.FAILED,
        ended_at=datetime.now(UTC),
        notes=reason,
    )


def _transition(
    experiment_id: str,
    target_status: ExperimentStatus,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    notes: str | None = None,
) -> Experiment:
    current = _require_experiment(experiment_id)
    _ensure_transition(current, target_status)
    updated = update_experiment_status(
        experiment_id,
        target_status.value,
        started_at=started_at,
        ended_at=ended_at,
        notes=notes,
    )
    experiment = _require_updated(updated, experiment_id)
    metadata = {"status": target_status.value}
    if notes:
        metadata["notes"] = notes
    save_experiment_event(
        build_experiment_event(
            experiment.id,
            target_status.value.lower(),
            f"Experiment moved to {target_status.value}",
            metadata=metadata,
        )
    )
    return experiment


def _require_experiment(experiment_id: str) -> Experiment:
    experiment = get_experiment(experiment_id)
    if experiment is None:
        raise ExperimentNotFoundError(experiment_id)
    return experiment


def _require_updated(experiment: Experiment | None, experiment_id: str) -> Experiment:
    if experiment is None:
        raise ExperimentNotFoundError(experiment_id)
    return experiment


def _ensure_transition(experiment: Experiment, target: ExperimentStatus) -> None:
    allowed = {
        ExperimentStatus.DRAFT: {
            ExperimentStatus.READY,
            ExperimentStatus.CANCELLED,
            ExperimentStatus.FAILED,
        },
        ExperimentStatus.READY: {
            ExperimentStatus.RUNNING,
            ExperimentStatus.CANCELLED,
            ExperimentStatus.FAILED,
        },
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
    if target not in allowed[experiment.status]:
        raise InvalidExperimentTransitionError(experiment.id, experiment.status, target)
