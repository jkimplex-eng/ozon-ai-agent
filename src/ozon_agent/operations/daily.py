"""Daily Operations Engine — generates daily risks, opportunities, actions, and briefings."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BRIEFINGS_DIR = Path("data/briefings")


@dataclass(frozen=True)
class DailyRisk:
    sku: str
    risk_type: str
    severity: str
    score: float
    reason: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyOpportunity:
    sku: str
    opportunity_type: str
    score: float
    reason: str
    expected_impact: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyAction:
    priority: str
    action: str
    sku: str
    reason: str
    deadline: str
    expected_impact: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyBriefing:
    date: str
    revenue_yesterday: float
    profit_yesterday: float
    orders_yesterday: int
    top_risks: list[DailyRisk]
    top_opportunities: list[DailyOpportunity]
    actions_required: list[DailyAction]
    expected_profit_impact: float
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "revenue_yesterday": self.revenue_yesterday,
            "profit_yesterday": self.profit_yesterday,
            "orders_yesterday": self.orders_yesterday,
            "top_risks": [r.to_dict() for r in self.top_risks],
            "top_opportunities": [o.to_dict() for o in self.top_opportunities],
            "actions_required": [a.to_dict() for a in self.actions_required],
            "expected_profit_impact": self.expected_profit_impact,
            "summary": self.summary,
        }


def _load_daily_data() -> list[dict[str, Any]]:
    """Load daily summary data from files."""
    try:
        from ozon_agent.sheets.file_source import load_sales
        return load_sales() or []
    except Exception:
        return []


def _generate_risks(daily_data: list[dict[str, Any]]) -> list[DailyRisk]:
    """Generate top risks from daily data."""
    risks: list[DailyRisk] = []

    if not daily_data:
        return risks

    for row in daily_data[-7:]:
        sku = str(row.get("sku", ""))
        revenue = float(row.get("revenue", 0))
        margin = float(row.get("margin", 0))
        drr = float(row.get("drr", 0))
        stock_days = row.get("stock_days")

        if margin < 10 and revenue > 0:
            risks.append(DailyRisk(
                sku=sku, risk_type="Low Margin", severity="HIGH",
                score=80.0, reason=f"Margin {margin:.1f}%",
                action="Review pricing or COGS",
            ))

        if drr > 25 and revenue > 0:
            risks.append(DailyRisk(
                sku=sku, risk_type="Ad Waste", severity="MEDIUM",
                score=60.0, reason=f"DRR {drr:.1f}%",
                action="Reduce ad spend or pause campaign",
            ))

        if stock_days is not None and stock_days < 7:
            risks.append(DailyRisk(
                sku=sku, risk_type="Stock Risk", severity="CRITICAL",
                score=90.0, reason=f"Only {stock_days:.0f} days stock",
                action="Reorder immediately",
            ))

    risks.sort(key=lambda r: r.score, reverse=True)
    return risks[:10]


def _generate_opportunities(daily_data: list[dict[str, Any]]) -> list[DailyOpportunity]:
    """Generate top opportunities from daily data."""
    opps: list[DailyOpportunity] = []

    if not daily_data:
        return opps

    for row in daily_data[-7:]:
        sku = str(row.get("sku", ""))
        revenue = float(row.get("revenue", 0))
        margin = float(row.get("margin", 0))
        drr = float(row.get("drr", 0))

        if margin > 40 and revenue > 0:
            opps.append(DailyOpportunity(
                sku=sku, opportunity_type="High Margin", score=75.0,
                reason=f"Margin {margin:.1f}%",
                expected_impact="+15% profit", action="Scale advertising",
            ))

        if drr < 8 and revenue > 10000:
            opps.append(DailyOpportunity(
                sku=sku, opportunity_type="Ad Scale", score=70.0,
                reason=f"DRR {drr:.1f}% with {revenue:.0f} revenue",
                expected_impact="+20% revenue", action="Increase budget",
            ))

    opps.sort(key=lambda o: o.score, reverse=True)
    return opps[:10]


def _generate_actions(
    risks: list[DailyRisk],
    opps: list[DailyOpportunity],
) -> list[DailyAction]:
    """Generate required actions from risks and opportunities."""
    actions: list[DailyAction] = []

    for risk in risks[:5]:
        actions.append(DailyAction(
            priority="HIGH" if risk.severity in ("CRITICAL", "HIGH") else "MEDIUM",
            action=f"Address {risk.risk_type}",
            sku=risk.sku,
            reason=risk.reason,
            deadline="Today",
            expected_impact="Prevent loss",
        ))

    for opp in opps[:3]:
        actions.append(DailyAction(
            priority="MEDIUM",
            action=f"Leverage {opp.opportunity_type}",
            sku=opp.sku,
            reason=opp.reason,
            deadline="This week",
            expected_impact=opp.expected_impact,
        ))

    return actions


def generate_daily_briefing() -> DailyBriefing:
    """Generate complete daily briefing."""
    daily_data = _load_daily_data()
    now = datetime.now(UTC)

    revenue = sum(float(r.get("revenue", 0)) for r in daily_data[-1:])
    profit = sum(float(r.get("profit", 0)) for r in daily_data[-1:])
    orders = sum(int(r.get("orders", 0)) for r in daily_data[-1:])

    risks = _generate_risks(daily_data)
    opps = _generate_opportunities(daily_data)
    actions = _generate_actions(risks, opps)

    risk_impact = sum(r.score * -0.01 for r in risks[:3])
    opp_impact = sum(o.score * 0.01 for o in opps[:3])
    expected_delta = opp_impact + risk_impact

    summary = (
        f"Revenue: {revenue:,.0f} | Profit: {profit:,.0f} | "
        f"Risks: {len(risks)} | Opportunities: {len(opps)} | "
        f"Actions: {len(actions)}"
    )

    return DailyBriefing(
        date=now.strftime("%Y-%m-%d"),
        revenue_yesterday=revenue,
        profit_yesterday=profit,
        orders_yesterday=orders,
        top_risks=risks,
        top_opportunities=opps,
        actions_required=actions,
        expected_profit_impact=expected_delta,
        summary=summary,
    )


def save_briefing(briefing: DailyBriefing) -> Path:
    """Save briefing to disk."""
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEFINGS_DIR / f"briefing_{briefing.date}.json"
    path.write_text(
        json.dumps(briefing.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return path


def format_briefing(briefing: DailyBriefing) -> str:
    """Format briefing for Telegram display."""
    lines = [
        f"DAILY BRIEFING — {briefing.date}",
        "=" * 40,
        "",
        f"Revenue Yesterday: {briefing.revenue_yesterday:,.0f} ₽",
        f"Profit Yesterday:  {briefing.profit_yesterday:,.0f} ₽",
        f"Orders:            {briefing.orders_yesterday}",
        "",
        "TOP RISKS:",
    ]

    for r in briefing.top_risks[:3]:
        lines.append(f"  [{r.severity}] {r.sku}: {r.risk_type} — {r.reason}")

    lines.append("")
    lines.append("TOP OPPORTUNITIES:")
    for o in briefing.top_opportunities[:3]:
        lines.append(f"  {o.sku}: {o.opportunity_type} — {o.expected_impact}")

    lines.append("")
    lines.append("ACTIONS REQUIRED:")
    for a in briefing.actions_required[:5]:
        lines.append(f"  [{a.priority}] {a.action} ({a.sku}) — {a.deadline}")

    lines.append("")
    lines.append(f"Expected Profit Impact: {briefing.expected_profit_impact:+.1f}%")

    return "\n".join(lines)
