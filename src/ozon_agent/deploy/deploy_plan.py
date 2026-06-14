"""Deployment decision and plan generation."""
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeployDecision:
    deploy_allowed: bool
    reason: str
    required_steps: list[str]
    risk_level: str  # low, medium, high, blocked
    supervisor_status: str
    test_results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deploy_allowed": self.deploy_allowed,
            "reason": self.reason,
            "required_steps": self.required_steps,
            "risk_level": self.risk_level,
            "supervisor_status": self.supervisor_status,
            "test_results": self.test_results,
        }


@dataclass
class DeployPlan:
    target: str
    branch: str
    commands: list[str]
    health_check_commands: list[str]
    rollback_commands: list[str]
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "branch": self.branch,
            "commands": self.commands,
            "health_check_commands": self.health_check_commands,
            "rollback_commands": self.rollback_commands,
            "dry_run": self.dry_run,
        }


def evaluate_deploy_readiness(
    supervisor_status: str,
    test_results: dict[str, Any],
) -> DeployDecision:
    """Determine if deployment is allowed based on supervisor results."""
    if supervisor_status == "fail":
        return DeployDecision(
            deploy_allowed=False,
            reason="Supervisor status is FAIL — fix issues before deploying",
            required_steps=[],
            risk_level="blocked",
            supervisor_status=supervisor_status,
            test_results=test_results,
        )

    lint_status = test_results.get("lint_status", "unknown")
    type_status = test_results.get("type_status", "unknown")
    failed = test_results.get("failed", 0)
    total = test_results.get("total", 0)

    if failed > 0:
        return DeployDecision(
            deploy_allowed=False,
            reason=f"{failed} test(s) failed — fix before deploying",
            required_steps=["Fix failing tests"],
            risk_level="blocked",
            supervisor_status=supervisor_status,
            test_results=test_results,
        )

    risk_level = "low"
    reasons = []

    if total == 0:
        risk_level = "medium"
        reasons.append("tests were skipped or not found")
        logger.warning("No test results found — tests may have been skipped")

    if lint_status == "fail":
        risk_level = "medium"
        reasons.append("lint warnings present")
    if type_status == "fail":
        risk_level = "medium"
        reasons.append("type errors present")

    reason = "All checks passed" if not reasons else "; ".join(reasons)

    steps = [
        "git pull origin {branch}",
        "npm install",
        "npm test",
        "npm run health",
        "pm2 restart ollama-bot --update-env",
        "pm2 save",
    ]

    return DeployDecision(
        deploy_allowed=True,
        reason=reason,
        required_steps=steps,
        risk_level=risk_level,
        supervisor_status=supervisor_status,
        test_results=test_results,
    )


def build_deploy_plan(
    decision: DeployDecision,
    target: str = "vps",
    branch: str = "main",
    dry_run: bool = True,
) -> DeployPlan:
    """Build deployment plan from decision."""
    commands = [
        f"ssh {target} 'cd /root/ollama-bot && git pull origin {branch}'",
        f"ssh {target} 'cd /root/ollama-bot && npm install'",
        f"ssh {target} 'cd /root/ollama-bot && npm test'",
        f"ssh {target} 'cd /root/ollama-bot && npm run health'",
        f"ssh {target} 'pm2 restart ollama-bot --update-env'",
        f"ssh {target} 'pm2 save'",
    ]

    health_check = [
        f"ssh {target} 'pm2 list'",
        f"ssh {target} 'pm2 logs ollama-bot --lines 10 --nostream'",
        f"ssh {target} 'curl -s http://localhost:3000/health || echo HEALTH_FAIL'",
    ]

    rollback = [
        f"ssh {target} 'cd /root/ollama-bot && git checkout HEAD~1'",
        f"ssh {target} 'cd /root/ollama-bot && npm install'",
        f"ssh {target} 'pm2 restart ollama-bot --update-env'",
        f"ssh {target} 'pm2 save'",
    ]

    return DeployPlan(
        target=target,
        branch=branch,
        commands=commands,
        health_check_commands=health_check,
        rollback_commands=rollback,
        dry_run=dry_run,
    )


def format_plan_text(plan: DeployPlan, decision: DeployDecision) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("DEPLOYMENT PLAN")
    lines.append("=" * 60)
    lines.append(f"Target:      {plan.target}")
    lines.append(f"Branch:      {plan.branch}")
    lines.append(f"Mode:        {'DRY RUN' if plan.dry_run else 'EXECUTE'}")
    lines.append(f"Risk:        {decision.risk_level}")
    lines.append(f"Supervisor:  {decision.supervisor_status}")
    lines.append(f"Reason:      {decision.reason}")
    lines.append("")

    lines.append("DEPLOY COMMANDS:")
    for i, cmd in enumerate(plan.commands, 1):
        prefix = "  " if plan.dry_run else "$ "
        lines.append(f"  {i}. {prefix}{cmd}")
    lines.append("")

    lines.append("HEALTH CHECK:")
    for cmd in plan.health_check_commands:
        lines.append(f"  $ {cmd}")
    lines.append("")

    lines.append("ROLLBACK (if health check fails):")
    for cmd in plan.rollback_commands:
        lines.append(f"  $ {cmd}")
    lines.append("")

    if plan.dry_run:
        lines.append("[DRY RUN] No commands executed. Use --execute to deploy.")
    else:
        lines.append("[EXECUTE] Commands will be executed on target.")

    lines.append("=" * 60)
    return "\n".join(lines)
