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

    deploy_dir = "/root/ozon-ai-agent"
    venv = f"{deploy_dir}/.venv/bin/activate"
    steps = [
        (
            "Pull code",
            f"cd {deploy_dir} && git fetch origin && git checkout {branch} "
            f"&& git pull origin {branch}",
        ),
        (
            "Install dependencies",
            f"cd {deploy_dir} && source {venv} && pip install -e .",
        ),
        (
            "Verify CLI",
            f"cd {deploy_dir} && source {venv} "
            "&& python -m ozon_agent.cli --help >/dev/null",
        ),
        ("Prepare logs", f"mkdir -p {deploy_dir}/logs"),
        (
            "Install supervisor configs",
            f"cp {deploy_dir}/deploy/supervisor/*.conf /etc/supervisor/conf.d/",
        ),
        ("Supervisor reread", "supervisorctl reread"),
        ("Supervisor update", "supervisorctl update"),
        (
            "Restart sheets watcher",
            "supervisorctl restart ozon-sheets-watch "
            "|| supervisorctl start ozon-sheets-watch",
        ),
        (
            "Verify sheets watcher",
            "supervisorctl status ozon-sheets-watch | grep -q RUNNING",
        ),
        (
            "Sheets sync smoke",
            f"cd {deploy_dir} && source {venv} && SHEETS_DATA_SOURCE=files "
            "python -m ozon_agent.cli sheets sync --source files --delay 10",
        ),
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
        ("Supervisor status", "supervisorctl status ozon-sheets-watch"),
        (
            "Recent logs",
            "tail -50 /root/ozon-ai-agent/logs/ozon-sheets-watch.log",
        ),
        (
            "CLI health",
            "cd /root/ozon-ai-agent && .venv/bin/python -m ozon_agent.cli --help",
        ),
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


