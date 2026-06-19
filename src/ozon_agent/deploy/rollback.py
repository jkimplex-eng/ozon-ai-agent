"""Rollback procedures."""
from typing import Any

from .vps_deployer import run_ssh_command


def generate_rollback_commands(target: str, branch: str = "main") -> list[str]:
    """Generate rollback command list."""
    return [
        f"ssh {target} 'cd /root/ozon-ai-agent && git log --oneline -1'",
        f"ssh {target} 'cd /root/ozon-ai-agent && git checkout HEAD~1'",
        f"ssh {target} 'cd /root/ozon-ai-agent && source .venv/bin/activate && pip install -e .'",
        f"ssh {target} 'cp /root/ozon-ai-agent/deploy/supervisor/*.conf /etc/supervisor/conf.d/'",
        f"ssh {target} 'supervisorctl reread && supervisorctl update'",
        f"ssh {target} 'supervisorctl restart ozon-sheets-watch'",
        f"ssh {target} 'supervisorctl status ozon-sheets-watch'",
    ]


def execute_rollback(target: str) -> dict[str, Any]:
    """Execute rollback on VPS."""
    steps = [
        ("Get current commit", "cd /root/ozon-ai-agent && git log --oneline -1"),
        ("Revert to previous", "cd /root/ozon-ai-agent && git checkout HEAD~1"),
        (
            "Install dependencies",
            "cd /root/ozon-ai-agent && source .venv/bin/activate && pip install -e .",
        ),
        (
            "Install supervisor configs",
            "cp /root/ozon-ai-agent/deploy/supervisor/*.conf /etc/supervisor/conf.d/",
        ),
        ("Supervisor reread", "supervisorctl reread"),
        ("Supervisor update", "supervisorctl update"),
        ("Restart sheets watcher", "supervisorctl restart ozon-sheets-watch"),
        ("Verify sheets watcher", "supervisorctl status ozon-sheets-watch"),
    ]

    results = []
    for step_name, command in steps:
        result = run_ssh_command(target, command, timeout=120)
        results.append({"step": step_name, **result})

        if not result["success"] and step_name in ("Revert to previous", "Restart sheets watcher"):
            break

    return {
        "success": all(r["success"] for r in results),
        "steps": results,
    }


def format_rollback_text(target: str) -> str:
    """Format rollback instructions as text."""
    commands = generate_rollback_commands(target)
    lines = [
        "=" * 60,
        "ROLLBACK INSTRUCTIONS",
        "=" * 60,
        "",
        "If health check fails after deployment, run these commands:",
        "",
    ]
    for i, cmd in enumerate(commands, 1):
        lines.append(f"  {i}. {cmd}")

    lines.extend([
        "",
        "Or run: ozon-agent rollback --target " + target,
        "=" * 60,
    ])
    return "\n".join(lines)
