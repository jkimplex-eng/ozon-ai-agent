"""COGS coverage analysis."""
from __future__ import annotations

from typing import Any

from ozon_agent.cogs.models import CogsCoverageReport
from ozon_agent.cogs.repository import list_records


def calculate_coverage(products: list[dict[str, Any]]) -> CogsCoverageReport:
    """Calculate COGS coverage for a product list."""
    total = len(products)
    existing_cogs = {r.sku for r in list_records()}

    with_cogs = 0
    missing_skus: list[str] = []

    for p in products:
        sku = p.get("sku", "")
        if not sku:
            continue
        if sku in existing_cogs:
            with_cogs += 1
        else:
            missing_skus.append(sku)

    without_cogs = total - with_cogs
    coverage_pct = (with_cogs / total * 100) if total > 0 else 0.0

    return CogsCoverageReport(
        total_products=total,
        with_cogs=with_cogs,
        without_cogs=without_cogs,
        coverage_pct=round(coverage_pct, 1),
        missing_skus=missing_skus[:20],
    )


def format_coverage_report(report: CogsCoverageReport) -> str:
    """Format coverage report as readable text."""
    lines = [
        f"COGS coverage: {report.coverage_pct}%",
        f"Products with COGS: {report.with_cogs}",
        f"Products without COGS: {report.without_cogs}",
    ]

    if report.missing_skus:
        lines.append("")
        lines.append("Missing COGS:")
        for sku in report.missing_skus[:10]:
            lines.append(f"  - SKU {sku}")

    return "\n".join(lines)
