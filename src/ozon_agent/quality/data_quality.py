"""Data Quality Engine — tracks data completeness and quality status for all metrics."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

QUALITY_DIR = Path("data/quality")


class DataQualityStatus:
    COMPLETE = "COMPLETE"
    ESTIMATED = "ESTIMATED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class MetricQuality:
    metric: str
    status: str
    source: str
    coverage_pct: float
    last_updated: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataQualityReport:
    generated_at: str
    metrics: list[MetricQuality]
    overall_status: str
    complete_count: int
    estimated_count: int
    partial_count: int
    insufficient_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "complete_count": self.complete_count,
            "estimated_count": self.estimated_count,
            "partial_count": self.partial_count,
            "insufficient_count": self.insufficient_count,
            "metrics": [m.to_dict() for m in self.metrics],
        }


def evaluate_metric_quality(
    metric: str,
    has_data: bool,
    source: str = "unknown",
    coverage_pct: float = 0.0,
    is_estimated: bool = False,
    notes: str = "",
) -> MetricQuality:
    """Evaluate quality status for a single metric."""
    now = datetime.now(UTC).isoformat()

    if not has_data:
        status = DataQualityStatus.INSUFFICIENT
    elif is_estimated:
        status = DataQualityStatus.ESTIMATED
    elif coverage_pct < 80:
        status = DataQualityStatus.PARTIAL
    else:
        status = DataQualityStatus.COMPLETE

    return MetricQuality(
        metric=metric,
        status=status,
        source=source,
        coverage_pct=coverage_pct,
        last_updated=now,
        notes=notes,
    )


def build_quality_report(
    daily_data: list[dict[str, Any]],
    products: list[dict[str, Any]] | None = None,
    stocks: list[dict[str, Any]] | None = None,
    advertising: list[dict[str, Any]] | None = None,
) -> DataQualityReport:
    """Build comprehensive data quality report."""
    now = datetime.now(UTC).isoformat()
    metrics: list[MetricQuality] = []

    has_revenue = (
        any(float(row.get("revenue", 0)) > 0 for row in daily_data)
        if daily_data else False
    )
    metrics.append(evaluate_metric_quality(
        metric="Revenue",
        has_data=has_revenue,
        source="Daily Input",
        coverage_pct=100.0 if has_revenue else 0.0,
    ))

    has_profit = (
        any(float(row.get("profit", 0)) != 0 for row in daily_data)
        if daily_data else False
    )
    metrics.append(evaluate_metric_quality(
        metric="COGS",
        has_data=has_profit,
        source="COGS mapping",
        coverage_pct=90.0 if has_profit else 0.0,
    ))

    has_advertising = bool(advertising) if advertising else False
    metrics.append(evaluate_metric_quality(
        metric="Advertising",
        has_data=has_advertising,
        source="Performance API" if has_advertising else "None",
        coverage_pct=70.0 if has_advertising else 0.0,
        is_estimated=not has_advertising,
        notes="Estimated from daily input" if not has_advertising else "",
    ))

    has_stocks = bool(stocks) if stocks else False
    metrics.append(evaluate_metric_quality(
        metric="Stocks",
        has_data=has_stocks,
        source="Ozon API" if has_stocks else "None",
        coverage_pct=100.0 if has_stocks else 0.0,
    ))

    has_products = bool(products) if products else False
    metrics.append(evaluate_metric_quality(
        metric="Products",
        has_data=has_products,
        source="Ozon API" if has_products else "None",
        coverage_pct=100.0 if has_products else 0.0,
    ))

    has_orders = any(int(row.get("orders", 0)) > 0 for row in daily_data) if daily_data else False
    metrics.append(evaluate_metric_quality(
        metric="Orders",
        has_data=has_orders,
        source="Daily Input",
        coverage_pct=100.0 if has_orders else 0.0,
    ))

    has_margin = has_revenue and has_profit
    metrics.append(evaluate_metric_quality(
        metric="Margin",
        has_data=has_margin,
        source="Calculated",
        coverage_pct=100.0 if has_margin else 0.0,
    ))

    has_drr = has_advertising and has_revenue
    metrics.append(evaluate_metric_quality(
        metric="DRR",
        has_data=has_drr,
        source="Calculated",
        coverage_pct=70.0 if has_drr else 0.0,
        is_estimated=not has_advertising,
    ))

    statuses = [m.status for m in metrics]
    complete_count = statuses.count(DataQualityStatus.COMPLETE)
    estimated_count = statuses.count(DataQualityStatus.ESTIMATED)
    partial_count = statuses.count(DataQualityStatus.PARTIAL)
    insufficient_count = statuses.count(DataQualityStatus.INSUFFICIENT)

    if insufficient_count > 0:
        overall = DataQualityStatus.INSUFFICIENT
    elif partial_count > 0:
        overall = DataQualityStatus.PARTIAL
    elif estimated_count > complete_count:
        overall = DataQualityStatus.ESTIMATED
    else:
        overall = DataQualityStatus.COMPLETE

    return DataQualityReport(
        generated_at=now,
        metrics=metrics,
        overall_status=overall,
        complete_count=complete_count,
        estimated_count=estimated_count,
        partial_count=partial_count,
        insufficient_count=insufficient_count,
    )


def save_quality_report(
    report: DataQualityReport,
    output_dir: str | Path | None = None,
) -> Path:
    """Save quality report to disk."""
    path = Path(output_dir) if output_dir else QUALITY_DIR
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "quality_report.json"
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


def format_quality_report(report: DataQualityReport) -> str:
    """Format quality report for display."""
    lines = [
        "Data Quality Report",
        "=" * 50,
        f"Generated: {report.generated_at}",
        f"Overall Status: {report.overall_status}",
        "",
        f"Complete: {report.complete_count}",
        f"Estimated: {report.estimated_count}",
        f"Partial: {report.partial_count}",
        f"Insufficient: {report.insufficient_count}",
        "",
        "Metrics:",
    ]

    for metric in report.metrics:
        status_symbol = {
            DataQualityStatus.COMPLETE: "[OK]",
            DataQualityStatus.ESTIMATED: "[~]",
            DataQualityStatus.PARTIAL: "[!]",
            DataQualityStatus.INSUFFICIENT: "[X]",
        }.get(metric.status, "[?]")
        coverage = metric.coverage_pct
        lines.append(
            f"  {status_symbol} {metric.metric}: "
            f"{metric.status} ({metric.source}, {coverage:.0f}%)"
        )
        if metric.notes:
            lines.append(f"      Note: {metric.notes}")

    return "\n".join(lines)
