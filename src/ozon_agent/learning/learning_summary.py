"""Text formatter for learning reports."""
from __future__ import annotations

from typing import Any

from ozon_agent.learning.models import (
    BacktestResult,
    CalibrationResult,
    RecommendationAccuracy,
)


def format_accuracy(acc: RecommendationAccuracy) -> str:
    lines = [
        f"  Samples: {acc.total_samples}",
        f"  Comparable metrics: {acc.comparable_metrics}",
        f"  Average error: {acc.average_percentage_error:.1f}%",
        f"  Direction accuracy: {acc.direction_accuracy:.1%}",
        f"  Success rate: {acc.success_rate:.1%}",
    ]
    return "\n".join(lines)


def format_calibration(cal: CalibrationResult) -> str:
    lines = [
        "Overall Accuracy:",
        format_accuracy(cal.overall_accuracy),
        "",
        f"Calibration factor: {cal.overall_factor:.2f}",
    ]
    if cal.reasons:
        lines.append("Reasons:")
        for r in cal.reasons:
            lines.append(f"  - {r}")
    if cal.by_action:
        lines.append("")
        lines.append("By Action:")
        for key, c in cal.by_action.items():
            lines.append(
                f"  {key}: factor={c.calibration_factor:.2f}, "
                f"err={c.average_error:.1f}%, dir={c.direction_accuracy:.0%} "
                f"(n={c.sample_size})"
            )
    return "\n".join(lines)


def format_backtest(bt: BacktestResult) -> str:
    lines = [
        f"Total recommendations: {bt.total_recommendations}",
        f"Successful: {bt.successful_recommendations} ({bt.success_rate:.1%})",
        f"Average error: {bt.average_error:.1f}%",
        f"Median error: {bt.median_error:.1f}%",
        f"Direction accuracy: {bt.direction_accuracy:.1%}",
        f"Estimated profit lift: {bt.estimated_profit_lift:.2f}",
    ]
    if bt.by_action:
        lines.append("")
        lines.append("By Action:")
        for key, acc in bt.by_action.items():
            lines.append(
                f"  {key}: err={acc.average_percentage_error:.1f}%, "
                f"dir={acc.direction_accuracy:.0%} (n={acc.total_samples})"
            )
    return "\n".join(lines)


def format_learning_report(
    accuracy: RecommendationAccuracy,
    calibration: CalibrationResult | None = None,
    backtest: BacktestResult | None = None,
    by_action: dict[str, RecommendationAccuracy] | None = None,
    by_sku: dict[str, RecommendationAccuracy] | None = None,
) -> str:
    sections = [
        "=" * 60,
        "LEARNING REPORT",
        "=" * 60,
        "",
        "Overall Accuracy:",
        format_accuracy(accuracy),
    ]
    if calibration:
        sections.extend(["", format_calibration(calibration)])
    if backtest:
        sections.extend(["", "Backtest Summary:", format_backtest(backtest)])
    if by_action:
        sections.append("")
        sections.append("Accuracy by Action:")
        for key, acc in by_action.items():
            sections.append(
                f"  {key}: err={acc.average_percentage_error:.1f}%, "
                f"dir={acc.direction_accuracy:.0%} (n={acc.total_samples})"
            )
    if by_sku:
        sections.append("")
        sections.append("Accuracy by SKU:")
        for key, acc in list(by_sku.items())[:10]:
            sections.append(
                f"  {key}: err={acc.average_percentage_error:.1f}%, "
                f"dir={acc.direction_accuracy:.0%} (n={acc.total_samples})"
            )
    sections.extend([
        "",
        "Risks and Limitations:",
        "  - Small sample sizes reduce calibration reliability",
        "  - Historical accuracy does not guarantee future performance",
        "  - Learning is read-only, no Ozon actions executed",
        "=" * 60,
    ])
    return "\n".join(sections)


def learning_report_to_dict(
    accuracy: RecommendationAccuracy,
    calibration: CalibrationResult | None = None,
    backtest: BacktestResult | None = None,
    by_action: dict[str, RecommendationAccuracy] | None = None,
    by_sku: dict[str, RecommendationAccuracy] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "accuracy": {
            "total_samples": accuracy.total_samples,
            "average_percentage_error": accuracy.average_percentage_error,
            "direction_accuracy": accuracy.direction_accuracy,
            "success_rate": accuracy.success_rate,
        },
    }
    if calibration:
        result["calibration"] = {
            "overall_factor": calibration.overall_factor,
            "reasons": calibration.reasons,
            "by_action": {
                k: {
                    "calibration_factor": v.calibration_factor,
                    "average_error": v.average_error,
                    "sample_size": v.sample_size,
                }
                for k, v in calibration.by_action.items()
            },
        }
    if backtest:
        result["backtest"] = {
            "total": backtest.total_recommendations,
            "successful": backtest.successful_recommendations,
            "success_rate": backtest.success_rate,
            "average_error": backtest.average_error,
            "direction_accuracy": backtest.direction_accuracy,
        }
    if by_action:
        result["by_action"] = {
            k: {
                "error": v.average_percentage_error,
                "direction": v.direction_accuracy,
                "samples": v.total_samples,
            }
            for k, v in by_action.items()
        }
    if by_sku:
        result["by_sku"] = {
            k: {
                "error": v.average_percentage_error,
                "direction": v.direction_accuracy,
                "samples": v.total_samples,
            }
            for k, v in by_sku.items()
        }
    return result
