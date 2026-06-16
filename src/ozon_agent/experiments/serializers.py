from __future__ import annotations

from datetime import datetime
from typing import Any

from ozon_agent.decision.models import RecommendationAction, RiskLevel
from ozon_agent.experiments.models import (
    Experiment,
    ExperimentEvaluation,
    ExperimentEvent,
    ExperimentMetric,
    ExperimentOutcome,
    ExperimentStatus,
)


def experiment_to_json(experiment: Experiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "created_at": experiment.created_at.isoformat(),
        "updated_at": experiment.updated_at.isoformat(),
        "recommendation_id": experiment.recommendation_id,
        "sku": experiment.sku,
        "title": experiment.title,
        "hypothesis": experiment.hypothesis,
        "action": experiment.action.value,
        "status": experiment.status.value,
        "risk_level": experiment.risk_level.value if experiment.risk_level is not None else None,
        "confidence_score": experiment.confidence_score,
        "started_at": _datetime_or_none(experiment.started_at),
        "ended_at": _datetime_or_none(experiment.ended_at),
        "created_by": experiment.created_by,
        "notes": experiment.notes,
    }


def experiment_from_json(payload: dict[str, Any]) -> Experiment:
    return Experiment(
        id=str(payload["id"]),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        recommendation_id=_string_or_none(payload.get("recommendation_id")),
        sku=str(payload["sku"]),
        title=str(payload["title"]),
        hypothesis=str(payload["hypothesis"]),
        action=RecommendationAction(str(payload["action"])),
        status=ExperimentStatus(str(payload["status"])),
        risk_level=_enum_or_none(RiskLevel, payload.get("risk_level")),
        confidence_score=_float_or_none(payload.get("confidence_score")),
        started_at=_parse_datetime_or_none(payload.get("started_at")),
        ended_at=_parse_datetime_or_none(payload.get("ended_at")),
        created_by=_string_or_none(payload.get("created_by")),
        notes=_string_or_none(payload.get("notes")),
    )


def metric_to_json(metric: ExperimentMetric) -> dict[str, Any]:
    return {
        "id": metric.id,
        "experiment_id": metric.experiment_id,
        "period": metric.period,
        "metric_name": metric.metric_name,
        "metric_value": metric.metric_value,
        "created_at": metric.created_at.isoformat(),
    }


def metric_from_json(payload: dict[str, Any]) -> ExperimentMetric:
    return ExperimentMetric(
        id=str(payload["id"]),
        experiment_id=str(payload["experiment_id"]),
        period=str(payload["period"]),
        metric_name=str(payload["metric_name"]),
        metric_value=_float_or_none(payload.get("metric_value")),
        created_at=_parse_datetime(payload["created_at"]),
    )


def event_to_json(event: ExperimentEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "experiment_id": event.experiment_id,
        "created_at": event.created_at.isoformat(),
        "event_type": event.event_type,
        "message": event.message,
        "metadata": event.metadata,
    }


def event_from_json(payload: dict[str, Any]) -> ExperimentEvent:
    return ExperimentEvent(
        id=str(payload["id"]),
        experiment_id=str(payload["experiment_id"]),
        created_at=_parse_datetime(payload["created_at"]),
        event_type=str(payload["event_type"]),
        message=str(payload["message"]),
        metadata=_dict_or_empty(payload.get("metadata")),
    )


def outcome_to_json(outcome: ExperimentOutcome) -> dict[str, Any]:
    return {
        "id": outcome.id,
        "experiment_id": outcome.experiment_id,
        "created_at": outcome.created_at.isoformat(),
        "success_score": outcome.success_score,
        "direction_accuracy": outcome.direction_accuracy,
        "actual_effect": outcome.actual_effect,
        "expected_effect": outcome.expected_effect,
        "summary": outcome.summary,
    }


def outcome_from_json(payload: dict[str, Any]) -> ExperimentOutcome:
    return ExperimentOutcome(
        id=str(payload["id"]),
        experiment_id=str(payload["experiment_id"]),
        created_at=_parse_datetime(payload["created_at"]),
        success_score=_float_or_none(payload.get("success_score")),
        direction_accuracy=_float_or_none(payload.get("direction_accuracy")),
        actual_effect=_dict_or_empty(payload.get("actual_effect")),
        expected_effect=_dict_or_empty(payload.get("expected_effect")),
        summary=str(payload.get("summary", "")),
    )


def evaluation_to_json(evaluation: ExperimentEvaluation) -> dict[str, Any]:
    return {
        "success_score": evaluation.success_score,
        "direction_accuracy": evaluation.direction_accuracy,
        "actual_effect": evaluation.actual_effect,
        "expected_effect": evaluation.expected_effect,
        "summary": evaluation.summary,
    }


def _datetime_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_datetime_or_none(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return _parse_datetime(value)


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _enum_or_none(enum_type: type[Any], value: Any) -> Any:
    if value in (None, ""):
        return None
    return enum_type(str(value))
