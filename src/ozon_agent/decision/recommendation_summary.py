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
    if rec.market_signals:
        lines.append("Market signals:")
        for signal in rec.market_signals:
            lines.append(f"  - {signal.get('type')}: {signal.get('message')}")
    if rec.market_risks:
        lines.append("Market risks:")
        for risk in rec.market_risks:
            lines.append(f"  - {risk.get('type')}: {risk.get('message')}")
    if rec.market_opportunities:
        lines.append("Market opportunities:")
        for opportunity in rec.market_opportunities:
            lines.append(f"  - {opportunity.get('type')}: {opportunity.get('message')}")
    if rec.knowledge_signals:
        lines.append("Knowledge signals:")
        for signal in rec.knowledge_signals:
            lines.append(f"  - {signal.get('domain')}: {signal.get('signal')}")
    if rec.knowledge_rules:
        lines.append("Knowledge rules:")
        for rule in rec.knowledge_rules:
            lines.append(f"  - {rule.get('domain')}: {rule.get('title')}")
    if rec.learning_signals:
        lines.append("Learning:")
        for signal in rec.learning_signals:
            lines.append(f"  - {signal.get('message')}")
        lines.append(f"  - historical_success_rate: {rec.historical_success_rate:.0%}")
        if rec.recommended_confidence is not None:
            lines.append(f"  - recommended_confidence: {rec.recommended_confidence:.2f}")
    if rec.similar_experiments:
        lines.append("Similar experiments:")
        for match in rec.similar_experiments:
            lines.append(
                f"  - {match.get('experiment_id')}: "
                f"score={match.get('score')} result={match.get('result')}"
            )
    if rec.memory_signals:
        lines.append("Recommendation memory:")
        for signal in rec.memory_signals:
            lines.append(f"  - {signal.get('message')}")
        lines.append(
            f"  - historical_action_success_rate: "
            f"{rec.historical_action_success_rate:.0%}"
        )
        if rec.memory_confidence is not None:
            lines.append(f"  - memory_confidence: {rec.memory_confidence:.2f}")
    if rec.similar_recommendations:
        lines.append("Similar recommendations:")
        for match in rec.similar_recommendations:
            lines.append(
                f"  - {match.get('record_id')}: "
                f"score={match.get('score')} result={match.get('result')}"
            )
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
        "market_signals": rec.market_signals,
        "market_risks": rec.market_risks,
        "market_opportunities": rec.market_opportunities,
        "knowledge_signals": rec.knowledge_signals,
        "knowledge_rules": rec.knowledge_rules,
        "knowledge_sources": rec.knowledge_sources,
        "learning_signals": rec.learning_signals,
        "similar_experiments": rec.similar_experiments,
        "historical_success_rate": rec.historical_success_rate,
        "learning_insights": rec.learning_insights,
        "recommended_confidence": rec.recommended_confidence,
        "memory_signals": rec.memory_signals,
        "similar_recommendations": rec.similar_recommendations,
        "historical_action_success_rate": rec.historical_action_success_rate,
        "memory_insights": rec.memory_insights,
        "memory_confidence": rec.memory_confidence,
    }
