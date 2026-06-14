from __future__ import annotations

from datetime import datetime
from typing import Any

from ozon_agent.approval.models import (
    RecommendationOutcome,
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel


def recommendation_to_json(recommendation: StoredRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "created_at": recommendation.created_at.isoformat(),
        "updated_at": recommendation.updated_at.isoformat(),
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
        "expected_effect": recommendation.expected_effect,
        "supporting_metrics": recommendation.supporting_metrics,
        "status": recommendation.status.value,
        "approved_by": recommendation.approved_by,
        "approved_at": _datetime_or_none(recommendation.approved_at),
        "rejected_by": recommendation.rejected_by,
        "rejected_at": _datetime_or_none(recommendation.rejected_at),
        "rejection_reason": recommendation.rejection_reason,
        "executed_at": _datetime_or_none(recommendation.executed_at),
        "observed_at": _datetime_or_none(recommendation.observed_at),
        "closed_at": _datetime_or_none(recommendation.closed_at),
        "source": recommendation.source,
        "campaign_id": recommendation.campaign_id,
    }


def recommendation_from_json(payload: dict[str, Any]) -> StoredRecommendation:
    return StoredRecommendation(
        id=str(payload["id"]),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        sku=str(payload["sku"]),
        product_name=_string_or_none(payload.get("product_name")),
        action=RecommendationAction(str(payload["action"])),
        reason=str(payload["reason"]),
        confidence_score=_float_or_none(payload.get("confidence_score")),
        confidence_level=_enum_or_none(ConfidenceLevel, payload.get("confidence_level")),
        risk_score=_float_or_none(payload.get("risk_score")),
        risk_level=_enum_or_none(RiskLevel, payload.get("risk_level")),
        expected_effect=_dict_or_empty(payload.get("expected_effect")),
        supporting_metrics=_dict_or_empty(payload.get("supporting_metrics")),
        status=RecommendationStatus(str(payload["status"])),
        approved_by=_string_or_none(payload.get("approved_by")),
        approved_at=_parse_datetime_or_none(payload.get("approved_at")),
        rejected_by=_string_or_none(payload.get("rejected_by")),
        rejected_at=_parse_datetime_or_none(payload.get("rejected_at")),
        rejection_reason=_string_or_none(payload.get("rejection_reason")),
        executed_at=_parse_datetime_or_none(payload.get("executed_at")),
        observed_at=_parse_datetime_or_none(payload.get("observed_at")),
        closed_at=_parse_datetime_or_none(payload.get("closed_at")),
        source=_string_or_none(payload.get("source")),
        campaign_id=_string_or_none(payload.get("campaign_id")),
    )


def outcome_to_json(outcome: RecommendationOutcome) -> dict[str, Any]:
    return {
        "id": outcome.id,
        "recommendation_id": outcome.recommendation_id,
        "created_at": outcome.created_at.isoformat(),
        "observation_window_days": outcome.observation_window_days,
        "expected_effect": outcome.expected_effect,
        "actual_effect": outcome.actual_effect,
        "forecast_error": outcome.forecast_error,
        "success_score": outcome.success_score,
        "notes": outcome.notes,
    }


def outcome_from_json(payload: dict[str, Any]) -> RecommendationOutcome:
    return RecommendationOutcome(
        id=str(payload["id"]),
        recommendation_id=str(payload["recommendation_id"]),
        created_at=_parse_datetime(payload["created_at"]),
        observation_window_days=int(payload["observation_window_days"]),
        expected_effect=_dict_or_empty(payload.get("expected_effect")),
        actual_effect=_dict_or_empty(payload.get("actual_effect")),
        forecast_error=_float_or_none(payload.get("forecast_error")),
        success_score=_float_or_none(payload.get("success_score")),
        notes=_string_or_none(payload.get("notes")),
    )


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
