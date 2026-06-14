"""Text formatter for recommendation output."""
from __future__ import annotations

from typing import Any

from ozon_agent.decision.models import Recommendation


def format_recommendation_text(rec: Recommendation) -> str:
    lines = [
        f"SKU: {rec.sku}",
        f"Action: {rec.action.value}",
        f"Expected effect: {rec.expected_effect}",
        f"Confidence: {rec.confidence.level.value} ({rec.confidence.score:.2f})",
        f"Risk: {rec.risk.level.value} ({rec.risk.score:.2f})",
        f"Reason: {rec.reason}",
        "Supporting metrics:",
    ]
    for key, value in rec.supporting_metrics.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def format_recommendations_text(recs: list[Recommendation]) -> str:
    if not recs:
        return "No recommendations generated."
    parts = [format_recommendation_text(rec) for rec in recs]
    return "\n\n".join(parts)


def recommendation_to_dict(rec: Recommendation) -> dict[str, Any]:
    return {
        "sku": rec.sku,
        "action": rec.action.value,
        "expected_effect": rec.expected_effect,
        "confidence": {
            "score": rec.confidence.score,
            "level": rec.confidence.level.value,
            "reasons": rec.confidence.reasons,
        },
        "risk": {
            "level": rec.risk.level.value,
            "score": rec.risk.score,
            "reasons": rec.risk.reasons,
        },
        "reason": rec.reason,
        "supporting_metrics": rec.supporting_metrics,
        "created_at": rec.created_at,
        "opportunity_type": rec.opportunity_type.value,
        "campaign_id": rec.campaign_id,
        "impact_score": rec.impact_score,
    }
