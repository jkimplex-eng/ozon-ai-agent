"""Audit report generation for any builder."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditReport:
    builder_type: str
    task_goal: str
    timestamp: str
    git_status: str
    changed_files: list[str]
    test_results: dict[str, Any]
    roadmap_alignment: dict[str, Any]
    architecture_risks: list[str]
    recommended_next_task: str
    summary: str
    deploy_decision: dict[str, Any] | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "builder_type": self.builder_type,
            "task_goal": self.task_goal,
            "timestamp": self.timestamp,
            "git_status": self.git_status,
            "changed_files": self.changed_files,
            "test_results": self.test_results,
            "roadmap_alignment": self.roadmap_alignment,
            "architecture_risks": self.architecture_risks,
            "recommended_next_task": self.recommended_next_task,
            "summary": self.summary,
        }
        if self.deploy_decision is not None:
            result["deploy_decision"] = self.deploy_decision
        return result


def format_report_text(report: AuditReport) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("OZON AI AGENT — SUPERVISOR AUDIT REPORT")
    lines.append("=" * 60)
    lines.append(f"Builder:    {report.builder_type}")
    lines.append(f"Task Goal:  {report.task_goal}")
    lines.append(f"Timestamp:  {report.timestamp}")
    lines.append("")

    lines.append("GIT STATUS:")
    lines.append(f"  {report.git_status}")
    lines.append("")

    lines.append("CHANGED FILES:")
    if report.changed_files:
        for f in report.changed_files:
            lines.append(f"  - {f}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("TEST RESULTS:")
    tr = report.test_results
    lines.append(f"  Total:   {tr.get('total', 0)}")
    lines.append(f"  Passed:  {tr.get('passed', 0)}")
    lines.append(f"  Failed:  {tr.get('failed', 0)}")
    lines.append(f"  Lint:    {tr.get('lint_status', 'unknown')}")
    lines.append(f"  Type:    {tr.get('type_status', 'unknown')}")
    lines.append("")

    lines.append("ROADMAP ALIGNMENT:")
    ra = report.roadmap_alignment
    lines.append(f"  Current Phase:  {ra.get('current_phase', 'N/A')}")
    lines.append(f"  Completed:      {ra.get('completed', [])}")
    lines.append(f"  Remaining:      {ra.get('remaining', [])}")
    lines.append("")

    lines.append("ARCHITECTURE RISKS:")
    if report.architecture_risks:
        for risk in report.architecture_risks:
            lines.append(f"  ⚠ {risk}")
    else:
        lines.append("  None detected")
    lines.append("")

    lines.append("RECOMMENDED NEXT TASK:")
    lines.append(f"  {report.recommended_next_task}")
    lines.append("")

    lines.append("SUMMARY:")
    lines.append(f"  {report.summary}")

    if report.deploy_decision:
        lines.append("")
        lines.append("DEPLOYMENT DECISION:")
        dd = report.deploy_decision
        lines.append(f"  Allowed:  {dd.get('deploy_allowed', 'N/A')}")
        lines.append(f"  Risk:     {dd.get('risk_level', 'N/A')}")
        lines.append(f"  Reason:   {dd.get('reason', 'N/A')}")

    lines.append("=" * 60)

    return "\n".join(lines)
