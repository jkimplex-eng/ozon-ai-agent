"""Tests for VPS deploy pipeline."""
from __future__ import annotations

from unittest.mock import patch

from ozon_agent.deploy.health_check import (
    check_cli_available,
    check_dependencies,
    check_env_vars,
    check_git_revision,
    check_python_import,
    check_sheets_sync_dry_run,
    check_sheets_watch_interval,
    check_supervisor_status,
    format_health_report,
    run_full_health_check,
)

OK = {"healthy": True}
FAIL = {"healthy": False}


def test_check_git_revision_no_expected() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "abc1234\n", "stderr": ""}
        result = check_git_revision("vps")
        assert result["healthy"] is True
        assert result["remote_revision"] == "abc1234"


def test_check_git_revision_match() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "abc1234\n", "stderr": ""}
        result = check_git_revision("vps", expected_rev="abc1234")
        assert result["healthy"] is True


def test_check_git_revision_mismatch() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "abc1234\n", "stderr": ""}
        result = check_git_revision("vps", expected_rev="xyz9999")
        assert result["healthy"] is False


def test_check_git_revision_failure() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": False, "stdout": "", "stderr": "ssh error"}
        result = check_git_revision("vps")
        assert result["healthy"] is False


def test_check_python_import_ok() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "0.1.0\n", "stderr": ""}
        result = check_python_import("vps")
        assert result["healthy"] is True
        assert result["version"] == "0.1.0"


def test_check_python_import_fail() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {
            "success": False, "stdout": "", "stderr": "ModuleNotFoundError",
        }
        result = check_python_import("vps")
        assert result["healthy"] is False


def test_check_cli_available_ok() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "OK\n", "stderr": ""}
        result = check_cli_available("vps")
        assert result["healthy"] is True


def test_check_dependencies_all_ok() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "", "stderr": ""}
        result = check_dependencies("vps")
        assert result["healthy"] is True
        assert result["missing"] == []


def test_check_dependencies_some_missing() -> None:
    def side_effect(target, command, timeout=10):
        if "gspread" in command:
            return {"success": False, "stdout": "", "stderr": "No module"}
        return {"success": True, "stdout": "", "stderr": ""}

    with patch("ozon_agent.deploy.health_check.run_ssh_command", side_effect=side_effect):
        result = check_dependencies("vps")
        assert result["healthy"] is False
        assert "gspread" in result["missing"]


def test_check_env_vars_ok() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "OK\n", "stderr": ""}
        result = check_env_vars("vps")
        assert result["healthy"] is True
        assert result["missing"] == []


def test_check_env_vars_missing() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "MISSING\n", "stderr": ""}
        result = check_env_vars("vps")
        assert result["healthy"] is False
        assert len(result["missing"]) > 0


def test_check_supervisor_status_running() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {
            "success": True,
            "stdout": "ozon-sheets-watch RUNNING pid 123, uptime 0:01:00\n",
            "stderr": "",
        }
        result = check_supervisor_status("vps")
        assert result["healthy"] is True


def test_check_supervisor_status_stopped() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {
            "success": True,
            "stdout": "ozon-sheets-watch STOPPED Not started\n",
            "stderr": "",
        }
        result = check_supervisor_status("vps")
        assert result["healthy"] is False


def test_check_sheets_watch_interval_ok() -> None:
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": "", "stderr": ""}
        result = check_sheets_watch_interval("vps")
        assert result["healthy"] is True


def test_check_sheets_sync_ok() -> None:
    output = "Syncing all tabs...\nDaily Report: OK\nRecommendations: OK"
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": output, "stderr": ""}
        result = check_sheets_sync_dry_run("vps")
        assert result["healthy"] is True


def test_check_sheets_sync_failed() -> None:
    output = "Daily Report: FAILED\nRecommendations: OK"
    with patch("ozon_agent.deploy.health_check.run_ssh_command") as m:
        m.return_value = {"success": True, "stdout": output, "stderr": ""}
        result = check_sheets_sync_dry_run("vps")
        assert result["healthy"] is False


def _mock_all() -> list:
    """Helper to patch all health checks as passing."""
    checks = {
        "check_git_revision": OK,
        "check_python_import": OK,
        "check_cli_available": OK,
        "check_dependencies": OK,
        "check_env_vars": OK,
        "check_sheets_sync_dry_run": OK,
        "check_supervisor_status": OK,
        "check_sheets_watch_interval": OK,
        "check_logs_errors": OK,
    }
    patches = []
    for func, val in checks.items():
        patches.append(
            patch(f"ozon_agent.deploy.health_check.{func}", return_value=val)
        )
    return patches


def test_run_full_health_check_pass() -> None:
    patches = _mock_all()
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        result = run_full_health_check("vps")
        assert result["healthy"] is True


def test_run_full_health_check_fails_on_one() -> None:
    patches = _mock_all()
    patches[1] = patch(
        "ozon_agent.deploy.health_check.check_python_import",
        return_value=FAIL,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        result = run_full_health_check("vps")
        assert result["healthy"] is False


def test_format_health_report_pass() -> None:
    result = {
        "healthy": True,
        "checks": {"git": {"healthy": True}, "cli": {"healthy": True}},
    }
    text = format_health_report(result)
    assert "All checks passed" in text


def test_format_health_report_fail() -> None:
    result = {
        "healthy": False,
        "checks": {
            "git": {"healthy": True},
            "cli": {"healthy": False, "error": "not found"},
        },
    }
    text = format_health_report(result)
    assert "failed" in text.lower()
    assert "not found" in text
