"""VPS deployment execution."""
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


def run_ssh_command(target: str, command: str, timeout: int = 120) -> dict[str, Any]:
    """Execute a command on VPS via SSH."""
    full_cmd = ["ssh", target, command]
    logger.info("Running: %s", " ".join(full_cmd))

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(full_cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "command": " ".join(full_cmd),
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": " ".join(full_cmd),
        }


def execute_deploy(
    target: str,
    branch: str = "main",
) -> dict[str, Any]:
    """Execute full deployment sequence on VPS."""
    results = []
    overall_success = True

    steps = [
        ("Pull code", f"cd /root/ollama-bot && git pull origin {branch}"),
        ("Install dependencies", "cd /root/ollama-bot && npm install"),
        ("Run tests", "cd /root/ollama-bot && npm test"),
        ("Health check", "cd /root/ollama-bot && npm run health"),
        ("Restart PM2", "pm2 restart ollama-bot --update-env"),
        ("Save PM2", "pm2 save"),
    ]

    for step_name, command in steps:
        logger.info("Step: %s", step_name)
        result = run_ssh_command(target, command)
        results.append({"step": step_name, **result})

        if not result["success"]:
            overall_success = False
            logger.error("Step failed: %s — %s", step_name, result["stderr"])
            break

    return {
        "success": overall_success,
        "steps": results,
    }


def execute_health_check(target: str) -> dict[str, Any]:
    """Run health checks on deployed VPS."""
    checks = [
        ("PM2 status", "pm2 list"),
        ("Recent logs", "pm2 logs ollama-bot --lines 10 --nostream"),
        ("HTTP health", "curl -s http://localhost:3000/health || echo HEALTH_FAIL"),
    ]

    results = []
    all_healthy = True

    for check_name, command in checks:
        result = run_ssh_command(target, command, timeout=30)
        results.append({"check": check_name, **result})

        if not result["success"]:
            all_healthy = False

    return {
        "healthy": all_healthy,
        "checks": results,
    }



