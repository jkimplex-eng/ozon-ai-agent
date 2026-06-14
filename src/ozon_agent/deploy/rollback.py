"""Rollback procedures."""
from typing import Any

from .vps_deployer import run_ssh_command


def generate_rollback_commands(target: str, branch: str = "main") -> list[str]:
    """Generate rollback command list."""
    return [
        f"ssh {target} 'cd /root/ollama-bot && git log --oneline -1'",
        f"ssh {target} 'cd /root/ollama-bot && git checkout HEAD~1'",
        f"ssh {target} 'cd /root/ollama-bot && npm install'",
        f"ssh {target} 'cd /root/ollama-bot && npm test'",
        f"ssh {target} 'pm2 restart ollama-bot --update-env'",
        f"ssh {target} 'pm2 save'",
    ]


def execute_rollback(target: str) -> dict[str, Any]:
    """Execute rollback on VPS."""
    steps = [
        ("Get current commit", "cd /root/ollama-bot && git log --oneline -1"),
        ("Revert to previous", "cd /root/ollama-bot && git checkout HEAD~1"),
        ("Install dependencies", "cd /root/ollama-bot && npm install"),
        ("Run tests", "cd /root/ollama-bot && npm test"),
        ("Restart PM2", "pm2 restart ollama-bot --update-env"),
        ("Save PM2", "pm2 save"),
    ]

    results = []
    for step_name, command in steps:
        result = run_ssh_command(target, command, timeout=120)
        results.append({"step": step_name, **result})

        if not result["success"] and step_name in ("Revert to previous", "Restart PM2"):
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
