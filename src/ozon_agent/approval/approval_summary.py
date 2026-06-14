"""Text formatter for approval workflow output."""
from __future__ import annotations

from typing import Any

from ozon_agent.approval.models import (
    RecommendationOutcome,
    RecommendationStatus,
    StoredRecommendation,
)


def format_recommendation_detail(rec: StoredRecommendation) -> str:
    lines = [
        f"ID: {rec.id}",
        f"Status: {rec.status.value}",
        f"SKU: {rec.sku}",
        f"Action: {rec.action.value}",
        f"Expected: {rec.expected_effect}",
        f"Confidence: {rec.confidence_level.value if rec.confidence_level else 'N/A'}"
        f" ({rec.confidence_score:.2f})" if rec.confidence_score is not None else "",
        f"Risk: {rec.risk_level.value if rec.risk_level else 'N/A'}"
        f" ({rec.risk_score:.2f})" if rec.risk_score is not None else "",
        f"Reason: {rec.reason}",
        f"Created: {rec.created_at.isoformat()}",
    ]
    if rec.approved_by:
        lines.append(f"Approved by: {rec.approved_by} at {rec.approved_at}")
    if rec.rejected_by:
        lines.append(f"Rejected by: {rec.rejected_by} at {rec.rejected_at}")
        lines.append(f"Rejection reason: {rec.rejection_reason}")
    if rec.executed_at:
        lines.append(f"Executed: {rec.executed_at}")
    if rec.observed_at:
        lines.append(f"Observed: {rec.observed_at}")
    if rec.closed_at:
        lines.append(f"Closed: {rec.closed_at}")
    lifecycle = _lifecycle(rec)
    lines.append(f"Lifecycle: {lifecycle}")
    return "\n".join(line for line in lines if line)


def format_recommendation_list(recs: list[StoredRecommendation]) -> str:
    if not recs:
        return "No recommendations found."
    lines = [f"Found {len(recs)} recommendation(s):", ""]
    for rec in recs:
        lines.append(
            f"  [{rec.status.value}] {rec.id[:8]}... | "
            f"SKU: {rec.sku} | Action: {rec.action.value}"
        )
    return "\n".join(lines)


def format_outcome_detail(outcome: RecommendationOutcome) -> str:
    lines = [
        f"Outcome ID: {outcome.id}",
        f"Recommendation: {outcome.recommendation_id}",
        f"Window: {outcome.observation_window_days} days",
        f"Expected: {outcome.expected_effect}",
        f"Actual: {outcome.actual_effect}",
        f"Forecast error: {outcome.forecast_error}",
        f"Success score: {outcome.success_score}",
    ]
    if outcome.notes:
        lines.append(f"Notes: {outcome.notes}")
    return "\n".join(lines)


def recommendation_to_dict(rec: StoredRecommendation) -> dict[str, Any]:
    return {
        "id": rec.id,
        "status": rec.status.value,
        "sku": rec.sku,
        "action": rec.action.value,
        "reason": rec.reason,
        "confidence_score": rec.confidence_score,
        "confidence_level": rec.confidence_level.value if rec.confidence_level else None,
        "risk_score": rec.risk_score,
        "risk_level": rec.risk_level.value if rec.risk_level else None,
        "expected_effect": rec.expected_effect,
        "created_at": rec.created_at.isoformat(),
        "approved_by": rec.approved_by,
        "rejected_by": rec.rejected_by,
        "rejection_reason": rec.rejection_reason,
        "lifecycle": _lifecycle(rec),
    }


def _lifecycle(rec: StoredRecommendation) -> str:
    states = []
    states.append("created")
    if rec.status in (
        RecommendationStatus.APPROVED,
        RecommendationStatus.EXECUTED,
        RecommendationStatus.OBSERVED,
        RecommendationStatus.CLOSED,
    ):
        states.append("approved")
    if rec.status in (
        RecommendationStatus.EXECUTED,
        RecommendationStatus.OBSERVED,
        RecommendationStatus.CLOSED,
    ):
        states.append("executed")
    if rec.status in (RecommendationStatus.OBSERVED, RecommendationStatus.CLOSED):
        states.append("observed")
    if rec.status == RecommendationStatus.CLOSED:
        states.append("closed")
    if rec.status == RecommendationStatus.REJECTED:
        states.append("rejected")
    return " -> ".join(states)
