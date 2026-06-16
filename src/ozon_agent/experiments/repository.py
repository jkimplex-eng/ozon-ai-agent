from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from ozon_agent.db.connection import get_connection
from ozon_agent.experiments.models import (
    Experiment,
    ExperimentEvent,
    ExperimentMetric,
    ExperimentOutcome,
    ExperimentStatus,
)
from ozon_agent.experiments.serializers import (
    event_from_json,
    experiment_from_json,
    metric_from_json,
    outcome_from_json,
)

ConnectionFactory = Callable[[], Any]

_connection_factory: ConnectionFactory = get_connection


def save_experiment(experiment: Experiment) -> str:
    sql = """
        INSERT INTO experiments (
            id, created_at, updated_at, recommendation_id, sku, title, hypothesis,
            action, status, risk_level, confidence_score, started_at, ended_at,
            created_by, notes
        ) VALUES (
            %(id)s, %(created_at)s, %(updated_at)s, %(recommendation_id)s, %(sku)s,
            %(title)s, %(hypothesis)s, %(action)s, %(status)s, %(risk_level)s,
            %(confidence_score)s, %(started_at)s, %(ended_at)s, %(created_by)s, %(notes)s
        )
        ON CONFLICT (id) DO UPDATE SET
            updated_at = EXCLUDED.updated_at,
            recommendation_id = EXCLUDED.recommendation_id,
            sku = EXCLUDED.sku,
            title = EXCLUDED.title,
            hypothesis = EXCLUDED.hypothesis,
            action = EXCLUDED.action,
            status = EXCLUDED.status,
            risk_level = EXCLUDED.risk_level,
            confidence_score = EXCLUDED.confidence_score,
            started_at = EXCLUDED.started_at,
            ended_at = EXCLUDED.ended_at,
            created_by = EXCLUDED.created_by,
            notes = EXCLUDED.notes
    """
    _execute(sql, _experiment_record(experiment))
    return experiment.id


def get_experiment(experiment_id: str) -> Experiment | None:
    rows = _fetch_all("SELECT * FROM experiments WHERE id = %(id)s", {"id": experiment_id})
    if not rows:
        return None
    return _row_to_experiment(rows[0])


def list_experiments(
    status: ExperimentStatus | None = None,
    sku: str | None = None,
    limit: int = 50,
) -> list[Experiment]:
    sql, params = _build_list_experiments_query(status=status, sku=sku, limit=limit)
    rows = _fetch_all(sql, params)
    return [_row_to_experiment(row) for row in rows]


def update_experiment_status(
    experiment_id: str,
    status: str,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    notes: str | None = None,
) -> Experiment | None:
    sql = """
        UPDATE experiments
        SET updated_at = %(updated_at)s,
            status = %(status)s,
            started_at = COALESCE(%(started_at)s, started_at),
            ended_at = COALESCE(%(ended_at)s, ended_at),
            notes = COALESCE(%(notes)s, notes)
        WHERE id = %(id)s
    """
    _execute(
        sql,
        {
            "id": experiment_id,
            "updated_at": datetime.now(UTC),
            "status": status,
            "started_at": started_at,
            "ended_at": ended_at,
            "notes": notes,
        },
    )
    return get_experiment(experiment_id)


def save_experiment_metric(metric: ExperimentMetric) -> str:
    sql = """
        INSERT INTO experiment_metrics (
            id, experiment_id, period, metric_name, metric_value, created_at
        ) VALUES (
            %(id)s, %(experiment_id)s, %(period)s, %(metric_name)s, %(metric_value)s, %(created_at)s
        )
        ON CONFLICT (id) DO UPDATE SET
            period = EXCLUDED.period,
            metric_name = EXCLUDED.metric_name,
            metric_value = EXCLUDED.metric_value,
            created_at = EXCLUDED.created_at
    """
    _execute(
        sql,
        {
            "id": metric.id,
            "experiment_id": metric.experiment_id,
            "period": metric.period,
            "metric_name": metric.metric_name,
            "metric_value": metric.metric_value,
            "created_at": metric.created_at,
        },
    )
    return metric.id


def list_experiment_metrics(
    experiment_id: str,
    period: str | None = None,
) -> list[ExperimentMetric]:
    sql_lines = ["SELECT * FROM experiment_metrics", "WHERE experiment_id = %(experiment_id)s"]
    params: dict[str, Any] = {"experiment_id": experiment_id}
    if period is not None:
        sql_lines.append("AND period = %(period)s")
        params["period"] = period
    sql_lines.append("ORDER BY created_at ASC")
    rows = _fetch_all("\n".join(sql_lines), params)
    return [_row_to_metric(row) for row in rows]


def save_experiment_event(event: ExperimentEvent) -> str:
    sql = """
        INSERT INTO experiment_events (
            id, experiment_id, created_at, event_type, message, metadata
        ) VALUES (
            %(id)s, %(experiment_id)s, %(created_at)s, %(event_type)s,
            %(message)s, %(metadata)s::jsonb
        )
        ON CONFLICT (id) DO UPDATE SET
            created_at = EXCLUDED.created_at,
            event_type = EXCLUDED.event_type,
            message = EXCLUDED.message,
            metadata = EXCLUDED.metadata
    """
    _execute(
        sql,
        {
            "id": event.id,
            "experiment_id": event.experiment_id,
            "created_at": event.created_at,
            "event_type": event.event_type,
            "message": event.message,
            "metadata": json.dumps(event.metadata),
        },
    )
    return event.id


def list_experiment_events(experiment_id: str) -> list[ExperimentEvent]:
    rows = _fetch_all(
        """
        SELECT * FROM experiment_events
        WHERE experiment_id = %(experiment_id)s
        ORDER BY created_at ASC
        """,
        {"experiment_id": experiment_id},
    )
    return [_row_to_event(row) for row in rows]


def save_experiment_outcome(outcome: ExperimentOutcome) -> str:
    sql = """
        INSERT INTO experiment_outcomes (
            id, experiment_id, created_at, success_score, direction_accuracy,
            actual_effect, expected_effect, summary
        ) VALUES (
            %(id)s, %(experiment_id)s, %(created_at)s, %(success_score)s,
            %(direction_accuracy)s, %(actual_effect)s::jsonb,
            %(expected_effect)s::jsonb, %(summary)s
        )
        ON CONFLICT (id) DO UPDATE SET
            created_at = EXCLUDED.created_at,
            success_score = EXCLUDED.success_score,
            direction_accuracy = EXCLUDED.direction_accuracy,
            actual_effect = EXCLUDED.actual_effect,
            expected_effect = EXCLUDED.expected_effect,
            summary = EXCLUDED.summary
    """
    _execute(
        sql,
        {
            "id": outcome.id,
            "experiment_id": outcome.experiment_id,
            "created_at": outcome.created_at,
            "success_score": outcome.success_score,
            "direction_accuracy": outcome.direction_accuracy,
            "actual_effect": json.dumps(outcome.actual_effect),
            "expected_effect": json.dumps(outcome.expected_effect),
            "summary": outcome.summary,
        },
    )
    return outcome.id


def get_experiment_outcome(experiment_id: str) -> ExperimentOutcome | None:
    rows = _fetch_all(
        "SELECT * FROM experiment_outcomes WHERE experiment_id = %(experiment_id)s",
        {"experiment_id": experiment_id},
    )
    if not rows:
        return None
    return _row_to_outcome(rows[0])


def _experiment_record(experiment: Experiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "created_at": experiment.created_at,
        "updated_at": experiment.updated_at,
        "recommendation_id": experiment.recommendation_id,
        "sku": experiment.sku,
        "title": experiment.title,
        "hypothesis": experiment.hypothesis,
        "action": experiment.action.value,
        "status": experiment.status.value,
        "risk_level": experiment.risk_level.value if experiment.risk_level is not None else None,
        "confidence_score": experiment.confidence_score,
        "started_at": experiment.started_at,
        "ended_at": experiment.ended_at,
        "created_by": experiment.created_by,
        "notes": experiment.notes,
    }


def _build_list_experiments_query(
    status: ExperimentStatus | None,
    sku: str | None,
    limit: int,
) -> tuple[str, dict[str, Any]]:
    where_clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit}
    if status is not None:
        where_clauses.append("status = %(status)s")
        params["status"] = status.value
    if sku is not None:
        where_clauses.append("sku = %(sku)s")
        params["sku"] = sku
    sql_lines = ["SELECT * FROM experiments"]
    if where_clauses:
        sql_lines.append("WHERE " + " AND ".join(where_clauses))
    sql_lines.append("ORDER BY created_at DESC")
    sql_lines.append("LIMIT %(limit)s")
    return "\n".join(sql_lines), params


def _row_to_experiment(row: dict[str, Any]) -> Experiment:
    return experiment_from_json(row)


def _row_to_metric(row: dict[str, Any]) -> ExperimentMetric:
    return metric_from_json(row)


def _row_to_event(row: dict[str, Any]) -> ExperimentEvent:
    payload = {**row, "metadata": _json_to_dict(row.get("metadata"))}
    return event_from_json(payload)


def _row_to_outcome(row: dict[str, Any]) -> ExperimentOutcome:
    payload = {
        **row,
        "actual_effect": _json_to_dict(row.get("actual_effect")),
        "expected_effect": _json_to_dict(row.get("expected_effect")),
    }
    return outcome_from_json(payload)


def _json_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    return dict(json.loads(str(value)))


def _fetch_all(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with _connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
        conn.commit()
    return [dict(row) for row in rows]


def _execute(sql: str, params: dict[str, Any]) -> None:
    with _connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


@contextmanager
def override_connection_factory(factory: ConnectionFactory) -> Any:
    global _connection_factory
    previous_factory = _connection_factory
    _connection_factory = factory
    try:
        yield
    finally:
        _connection_factory = previous_factory
