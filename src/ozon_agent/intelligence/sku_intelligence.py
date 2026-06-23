"""SKU Intelligence — comparison, history, risk detection, and opportunity scoring."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/sku_intelligence")


@dataclass(frozen=True)
class SkuMetrics:
    sku: str
    name: str
    revenue: float = 0.0
    profit: float = 0.0
    orders: int = 0
    conversion: float = 0.0
    advertising: float = 0.0
    margin: float = 0.0
    drr: float = 0.0
    trend_revenue_pct: float = 0.0
    trend_orders_pct: float = 0.0
    stock_days: float | None = None
    review_rating: float | None = None
    review_count: int = 0
    period: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuComparison:
    sku1: SkuMetrics
    sku2: SkuMetrics
    metrics_compared: list[str]
    winner: dict[str, str]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku1": self.sku1.to_dict(),
            "sku2": self.sku2.to_dict(),
            "metrics_compared": self.metrics_compared,
            "winner": self.winner,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class SkuHistoryPoint:
    date: str
    revenue: float
    profit: float
    orders: int
    margin: float
    drr: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuHistory:
    sku: str
    period_days: int
    data_points: list[SkuHistoryPoint]
    trend_revenue_pct: float
    trend_profit_pct: float
    trend_orders_pct: float
    average_margin: float
    average_drr: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "period_days": self.period_days,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "trend_revenue_pct": self.trend_revenue_pct,
            "trend_profit_pct": self.trend_profit_pct,
            "trend_orders_pct": self.trend_orders_pct,
            "average_margin": self.average_margin,
            "average_drr": self.average_drr,
        }


@dataclass(frozen=True)
class RiskFactor:
    name: str
    severity: str
    score: float
    reason: str
    metric_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuRisk:
    sku: str
    overall_score: float
    risk_level: str
    factors: list[RiskFactor]
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "factors": [f.to_dict() for f in self.factors],
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True)
class OpportunityFactor:
    name: str
    score: float
    reason: str
    metric_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuOpportunity:
    sku: str
    opportunity_score: float
    factors: list[OpportunityFactor]
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "opportunity_score": self.opportunity_score,
            "factors": [f.to_dict() for f in self.factors],
            "evaluated_at": self.evaluated_at,
        }


def compare_skus(sku1: SkuMetrics, sku2: SkuMetrics) -> SkuComparison:
    """Compare two SKUs across key metrics."""
    metrics = [
        ("revenue", "Revenue"),
        ("profit", "Profit"),
        ("orders", "Orders"),
        ("margin", "Margin"),
        ("drr", "DRR"),
        ("advertising", "Advertising"),
    ]

    winner = {}
    for field_name, label in metrics:
        v1 = getattr(sku1, field_name, 0)
        v2 = getattr(sku2, field_name, 0)
        if field_name == "drr":
            winner[label] = sku1.sku if v1 < v2 else sku2.sku if v2 < v1 else "Tie"
        else:
            winner[label] = sku1.sku if v1 > v2 else sku2.sku if v2 > v1 else "Tie"

    sku1_wins = sum(1 for v in winner.values() if v == sku1.sku)
    sku2_wins = sum(1 for v in winner.values() if v == sku2.sku)

    if sku1_wins > sku2_wins:
        summary = f"{sku1.sku} outperforms {sku2.sku} in {sku1_wins}/{len(metrics)} metrics"
    elif sku2_wins > sku1_wins:
        summary = f"{sku2.sku} outperforms {sku1.sku} in {sku2_wins}/{len(metrics)} metrics"
    else:
        summary = f"{sku1.sku} and {sku2.sku} are evenly matched"

    return SkuComparison(
        sku1=sku1,
        sku2=sku2,
        metrics_compared=[label for _, label in metrics],
        winner=winner,
        summary=summary,
    )


def build_sku_history(
    sku: str,
    daily_data: list[dict[str, Any]],
    period_days: int = 30,
) -> SkuHistory:
    """Build SKU history from daily data."""
    points = []
    for row in daily_data:
        points.append(SkuHistoryPoint(
            date=str(row.get("date", "")),
            revenue=float(row.get("revenue", 0)),
            profit=float(row.get("profit", 0)),
            orders=int(row.get("orders", 0)),
            margin=float(row.get("margin", 0)),
            drr=float(row.get("drr", 0)),
        ))

    if len(points) >= 2:
        first_half = points[:len(points) // 2]
        second_half = points[len(points) // 2:]

        rev_first = sum(p.revenue for p in first_half)
        rev_second = sum(p.revenue for p in second_half)
        trend_rev = ((rev_second - rev_first) / rev_first * 100) if rev_first > 0 else 0

        prof_first = sum(p.profit for p in first_half)
        prof_second = sum(p.profit for p in second_half)
        trend_prof = ((prof_second - prof_first) / prof_first * 100) if prof_first > 0 else 0

        ord_first = sum(p.orders for p in first_half)
        ord_second = sum(p.orders for p in second_half)
        trend_ord = ((ord_second - ord_first) / ord_first * 100) if ord_first > 0 else 0
    else:
        trend_rev = trend_prof = trend_ord = 0

    avg_margin = sum(p.margin for p in points) / len(points) if points else 0
    avg_drr = sum(p.drr for p in points) / len(points) if points else 0

    return SkuHistory(
        sku=sku,
        period_days=period_days,
        data_points=points,
        trend_revenue_pct=trend_rev,
        trend_profit_pct=trend_prof,
        trend_orders_pct=trend_ord,
        average_margin=avg_margin,
        average_drr=avg_drr,
    )


def detect_sku_risk(
    sku: str,
    metrics: SkuMetrics,
) -> SkuRisk:
    """Detect risks for a SKU."""
    factors: list[RiskFactor] = []
    total_score = 0.0

    if metrics.stock_days is not None and metrics.stock_days < 7:
        severity = "CRITICAL" if metrics.stock_days < 3 else "HIGH"
        score = min(100, (7 - metrics.stock_days) * 20)
        factors.append(RiskFactor(
            name="Inventory Risk",
            severity=severity,
            score=score,
            reason=f"Only {metrics.stock_days:.0f} days of stock remaining",
            metric_value=metrics.stock_days,
        ))
        total_score += score

    if metrics.margin < 10:
        severity = "CRITICAL" if metrics.margin < 0 else "HIGH"
        score = min(100, max(0, (10 - metrics.margin) * 10))
        factors.append(RiskFactor(
            name="Margin Collapse",
            severity=severity,
            score=score,
            reason=f"Margin at {metrics.margin:.1f}%",
            metric_value=metrics.margin,
        ))
        total_score += score

    if metrics.trend_revenue_pct < -20:
        severity = "HIGH" if metrics.trend_revenue_pct < -40 else "MEDIUM"
        score = min(100, abs(metrics.trend_revenue_pct))
        factors.append(RiskFactor(
            name="Traffic Collapse",
            severity=severity,
            score=score,
            reason=f"Revenue trend {metrics.trend_revenue_pct:+.1f}%",
            metric_value=metrics.trend_revenue_pct,
        ))
        total_score += score

    if metrics.drr > 30:
        severity = "HIGH" if metrics.drr > 50 else "MEDIUM"
        score = min(100, (metrics.drr - 30) * 2)
        factors.append(RiskFactor(
            name="Advertising Waste",
            severity=severity,
            score=score,
            reason=f"DRR at {metrics.drr:.1f}%",
            metric_value=metrics.drr,
        ))
        total_score += score

    if metrics.review_rating is not None and metrics.review_rating < 4.0:
        severity = "HIGH" if metrics.review_rating < 3.5 else "MEDIUM"
        score = min(100, (4.0 - metrics.review_rating) * 50)
        factors.append(RiskFactor(
            name="Review Deterioration",
            severity=severity,
            score=score,
            reason=f"Rating {metrics.review_rating:.1f}/5.0",
            metric_value=metrics.review_rating,
        ))
        total_score += score

    if factors:
        factor_factor = len(factors) / 5 * 100
        overall = min(100, total_score / max(1, len(factors)) * factor_factor)
    else:
        overall = 0
    if overall >= 70:
        level = "CRITICAL"
    elif overall >= 50:
        level = "HIGH"
    elif overall >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return SkuRisk(
        sku=sku,
        overall_score=overall,
        risk_level=level,
        factors=factors,
        evaluated_at=datetime.now(UTC).isoformat(),
    )


def detect_sku_opportunity(
    sku: str,
    metrics: SkuMetrics,
) -> SkuOpportunity:
    """Detect opportunities for a SKU."""
    factors: list[OpportunityFactor] = []
    total_score = 0.0

    if metrics.trend_revenue_pct > 15:
        score = min(100, metrics.trend_revenue_pct * 2)
        factors.append(OpportunityFactor(
            name="Growing Demand",
            score=score,
            reason=f"Revenue trending {metrics.trend_revenue_pct:+.1f}%",
            metric_value=metrics.trend_revenue_pct,
        ))
        total_score += score

    if metrics.drr < 10 and metrics.advertising > 0:
        score = min(100, (10 - metrics.drr) * 10)
        factors.append(OpportunityFactor(
            name="Low Advertising Pressure",
            score=score,
            reason=f"DRR at {metrics.drr:.1f}% with room to scale",
            metric_value=metrics.drr,
        ))
        total_score += score

    if metrics.margin > 40:
        score = min(100, (metrics.margin - 40) * 2)
        factors.append(OpportunityFactor(
            name="High Margin",
            score=score,
            reason=f"Margin at {metrics.margin:.1f}%",
            metric_value=metrics.margin,
        ))
        total_score += score

    if (metrics.review_rating is not None
            and metrics.review_rating >= 4.5
            and metrics.review_count > 10):
        score = min(100, metrics.review_rating * 15)
        factors.append(OpportunityFactor(
            name="Strong Reviews",
            score=score,
            reason=f"Rating {metrics.review_rating:.1f}/5.0 with {metrics.review_count} reviews",
            metric_value=metrics.review_rating,
        ))
        total_score += score

    if metrics.stock_days is not None and metrics.stock_days > 30:
        score = min(100, (metrics.stock_days - 30) * 2)
        factors.append(OpportunityFactor(
            name="Excess Stock",
            score=score,
            reason=f"{metrics.stock_days:.0f} days of stock — opportunity to promote",
            metric_value=metrics.stock_days,
        ))
        total_score += score

    if factors:
        factor_factor = len(factors) / 5 * 100
        overall = min(100, total_score / max(1, len(factors)) * factor_factor)
    else:
        overall = 0

    return SkuOpportunity(
        sku=sku,
        opportunity_score=overall,
        factors=factors,
        evaluated_at=datetime.now(UTC).isoformat(),
    )


def format_comparison(comp: SkuComparison) -> str:
    """Format comparison for display."""
    lines = [
        f"SKU Comparison: {comp.sku1.sku} vs {comp.sku2.sku}",
        "=" * 50,
        "",
        f"{'Metric':<15} {'SKU 1':>12} {'SKU 2':>12} {'Winner':>15}",
        "-" * 55,
    ]

    for label in comp.metrics_compared:
        v1 = getattr(comp.sku1, label.lower(), 0)
        v2 = getattr(comp.sku2, label.lower(), 0)
        w = comp.winner.get(label, "Tie")
        lines.append(f"{label:<15} {v1:>12.0f} {v2:>12.0f} {w:>15}")

    lines.append("")
    lines.append(f"Summary: {comp.summary}")
    return "\n".join(lines)


def format_history(history: SkuHistory) -> str:
    """Format history for display."""
    lines = [
        f"SKU History: {history.sku} ({history.period_days} days)",
        "=" * 50,
        f"Data points: {len(history.data_points)}",
        f"Revenue trend: {history.trend_revenue_pct:+.1f}%",
        f"Profit trend: {history.trend_profit_pct:+.1f}%",
        f"Orders trend: {history.trend_orders_pct:+.1f}%",
        f"Average margin: {history.average_margin:.1f}%",
        f"Average DRR: {history.average_drr:.1f}%",
        "",
        "Recent data:",
    ]

    for dp in history.data_points[-7:]:
        lines.append(f"  {dp.date}: Rev={dp.revenue:.0f} Prof={dp.profit:.0f} Ord={dp.orders}")

    return "\n".join(lines)


def format_risk(risk: SkuRisk) -> str:
    """Format risk assessment for display."""
    lines = [
        f"SKU Risk: {risk.sku}",
        "=" * 50,
        f"Overall Score: {risk.overall_score:.0f}/100",
        f"Risk Level: {risk.risk_level}",
        "",
        "Risk Factors:",
    ]

    for factor in risk.factors:
        lines.append(
            f"  [{factor.severity}] {factor.name}: "
            f"{factor.reason} (score: {factor.score:.0f})"
        )

    if not risk.factors:
        lines.append("  No significant risks detected")

    return "\n".join(lines)


def format_opportunity(opp: SkuOpportunity) -> str:
    """Format opportunity assessment for display."""
    lines = [
        f"SKU Opportunity: {opp.sku}",
        "=" * 50,
        f"Opportunity Score: {opp.opportunity_score:.0f}/100",
        "",
        "Opportunity Factors:",
    ]

    for factor in opp.factors:
        lines.append(f"  {factor.name}: {factor.reason} (score: {factor.score:.0f})")

    if not opp.factors:
        lines.append("  No significant opportunities detected")

    return "\n".join(lines)
