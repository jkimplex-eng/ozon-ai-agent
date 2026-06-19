"""Deployment decision and plan generation."""
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = [
    "update_price",
    "change_price",
    "create_campaign",
    "update_bid",
    "pause_campaign_api",
    "create_supply",
    "external_post",
    "execute_ozon_action",
    "requests.post",
    "httpx.post",
]


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

    forbidden = scan_decision_modules_forbidden()
    forbidden.extend(scan_approval_telegram_forbidden())
    if forbidden:
        return DeployDecision(
            deploy_allowed=False,
            reason=f"Forbidden keywords found: {', '.join(sorted(set(forbidden)))}",
            required_steps=["Remove forbidden write-action keywords from modules"],
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
        "pip install -e .",
        "python -m ozon_agent.cli --help",
        "install supervisor configs",
        "supervisorctl restart ozon-sheets-watch",
        "supervisorctl status ozon-sheets-watch",
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
        f"ssh {target} 'cd /root/ozon-ai-agent && git pull origin {branch}'",
        f"ssh {target} 'cd /root/ozon-ai-agent && source .venv/bin/activate && pip install -e .'",
        (
            f"ssh {target} 'cd /root/ozon-ai-agent && source .venv/bin/activate "
            "&& python -m ozon_agent.cli --help'"
        ),
        f"ssh {target} 'mkdir -p /root/ozon-ai-agent/logs'",
        f"ssh {target} 'cp /root/ozon-ai-agent/deploy/supervisor/*.conf /etc/supervisor/conf.d/'",
        f"ssh {target} 'supervisorctl reread && supervisorctl update'",
        (
            f"ssh {target} 'supervisorctl restart ozon-sheets-watch "
            "|| supervisorctl start ozon-sheets-watch'"
        ),
        f"ssh {target} 'supervisorctl status ozon-sheets-watch'",
    ]

    health_check = [
        f"ssh {target} 'supervisorctl status ozon-sheets-watch'",
        (
            f"ssh {target} 'grep -q \"sheets watch --interval 30\" "
            "/etc/supervisor/conf.d/ozon-sheets-watch.conf'"
        ),
        f"ssh {target} 'tail -50 /root/ozon-ai-agent/logs/ozon-sheets-watch.log'",
    ]

    rollback = [
        f"ssh {target} 'cd /root/ozon-ai-agent && git checkout HEAD~1'",
        f"ssh {target} 'cd /root/ozon-ai-agent && source .venv/bin/activate && pip install -e .'",
        f"ssh {target} 'cp /root/ozon-ai-agent/deploy/supervisor/*.conf /etc/supervisor/conf.d/'",
        f"ssh {target} 'supervisorctl reread && supervisorctl update'",
        f"ssh {target} 'supervisorctl restart ozon-sheets-watch'",
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

    migration = detect_pending_migrations()
    if migration:
        lines.append("")
        lines.append("Migration detected:")
        for m in migration:
            lines.append(f"  {m}")
        lines.append("")
        lines.append("Manual/automatic migration step required before restart.")

    learning_dir = os.path.join(os.path.dirname(__file__), "..", "learning")
    if os.path.isdir(learning_dir):
        lines.append("")
        lines.append("Learning module detected")
        lines.append("No migration required")
        lines.append("Read-only learning mode")

    experiments_dir = os.path.join(os.path.dirname(__file__), "..", "experiments")
    if os.path.isdir(experiments_dir):
        lines.append("")
        lines.append("Experiments module detected")
        lines.append("Control-plane only — no automatic Ozon actions")
        lines.append("Read-only experiment management")

    lines.append("=" * 60)
    return "\n".join(lines)


def scan_decision_modules_forbidden() -> list[str]:
    found: list[str] = []
    decision_dir = os.path.join(
        os.path.dirname(__file__), "..", "decision"
    )
    if not os.path.isdir(decision_dir):
        return found

    for filename in os.listdir(decision_dir):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(decision_dir, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in content:
                found.append(keyword)

    return sorted(set(found))


def scan_approval_telegram_forbidden() -> list[str]:
    found: list[str] = []
    for module_name in ("approval", "telegram", "learning", "experiments", "sheets"):
        module_dir = os.path.join(os.path.dirname(__file__), "..", module_name)
        if not os.path.isdir(module_dir):
            continue
        for filename in os.listdir(module_dir):
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(module_dir, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            for keyword in FORBIDDEN_KEYWORDS:
                if keyword in content:
                    found.append(keyword)
    return sorted(set(found))


def detect_pending_migrations() -> list[str]:
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations")
    if not os.path.isdir(migrations_dir):
        return []
    return [
        f"migrations/{f}"
        for f in sorted(os.listdir(migrations_dir))
        if f.endswith(".sql")
    ]
