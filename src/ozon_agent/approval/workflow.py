from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.approval.models import (
    InvalidRecommendationTransitionError,
    RecommendationNotFoundError,
    RecommendationStatus,
    StoredRecommendation,
    build_stored_recommendation,
)
from ozon_agent.approval.repository import (
    get_recommendation,
    save_recommendation,
    update_recommendation_status,
)
from ozon_agent.decision.models import Recommendation


def create_pending_recommendation(
    recommendation: Recommendation,
    source: str = "decision_engine",
) -> StoredRecommendation:
    stored = build_stored_recommendation(recommendation, source=source)
    save_recommendation(stored)
    return stored


def approve_recommendation(recommendation_id: str, approved_by: str) -> StoredRecommendation:
    current = _require_recommendation(recommendation_id)
    _ensure_transition(current, RecommendationStatus.APPROVED)
    updated = update_recommendation_status(
        recommendation_id,
        RecommendationStatus.APPROVED,
        approved_by=approved_by,
        approved_at=datetime.now(UTC),
    )
    return _require_updated(updated, recommendation_id)


def reject_recommendation(
    recommendation_id: str,
    rejected_by: str,
    reason: str,
) -> StoredRecommendation:
    current = _require_recommendation(recommendation_id)
    _ensure_transition(current, RecommendationStatus.REJECTED)
    updated = update_recommendation_status(
        recommendation_id,
        RecommendationStatus.REJECTED,
        rejected_by=rejected_by,
        rejected_at=datetime.now(UTC),
        rejection_reason=reason,
    )
    return _require_updated(updated, recommendation_id)


def mark_executed(recommendation_id: str) -> StoredRecommendation:
    current = _require_recommendation(recommendation_id)
    _ensure_transition(current, RecommendationStatus.EXECUTED)
    updated = update_recommendation_status(
        recommendation_id,
        RecommendationStatus.EXECUTED,
        executed_at=datetime.now(UTC),
    )
    return _require_updated(updated, recommendation_id)


def mark_observed(recommendation_id: str) -> StoredRecommendation:
    current = _require_recommendation(recommendation_id)
    _ensure_transition(current, RecommendationStatus.OBSERVED)
    updated = update_recommendation_status(
        recommendation_id,
        RecommendationStatus.OBSERVED,
        observed_at=datetime.now(UTC),
    )
    return _require_updated(updated, recommendation_id)


def close_recommendation(recommendation_id: str) -> StoredRecommendation:
    current = _require_recommendation(recommendation_id)
    _ensure_transition(current, RecommendationStatus.CLOSED)
    updated = update_recommendation_status(
        recommendation_id,
        RecommendationStatus.CLOSED,
        closed_at=datetime.now(UTC),
    )
    return _require_updated(updated, recommendation_id)


def _require_recommendation(recommendation_id: str) -> StoredRecommendation:
    recommendation = get_recommendation(recommendation_id)
    if recommendation is None:
        raise RecommendationNotFoundError(recommendation_id)
    return recommendation


def _require_updated(
    recommendation: StoredRecommendation | None,
    recommendation_id: str,
) -> StoredRecommendation:
    if recommendation is None:
        raise RecommendationNotFoundError(recommendation_id)
    return recommendation


def _ensure_transition(
    recommendation: StoredRecommendation,
    target: RecommendationStatus,
) -> None:
    allowed = {
        RecommendationStatus.PENDING: {
            RecommendationStatus.APPROVED,
            RecommendationStatus.REJECTED,
        },
        RecommendationStatus.APPROVED: {RecommendationStatus.EXECUTED},
        RecommendationStatus.EXECUTED: {RecommendationStatus.OBSERVED},
        RecommendationStatus.OBSERVED: {RecommendationStatus.CLOSED},
        RecommendationStatus.REJECTED: set(),
        RecommendationStatus.CLOSED: set(),
    }
    if target not in allowed[recommendation.status]:
        raise InvalidRecommendationTransitionError(recommendation.id, recommendation.status, target)
