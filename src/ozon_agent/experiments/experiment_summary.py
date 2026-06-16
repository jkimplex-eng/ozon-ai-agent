from __future__ import annotations

from typing import Any

from ozon_agent.experiments.models import Experiment


def format_experiment_list(experiments: list[Experiment]) -> str:
    if not experiments:
        return "No experiments found."
    lines = [f"Found {len(experiments)} experiment(s):", ""]
    for exp in experiments:
        lines.append(
            f"  [{exp.status.value}] {exp.id[:8]}... | "
            f"SKU: {exp.sku} | Action: {exp.action}"
        )
    return "\n".join(lines)


def format_experiment_detail(exp: Experiment) -> str:
    lines = [
        f"ID: {exp.id}",
        f"Status: {exp.status.value}",
        f"SKU: {exp.sku}",
        f"Hypothesis: {exp.hypothesis}",
        f"Action: {exp.action}",
        f"Risk: {exp.risk or 'N/A'}",
        f"Confidence: {exp.confidence or 'N/A'}",
        f"Created: {exp.created_at.isoformat()}",
        f"Created by: {exp.created_by}",
    ]
    if exp.recommendation_id:
        lines.append(f"Recommendation: {exp.recommendation_id}")
    if exp.started_at:
        lines.append(f"Started: {exp.started_at.isoformat()}")
    if exp.completed_at:
        lines.append(f"Completed: {exp.completed_at.isoformat()}")
    if exp.cancelled_at:
        lines.append(f"Cancelled: {exp.cancelled_at.isoformat()}")
        if exp.cancel_reason:
            lines.append(f"Cancel reason: {exp.cancel_reason}")
    if exp.failed_at:
        lines.append(f"Failed: {exp.failed_at.isoformat()}")
        if exp.fail_reason:
            lines.append(f"Fail reason: {exp.fail_reason}")
    if exp.paused_at:
        lines.append(f"Paused: {exp.paused_at.isoformat()}")
    lines.append(f"Lifecycle: {_lifecycle(exp)}")
    return "\n".join(lines)


def format_experiment_report(exp: Experiment) -> str:
    lines = [
        "=" * 50,
        "EXPERIMENT REPORT",
        "=" * 50,
        f"ID: {exp.id}",
        f"SKU: {exp.sku}",
        f"Status: {exp.status.value}",
        f"Hypothesis: {exp.hypothesis}",
        f"Action: {exp.action}",
        f"Risk: {exp.risk or 'N/A'}",
        f"Confidence: {exp.confidence or 'N/A'}",
        "",
        "Baseline:",
        f"  orders: {exp.baseline_orders:.2f}",
        f"  revenue: {exp.baseline_revenue:.2f}",
        f"  drr: {exp.baseline_drr:.4f}",
        "",
        "Current/Final:",
        f"  orders: {exp.current_orders:.2f}",
        f"  revenue: {exp.current_revenue:.2f}",
        f"  drr: {exp.current_drr:.4f}",
        "",
        "Result:",
        f"  success_score: {exp.success_score:.4f}" if exp.success_score is not None
        else "  success_score: N/A",
        f"  direction_accuracy: {exp.direction_accuracy:.4f}"
        if exp.direction_accuracy is not None
        else "  direction_accuracy: N/A",
        f"  actual_effect: {exp.actual_effect}",
        f"  summary: {exp.summary or 'N/A'}",
        "=" * 50,
    ]
    return "\n".join(lines)


def experiment_to_dict(exp: Experiment) -> dict[str, Any]:
    return {
        "id": exp.id,
        "status": exp.status.value,
        "sku": exp.sku,
        "hypothesis": exp.hypothesis,
        "action": exp.action,
        "risk": exp.risk,
        "confidence": exp.confidence,
        "recommendation_id": exp.recommendation_id,
        "baseline_orders": exp.baseline_orders,
        "baseline_revenue": exp.baseline_revenue,
        "baseline_drr": exp.baseline_drr,
        "current_orders": exp.current_orders,
        "current_revenue": exp.current_revenue,
        "current_drr": exp.current_drr,
        "success_score": exp.success_score,
        "direction_accuracy": exp.direction_accuracy,
        "actual_effect": exp.actual_effect,
        "expected_effect": exp.expected_effect,
        "summary": exp.summary,
        "created_at": exp.created_at.isoformat(),
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
        "cancelled_at": exp.cancelled_at.isoformat() if exp.cancelled_at else None,
        "failed_at": exp.failed_at.isoformat() if exp.failed_at else None,
        "cancel_reason": exp.cancel_reason,
        "fail_reason": exp.fail_reason,
        "created_by": exp.created_by,
        "lifecycle": _lifecycle(exp),
    }


def _lifecycle(exp: Experiment) -> str:
    states = ["created"]
    if exp.status.value in ("READY", "RUNNING", "PAUSED", "COMPLETED", "CANCELLED", "FAILED"):
        states.append("ready")
    if exp.status.value in ("RUNNING", "PAUSED", "COMPLETED", "CANCELLED", "FAILED"):
        states.append("running")
    if exp.status.value == "PAUSED":
        states.append("paused")
    if exp.status.value == "COMPLETED":
        states.append("completed")
    if exp.status.value == "CANCELLED":
        states.append("cancelled")
    if exp.status.value == "FAILED":
        states.append("failed")
    return " -> ".join(states)
