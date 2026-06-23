"""Management Cockpit — Executive dashboard for revenue, profit, risks."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import gspread

logger = logging.getLogger(__name__)

COCKPIT_TAB = "Management Cockpit"

SECTIONS: dict[str, dict[str, Any]] = {
    "revenue": {
        "title": "Revenue",
        "headers": ["Metric", "Value", "Plan", "Deviation", "Status"],
    },
    "profit": {
        "title": "Profit",
        "headers": ["Metric", "Value", "Plan", "Deviation", "Status"],
    },
    "advertising": {
        "title": "Advertising",
        "headers": ["Metric", "Value", "Target", "Status"],
    },
    "risks": {
        "title": "Top 10 Risks",
        "headers": ["SKU", "Risk Type", "Severity", "Score", "Action Required"],
    },
    "opportunities": {
        "title": "Top 10 Opportunities",
        "headers": ["SKU", "Opportunity", "Score", "Expected Impact", "Action"],
    },
    "actions": {
        "title": "Actions Required",
        "headers": ["Priority", "Action", "SKU", "Reason", "Deadline"],
    },
}


@dataclass(frozen=True)
class CockpitMetric:
    name: str
    value: float
    plan: float | None = None
    deviation_pct: float | None = None
    status: str = "OK"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CockpitRisk:
    sku: str
    risk_type: str
    severity: str
    score: float
    action_required: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CockpitOpportunity:
    sku: str
    opportunity: str
    score: float
    expected_impact: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CockpitAction:
    priority: str
    action: str
    sku: str
    reason: str
    deadline: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManagementCockpit:
    generated_at: str
    revenue: list[CockpitMetric]
    profit: list[CockpitMetric]
    advertising: list[CockpitMetric]
    risks: list[CockpitRisk]
    opportunities: list[CockpitOpportunity]
    actions: list[CockpitAction]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "revenue": [m.to_dict() for m in self.revenue],
            "profit": [m.to_dict() for m in self.profit],
            "advertising": [m.to_dict() for m in self.advertising],
            "risks": [r.to_dict() for r in self.risks],
            "opportunities": [o.to_dict() for o in self.opportunities],
            "actions": [a.to_dict() for a in self.actions],
        }


def _write_section(
    ws: gspread.Worksheet,
    start_row: int,
    section_key: str,
    data: list[Any],
) -> int:
    """Write a section to the worksheet. Returns next available row."""
    section = SECTIONS[section_key]

    ws.update_cell(start_row, 1, section["title"])
    ws.format(f"A{start_row}", {"textFormat": {"bold": True, "fontSize": 12}})

    headers = section["headers"]
    for col, header in enumerate(headers, 1):
        ws.update_cell(start_row + 1, col, header)
    ws.format(
        f"A{start_row + 1}:{chr(64 + len(headers))}{start_row + 1}",
        {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}},
    )

    current_row = start_row + 2
    for item in data:
        item_dict = item.to_dict() if hasattr(item, "to_dict") else item
        values = [item_dict.get(h.lower().replace(" ", "_"), "") for h in headers]
        for col, value in enumerate(values, 1):
            ws.update_cell(current_row, col, str(value) if value is not None else "")
        current_row += 1

    return current_row + 1


def export_cockpit(
    ws: gspread.Worksheet,
    cockpit: ManagementCockpit,
    use_files: bool = False,
) -> int:
    """Export management cockpit to worksheet."""
    ws.clear()

    ws.update_cell(1, 1, "Management Cockpit")
    ws.format("A1", {"textFormat": {"bold": True, "fontSize": 14}})

    ws.update_cell(2, 1, f"Generated: {cockpit.generated_at}")
    ws.format("A2", {"textFormat": {"italic": True}})

    current_row = 4

    current_row = _write_section(ws, current_row, "revenue", cockpit.revenue)
    current_row = _write_section(ws, current_row, "profit", cockpit.profit)
    current_row = _write_section(ws, current_row, "advertising", cockpit.advertising)
    current_row = _write_section(ws, current_row, "risks", cockpit.risks)
    current_row = _write_section(ws, current_row, "opportunities", cockpit.opportunities)
    current_row = _write_section(ws, current_row, "actions", cockpit.actions)

    return current_row


def build_cockpit_from_data(
    daily_summary: list[dict[str, Any]],
    risks: list[dict[str, Any]] | None = None,
    opportunities: list[dict[str, Any]] | None = None,
) -> ManagementCockpit:
    """Build management cockpit from available data."""
    now = datetime.now(UTC).isoformat()

    revenue_metrics = []
    profit_metrics = []
    advertising_metrics = []

    if daily_summary:
        total_revenue = sum(float(row.get("revenue", 0)) for row in daily_summary)
        total_profit = sum(float(row.get("profit", 0)) for row in daily_summary)
        total_advertising = sum(float(row.get("advertising", 0)) for row in daily_summary)
        total_orders = sum(int(row.get("orders", 0)) for row in daily_summary)
        avg_margin = total_profit / total_revenue * 100 if total_revenue > 0 else 0
        avg_drr = total_advertising / total_revenue * 100 if total_revenue > 0 else 0

        margin_status = "OK" if avg_margin > 20 else "WARNING"
        profit_status = "OK" if total_profit > 0 else "CRITICAL"
        profit_margin_status = "OK" if avg_margin > 15 else "WARNING"

        revenue_metrics.extend([
            CockpitMetric(name="MTD Revenue", value=total_revenue, status="OK"),
            CockpitMetric(name="MTD Orders", value=total_orders, status="OK"),
            CockpitMetric(name="Average Margin", value=avg_margin, status=margin_status),
        ])

        profit_metrics.extend([
            CockpitMetric(name="MTD Profit", value=total_profit, status=profit_status),
            CockpitMetric(name="Profit Margin", value=avg_margin, status=profit_margin_status),
        ])

        advertising_metrics.extend([
            CockpitMetric(name="MTD Ad Spend", value=total_advertising, status="OK"),
            CockpitMetric(name="DRR", value=avg_drr, status="OK" if avg_drr < 15 else "WARNING"),
        ])

    cockpit_risks = []
    if risks:
        sorted_risks = sorted(risks, key=lambda r: r.get("score", 0), reverse=True)[:10]
        for r in sorted_risks:
            cockpit_risks.append(CockpitRisk(
                sku=r.get("sku", ""),
                risk_type=r.get("risk_type", ""),
                severity=r.get("severity", "MEDIUM"),
                score=r.get("score", 0),
                action_required=r.get("action_required", "Review"),
            ))

    cockpit_opportunities = []
    if opportunities:
        sorted_opps = sorted(opportunities, key=lambda o: o.get("score", 0), reverse=True)[:10]
        for o in sorted_opps:
            cockpit_opportunities.append(CockpitOpportunity(
                sku=o.get("sku", ""),
                opportunity=o.get("opportunity", ""),
                score=o.get("score", 0),
                expected_impact=o.get("expected_impact", ""),
                action=o.get("action", ""),
            ))

    cockpit_actions = []
    for risk in cockpit_risks[:5]:
        cockpit_actions.append(CockpitAction(
            priority="HIGH" if risk.severity in ("CRITICAL", "HIGH") else "MEDIUM",
            action=f"Address {risk.risk_type}",
            sku=risk.sku,
            reason=f"Score: {risk.score:.0f}",
            deadline="7 days",
        ))

    return ManagementCockpit(
        generated_at=now,
        revenue=revenue_metrics,
        profit=profit_metrics,
        advertising=advertising_metrics,
        risks=cockpit_risks,
        opportunities=cockpit_opportunities,
        actions=cockpit_actions,
    )
