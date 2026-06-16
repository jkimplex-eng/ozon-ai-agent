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
    ExperimentEventType,
    ExperimentStatus,
)

ConnectionFactory = Callable[[], Any]

_connection_factory: ConnectionFactory = get_connection


def save_experiment(experiment: Experiment) -> str:
    sql = """
        INSERT INTO experiments (
            id, created_at, updated_at, sku, hypothesis, action, risk, confidence,
            status, recommendation_id,
            baseline_orders, baseline_revenue, baseline_drr,
            current_orders, current_revenue, current_drr,
            success_score, direction_accuracy,
            actual_effect, expected_effect, metrics, summary,
            started_at, paused_at, completed_at, cancelled_at, failed_at,
            cancel_reason, fail_reason, created_by
        ) VALUES (
            %(id)s, %(created_at)s, %(updated_at)s,
            %(sku)s, %(hypothesis)s, %(action)s, %(risk)s, %(confidence)s,
            %(status)s, %(recommendation_id)s,
            %(baseline_orders)s, %(baseline_revenue)s, %(baseline_drr)s,
            %(current_orders)s, %(current_revenue)s, %(current_drr)s,
            %(success_score)s, %(direction_accuracy)s,
            %(actual_effect)s::jsonb, %(expected_effect)s::jsonb,
            %(metrics)s::jsonb, %(summary)s,
            %(started_at)s, %(paused_at)s, %(completed_at)s,
            %(cancelled_at)s, %(failed_at)s,
            %(cancel_reason)s, %(fail_reason)s, %(created_by)s
        )
        ON CONFLICT (id) DO UPDATE SET
            updated_at = EXCLUDED.updated_at,
            sku = EXCLUDED.sku,
            hypothesis = EXCLUDED.hypothesis,
            action = EXCLUDED.action,
            risk = EXCLUDED.risk,
            confidence = EXCLUDED.confidence,
            status = EXCLUDED.status,
            recommendation_id = EXCLUDED.recommendation_id,
            baseline_orders = EXCLUDED.baseline_orders,
            baseline_revenue = EXCLUDED.baseline_revenue,
            baseline_drr = EXCLUDED.baseline_drr,
            current_orders = EXCLUDED.current_orders,
            current_revenue = EXCLUDED.current_revenue,
            current_drr = EXCLUDED.current_drr,
            success_score = EXCLUDED.success_score,
            direction_accuracy = EXCLUDED.direction_accuracy,
            actual_effect = EXCLUDED.actual_effect,
            expected_effect = EXCLUDED.expected_effect,
            metrics = EXCLUDED.metrics,
            summary = EXCLUDED.summary,
            started_at = EXCLUDED.started_at,
            paused_at = EXCLUDED.paused_at,
            completed_at = EXCLUDED.completed_at,
            cancelled_at = EXCLUDED.cancelled_at,
            failed_at = EXCLUDED.failed_at,
            cancel_reason = EXCLUDED.cancel_reason,
            fail_reason = EXCLUDED.fail_reason,
            created_by = EXCLUDED.created_by
    """
    _execute(sql, _experiment_record(experiment))
    return experiment.id


def get_experiment(experiment_id: str) -> Experiment | None:
    sql = "SELECT * FROM experiments WHERE id = %(id)s"
    rows = _fetch_all(sql, {"id": experiment_id})
    if not rows:
        return None
    return _row_to_experiment(rows[0])


def list_experiments(
    status: ExperimentStatus | None = None,
    sku: str | None = None,
    limit: int = 50,
) -> list[Experiment]:
    sql, params = _build_list_query(status=status, sku=sku, limit=limit)
    rows = _fetch_all(sql, params)
    return [_row_to_experiment(row) for row in rows]


def update_experiment_status(
    experiment_id: str,
    status: ExperimentStatus,
    **fields: Any,
) -> Experiment | None:
    set_clauses = ["status = %(status)s", "updated_at = %(updated_at)s"]
    params: dict[str, Any] = {
        "id": experiment_id,
        "updated_at": datetime.now(UTC),
        "status": status.value,
    }
    for key, value in fields.items():
        if value is not None:
            set_clauses.append(f"{key} = %({key})s")
            params[key] = value

    sql = f"UPDATE experiments SET {', '.join(set_clauses)} WHERE id = %(id)s"
    _execute(sql, params)
    return get_experiment(experiment_id)


def update_experiment_metrics(
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
) -> Experiment | None:
    set_clauses = ["updated_at = %(updated_at)s"]
    params: dict[str, Any] = {
        "id": experiment_id,
        "updated_at": datetime.now(UTC),
    }

    field_map: dict[str, Any] = {
        "baseline_orders": baseline_orders,
        "baseline_revenue": baseline_revenue,
        "baseline_drr": baseline_drr,
        "current_orders": current_orders,
        "current_revenue": current_revenue,
        "current_drr": current_drr,
        "success_score": success_score,
        "direction_accuracy": direction_accuracy,
        "summary": summary,
    }
    for key, value in field_map.items():
        if value is not None:
            set_clauses.append(f"{key} = %({key})s")
            params[key] = value

    if actual_effect is not None:
        set_clauses.append("actual_effect = %(actual_effect)s::jsonb")
        params["actual_effect"] = json.dumps(actual_effect)

    sql = f"UPDATE experiments SET {', '.join(set_clauses)} WHERE id = %(id)s"
    _execute(sql, params)
    return get_experiment(experiment_id)


def save_experiment_event(event: ExperimentEvent) -> str:
    sql = """
        INSERT INTO experiment_events (
            id, experiment_id, created_at, event_type,
            from_status, to_status, actor, reason, metadata
        ) VALUES (
            %(id)s, %(experiment_id)s, %(created_at)s, %(event_type)s,
            %(from_status)s, %(to_status)s, %(actor)s, %(reason)s,
            %(metadata)s::jsonb
        )
    """
    _execute(sql, {
        "id": event.id,
        "experiment_id": event.experiment_id,
        "created_at": event.created_at,
        "event_type": event.event_type.value,
        "from_status": event.from_status.value if event.from_status else None,
        "to_status": event.to_status.value if event.to_status else None,
        "actor": event.actor,
        "reason": event.reason,
        "metadata": json.dumps(event.metadata),
    })
    return event.id


def list_experiment_events(experiment_id: str) -> list[ExperimentEvent]:
    sql = """
        SELECT * FROM experiment_events
        WHERE experiment_id = %(experiment_id)s
        ORDER BY created_at DESC
    """
    rows = _fetch_all(sql, {"experiment_id": experiment_id})
    return [_row_to_event(row) for row in rows]


def _experiment_record(experiment: Experiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "created_at": experiment.created_at,
        "updated_at": experiment.updated_at,
        "sku": experiment.sku,
        "hypothesis": experiment.hypothesis,
        "action": experiment.action,
        "risk": experiment.risk,
        "confidence": experiment.confidence,
        "status": experiment.status.value,
        "recommendation_id": experiment.recommendation_id,
        "baseline_orders": experiment.baseline_orders,
        "baseline_revenue": experiment.baseline_revenue,
        "baseline_drr": experiment.baseline_drr,
        "current_orders": experiment.current_orders,
        "current_revenue": experiment.current_revenue,
        "current_drr": experiment.current_drr,
        "success_score": experiment.success_score,
        "direction_accuracy": experiment.direction_accuracy,
        "actual_effect": json.dumps(experiment.actual_effect),
        "expected_effect": json.dumps(experiment.expected_effect),
        "metrics": json.dumps(experiment.metrics),
        "summary": experiment.summary,
        "started_at": experiment.started_at,
        "paused_at": experiment.paused_at,
        "completed_at": experiment.completed_at,
        "cancelled_at": experiment.cancelled_at,
        "failed_at": experiment.failed_at,
        "cancel_reason": experiment.cancel_reason,
        "fail_reason": experiment.fail_reason,
        "created_by": experiment.created_by,
    }


def _row_to_experiment(row: dict[str, Any]) -> Experiment:
    return Experiment(
        id=str(row["id"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        sku=str(row["sku"]),
        hypothesis=str(row["hypothesis"]),
        action=str(row["action"]),
        risk=row.get("risk"),
        confidence=row.get("confidence"),
        status=ExperimentStatus(str(row["status"])),
        recommendation_id=row.get("recommendation_id"),
        baseline_orders=float(row.get("baseline_orders") or 0),
        baseline_revenue=float(row.get("baseline_revenue") or 0),
        baseline_drr=float(row.get("baseline_drr") or 0),
        current_orders=float(row.get("current_orders") or 0),
        current_revenue=float(row.get("current_revenue") or 0),
        current_drr=float(row.get("current_drr") or 0),
        success_score=_float_or_none(row.get("success_score")),
        direction_accuracy=_float_or_none(row.get("direction_accuracy")),
        actual_effect=_json_to_dict(row.get("actual_effect")),
        expected_effect=_json_to_dict(row.get("expected_effect")),
        metrics=_json_to_dict(row.get("metrics")),
        summary=row.get("summary"),
        started_at=row.get("started_at"),
        paused_at=row.get("paused_at"),
        completed_at=row.get("completed_at"),
        cancelled_at=row.get("cancelled_at"),
        failed_at=row.get("failed_at"),
        cancel_reason=row.get("cancel_reason"),
        fail_reason=row.get("fail_reason"),
        created_by=str(row.get("created_by") or "system"),
    )


def _row_to_event(row: dict[str, Any]) -> ExperimentEvent:
    return ExperimentEvent(
        id=str(row["id"]),
        experiment_id=str(row["experiment_id"]),
        created_at=row["created_at"],
        event_type=ExperimentEventType(str(row["event_type"])),
        from_status=ExperimentStatus(str(row["from_status"])) if row.get("from_status") else None,
        to_status=ExperimentStatus(str(row["to_status"])) if row.get("to_status") else None,
        actor=row.get("actor"),
        reason=row.get("reason"),
        metadata=_json_to_dict(row.get("metadata")),
    )


def _build_list_query(
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


def _json_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    return dict(json.loads(str(value)))


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


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
