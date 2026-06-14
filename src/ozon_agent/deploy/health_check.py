"""Post-deployment health checks."""
from typing import Any

from .vps_deployer import run_ssh_command


def check_pm2_status(target: str) -> dict[str, Any]:
    """Check PM2 process status."""
    result = run_ssh_command(target, "pm2 jlist", timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    try:
        import json
        processes = json.loads(result["stdout"])
        bot_process = None
        for proc in processes:
            if proc.get("name") == "ollama-bot":
                bot_process = proc
                break

        if bot_process is None:
            return {"healthy": False, "error": "ollama-bot process not found in PM2"}

        status = bot_process.get("pm2_env", {}).get("status", "unknown")
        restarts = bot_process.get("pm2_env", {}).get("restart_time", 0)

        return {
            "healthy": status == "online",
            "status": status,
            "restarts": restarts,
        }
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_http_health(target: str, url: str = "http://localhost:3000/health") -> dict[str, Any]:
    """Check HTTP health endpoint."""
    result = run_ssh_command(target, f"curl -s -o /dev/null -w '%{{http_code}}' {url}", timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    status_code = result["stdout"].strip().strip("'")
    return {
        "healthy": status_code == "200",
        "status_code": status_code,
    }


def check_logs_errors(target: str, lines: int = 20) -> dict[str, Any]:
    """Check recent logs for errors."""
    cmd = f"pm2 logs ollama-bot --lines {lines} --nostream 2>&1"
    result = run_ssh_command(target, cmd, timeout=15)
    if not result["success"]:
        return {"healthy": False, "error": result["stderr"]}

    output = result["stdout"].lower()
    error_indicators = ["error", "fatal", "panic", "exception", "traceback"]
    found_errors = [ind for ind in error_indicators if ind in output]

    return {
        "healthy": len(found_errors) == 0,
        "errors_found": found_errors,
        "log_lines": lines,
    }


def run_full_health_check(target: str) -> dict[str, Any]:
    """Run all health checks and return combined result."""
    checks = {
        "pm2": check_pm2_status(target),
        "http": check_http_health(target),
        "logs": check_logs_errors(target),
    }

    all_healthy = all(check["healthy"] for check in checks.values())

    return {
        "healthy": all_healthy,
        "checks": checks,
    }
