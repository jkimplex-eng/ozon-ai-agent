"""Tests for deploy health command."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from ozon_agent.cli import main


def test_deploy_health_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["deploy", "health", "--help"])
    assert result.exit_code == 0
    assert "health" in result.output.lower()


def test_deploy_vps_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["deploy", "vps", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output


def test_deploy_verify_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["deploy", "verify", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output


def test_deploy_rollback_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["deploy", "rollback", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output


def test_deploy_group_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "vps" in result.output
    assert "verify" in result.output
    assert "rollback" in result.output
    assert "health" in result.output


def test_deploy_health_all_ok() -> None:
    runner = CliRunner()
    ok = {"healthy": True}
    with patch("ozon_agent.deploy.health_check.check_git_revision", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_python_import", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_cli_available", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_dependencies", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_env_vars", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_sheets_sync_dry_run", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_pm2_status", return_value=ok):
        result = runner.invoke(main, ["deploy", "health"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_deploy_health_some_fail() -> None:
    runner = CliRunner()
    ok = {"healthy": True}
    fail = {"healthy": False, "error": "not found"}
    with patch("ozon_agent.deploy.health_check.check_git_revision", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_python_import", return_value=fail), \
         patch("ozon_agent.deploy.health_check.check_cli_available", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_dependencies", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_env_vars", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_sheets_sync_dry_run", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_pm2_status", return_value=ok):
        result = runner.invoke(main, ["deploy", "health"])
        assert result.exit_code == 0
        assert "FAIL" in result.output
        assert "not found" in result.output


def test_deploy_health_handles_exception() -> None:
    runner = CliRunner()
    ok = {"healthy": True}
    with patch("ozon_agent.deploy.health_check.check_git_revision", return_value=ok), \
         patch(
             "ozon_agent.deploy.health_check.check_python_import",
             side_effect=Exception("ssh down"),
         ), \
         patch("ozon_agent.deploy.health_check.check_cli_available", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_dependencies", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_env_vars", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_sheets_sync_dry_run", return_value=ok), \
         patch("ozon_agent.deploy.health_check.check_pm2_status", return_value=ok):
        result = runner.invoke(main, ["deploy", "health"])
        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "ssh down" in result.output


def test_gitignore_has_secrets() -> None:
    with open(".gitignore") as f:
        content = f.read()
    assert "secrets/" in content
    assert ".env" in content
    assert "*.key" in content
    assert "*.pem" in content


def test_supervisor_config_uses_venv() -> None:
    with open("deploy/supervisor/ozon-sheets-watch.conf") as f:
        content = f.read()
    assert ".venv/bin/python" in content
    assert "autostart=true" in content


def test_supervisor_telegram_config_autostart_false() -> None:
    with open("deploy/supervisor/ozon-telegram-bot.conf") as f:
        content = f.read()
    assert "autostart=false" in content
    assert ".venv/bin/python" in content
