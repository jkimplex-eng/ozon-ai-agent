from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from ozon_agent.approval.models import (
    RecommendationOutcome,
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.approval.serializers import outcome_from_json, recommendation_from_json
from ozon_agent.db.connection import get_connection

ConnectionFactory = Callable[[], Any]

_connection_factory: ConnectionFactory = get_connection


def save_recommendation(recommendation: StoredRecommendation) -> str:
    payload = _recommendation_record(recommendation)
    sql = """
        INSERT INTO recommendations (
            id, created_at, updated_at, sku, product_name, action, reason,
            confidence_score, confidence_level, risk_score, risk_level,
            expected_effect, supporting_metrics, status, approved_by, approved_at,
            rejected_by, rejected_at, rejection_reason, executed_at, observed_at,
            closed_at, source
        ) VALUES (
            %(id)s, %(created_at)s, %(updated_at)s,
            %(sku)s, %(product_name)s, %(action)s, %(reason)s,
            %(confidence_score)s, %(confidence_level)s, %(risk_score)s, %(risk_level)s,
            %(expected_effect)s::jsonb, %(supporting_metrics)s::jsonb,
            %(status)s, %(approved_by)s, %(approved_at)s,
            %(rejected_by)s, %(rejected_at)s, %(rejection_reason)s,
            %(executed_at)s, %(observed_at)s,
            %(closed_at)s, %(source)s
        )
        ON CONFLICT (id) DO UPDATE SET
            updated_at = EXCLUDED.updated_at,
            sku = EXCLUDED.sku,
            product_name = EXCLUDED.product_name,
            action = EXCLUDED.action,
            reason = EXCLUDED.reason,
            confidence_score = EXCLUDED.confidence_score,
            confidence_level = EXCLUDED.confidence_level,
            risk_score = EXCLUDED.risk_score,
            risk_level = EXCLUDED.risk_level,
            expected_effect = EXCLUDED.expected_effect,
            supporting_metrics = EXCLUDED.supporting_metrics,
            status = EXCLUDED.status,
            approved_by = EXCLUDED.approved_by,
            approved_at = EXCLUDED.approved_at,
            rejected_by = EXCLUDED.rejected_by,
            rejected_at = EXCLUDED.rejected_at,
            rejection_reason = EXCLUDED.rejection_reason,
            executed_at = EXCLUDED.executed_at,
            observed_at = EXCLUDED.observed_at,
            closed_at = EXCLUDED.closed_at,
            source = EXCLUDED.source
    """
    _execute(sql, payload)
    return recommendation.id


def get_recommendation(recommendation_id: str) -> StoredRecommendation | None:
    sql = "SELECT * FROM recommendations WHERE id = %(id)s"
    rows = _fetch_all(sql, {"id": recommendation_id})
    if not rows:
        return None
    return _row_to_recommendation(rows[0])


def list_recommendations(
    status: RecommendationStatus | None = None,
    sku: str | None = None,
    limit: int = 50,
) -> list[StoredRecommendation]:
    sql, params = _build_list_recommendations_query(status=status, sku=sku, limit=limit)
    rows = _fetch_all(sql, params)
    return [_row_to_recommendation(row) for row in rows]


def update_recommendation_status(
    recommendation_id: str,
    status: RecommendationStatus,
    *,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    rejected_by: str | None = None,
    rejected_at: datetime | None = None,
    rejection_reason: str | None = None,
    executed_at: datetime | None = None,
    observed_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> StoredRecommendation | None:
    sql = """
        UPDATE recommendations
        SET updated_at = %(updated_at)s,
            status = %(status)s,
            approved_by = COALESCE(%(approved_by)s, approved_by),
            approved_at = COALESCE(%(approved_at)s, approved_at),
            rejected_by = COALESCE(%(rejected_by)s, rejected_by),
            rejected_at = COALESCE(%(rejected_at)s, rejected_at),
            rejection_reason = COALESCE(%(rejection_reason)s, rejection_reason),
            executed_at = COALESCE(%(executed_at)s, executed_at),
            observed_at = COALESCE(%(observed_at)s, observed_at),
            closed_at = COALESCE(%(closed_at)s, closed_at)
        WHERE id = %(id)s
    """
    _execute(
        sql,
        {
            "id": recommendation_id,
            "updated_at": datetime.now(UTC),
            "status": status.value,
            "approved_by": approved_by,
            "approved_at": approved_at,
            "rejected_by": rejected_by,
            "rejected_at": rejected_at,
            "rejection_reason": rejection_reason,
            "executed_at": executed_at,
            "observed_at": observed_at,
            "closed_at": closed_at,
        },
    )
    return get_recommendation(recommendation_id)


def save_outcome(outcome: RecommendationOutcome) -> str:
    sql = """
        INSERT INTO recommendation_outcomes (
            id, recommendation_id, created_at, observation_window_days,
            expected_effect, actual_effect, forecast_error, success_score, notes
        ) VALUES (
            %(id)s, %(recommendation_id)s, %(created_at)s, %(observation_window_days)s,
            %(expected_effect)s::jsonb, %(actual_effect)s::jsonb,
            %(forecast_error)s, %(success_score)s, %(notes)s
        )
        ON CONFLICT (id) DO UPDATE SET
            created_at = EXCLUDED.created_at,
            observation_window_days = EXCLUDED.observation_window_days,
            expected_effect = EXCLUDED.expected_effect,
            actual_effect = EXCLUDED.actual_effect,
            forecast_error = EXCLUDED.forecast_error,
            success_score = EXCLUDED.success_score,
            notes = EXCLUDED.notes
    """
    _execute(
        sql,
        {
            "id": outcome.id,
            "recommendation_id": outcome.recommendation_id,
            "created_at": outcome.created_at,
            "observation_window_days": outcome.observation_window_days,
            "expected_effect": json.dumps(outcome.expected_effect),
            "actual_effect": json.dumps(outcome.actual_effect),
            "forecast_error": outcome.forecast_error,
            "success_score": outcome.success_score,
            "notes": outcome.notes,
        },
    )
    return outcome.id


def list_outcomes(recommendation_id: str) -> list[RecommendationOutcome]:
    sql = """
        SELECT * FROM recommendation_outcomes
        WHERE recommendation_id = %(recommendation_id)s
        ORDER BY created_at DESC
    """
    rows = _fetch_all(sql, {"recommendation_id": recommendation_id})
    return [_row_to_outcome(row) for row in rows]


def _recommendation_record(recommendation: StoredRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "created_at": recommendation.created_at,
        "updated_at": recommendation.updated_at,
        "sku": recommendation.sku,
        "product_name": recommendation.product_name,
        "action": recommendation.action.value,
        "reason": recommendation.reason,
        "confidence_score": recommendation.confidence_score,
        "confidence_level": recommendation.confidence_level.value
        if recommendation.confidence_level is not None
        else None,
        "risk_score": recommendation.risk_score,
        "risk_level": (
            recommendation.risk_level.value if recommendation.risk_level is not None else None
        ),
        "expected_effect": json.dumps(recommendation.expected_effect),
        "supporting_metrics": json.dumps(recommendation.supporting_metrics),
        "status": recommendation.status.value,
        "approved_by": recommendation.approved_by,
        "approved_at": recommendation.approved_at,
        "rejected_by": recommendation.rejected_by,
        "rejected_at": recommendation.rejected_at,
        "rejection_reason": recommendation.rejection_reason,
        "executed_at": recommendation.executed_at,
        "observed_at": recommendation.observed_at,
        "closed_at": recommendation.closed_at,
        "source": recommendation.source,
    }


def _row_to_recommendation(row: dict[str, Any]) -> StoredRecommendation:
    payload = {
        **row,
        "action": row["action"],
        "confidence_level": row.get("confidence_level"),
        "risk_level": row.get("risk_level"),
        "status": row["status"],
        "expected_effect": _json_to_dict(row.get("expected_effect")),
        "supporting_metrics": _json_to_dict(row.get("supporting_metrics")),
    }
    return recommendation_from_json(payload)


def _row_to_outcome(row: dict[str, Any]) -> RecommendationOutcome:
    payload = {
        **row,
        "expected_effect": _json_to_dict(row.get("expected_effect")),
        "actual_effect": _json_to_dict(row.get("actual_effect")),
    }
    return outcome_from_json(payload)


def _json_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    return dict(json.loads(str(value)))


def _build_list_recommendations_query(
    status: RecommendationStatus | None,
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

    sql_lines = ["SELECT * FROM recommendations"]
    if where_clauses:
        sql_lines.append("WHERE " + " AND ".join(where_clauses))
    sql_lines.append("ORDER BY created_at DESC")
    sql_lines.append("LIMIT %(limit)s")
    return "\n".join(sql_lines), params


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
