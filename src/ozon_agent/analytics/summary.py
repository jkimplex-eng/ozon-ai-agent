"""Analytics summary generation."""
from datetime import datetime
from typing import Any

import pandas as pd

from .diagnostics import run_full_diagnostics
from .factors import generate_factor_report
from .metrics import calculate_daily_pnl, calculate_sku_metrics, calculate_trends


def generate_analytics_summary(
    products_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    advertising_df: pd.DataFrame,
    finance_df: pd.DataFrame,
    review_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Generate comprehensive analytics summary."""
    # SKU metrics
    sku_metrics = calculate_sku_metrics(
        products_df, sales_df, advertising_df, review_df
    )

    # Daily P&L
    daily_pnl = calculate_daily_pnl(
        sales_df, finance_df, advertising_df, products_df
    )

    # Trends
    trends = calculate_trends(sku_metrics)

    # Factor analysis
    # Merge data for factor analysis
    if not sales_df.empty and not advertising_df.empty:
        merged = sales_df.merge(
            advertising_df[["product_id", "date", "spend", "impressions", "clicks", "ctr"]],
            on=["product_id", "date"],
            how="left",
            suffixes=("_sales", "_ads"),
        )
    else:
        merged = sales_df.copy()

    factor_report = generate_factor_report(merged)

    # Diagnostics
    diagnostics = run_full_diagnostics(sales_df)

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": trends,
        "sku_metrics": [
            {
                "product_id": m.product_id,
                "offer_id": m.offer_id,
                "sku": m.sku,
                "name": m.name,
                "revenue": m.total_revenue,
                "quantity": m.total_quantity,
                "spend": m.total_spend,
                "drr": m.drr,
                "rating": m.avg_rating,
                "reviews": m.total_reviews,
                "stock_days": m.stock_days,
                "gross_profit": m.gross_profit,
                "margin": m.margin,
            }
            for m in sku_metrics[:50]
        ],
        "daily_pnl": [
            {
                "date": d.date,
                "revenue": d.revenue,
                "quantity": d.quantity,
                "advertising": d.advertising,
                "commission": d.commission,
                "logistics": d.logistics,
                "cogs": d.cogs,
                "gross_profit": d.gross_profit,
            }
            for d in daily_pnl
        ],
        "factor_analysis": factor_report,
        "diagnostics": diagnostics,
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    """Format summary as readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("OZON AI AGENT - ANALYTICS SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Generated: {summary.get('generated_at', 'N/A')}")
    lines.append("")

    # Summary metrics
    s = summary.get("summary", {})
    lines.append("OVERVIEW:")
    lines.append(f"  Total Revenue: {s.get('total_revenue', 0):,.2f} ₽")
    lines.append(f"  Total Quantity: {s.get('total_quantity', 0)}")
    lines.append(f"  Total Ad Spend: {s.get('total_spend', 0):,.2f} ₽")
    lines.append(f"  Avg DRR: {s.get('avg_drr', 0):.1f}%")
    lines.append(f"  Avg Margin: {s.get('avg_margin', 0):.1f}%")
    lines.append(f"  SKUs: {s.get('total_skus', 0)} ({s.get('profitable_skus', 0)} profitable)")
    lines.append("")

    # Top SKUs
    skus = summary.get("sku_metrics", [])
    if skus:
        lines.append("TOP 10 SKUs BY REVENUE:")
        header = f"  {'SKU':<15} {'Revenue':>12} {'Qty':>6} {'DRR':>6}"
        header += f" {'Margin':>8} {'GP':>12}"
        lines.append(header)
        lines.append("  " + "-" * 65)
        for m in skus[:10]:
            lines.append(
                f"  {m['sku']:<15} {m['revenue']:>12,.2f} {m['quantity']:>6} "
                f"{m['drr']:>5.1f}% {m['margin']:>7.1f}% {m['gross_profit']:>12,.2f}"
            )
        lines.append("")

    # Diagnostics
    diag = summary.get("diagnostics", {})
    lines.append(f"DIAGNOSTICS: {diag.get('passed', 0)} passed, "
                 f"{diag.get('warnings', 0)} warnings, "
                 f"{diag.get('failed', 0)} failed")

    return "\n".join(lines)
