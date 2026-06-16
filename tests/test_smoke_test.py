"""Smoke test for experiment CLI commands."""
from __future__ import annotations

from click.testing import CliRunner

from ozon_agent.cli import main


def test_smoke_experiments_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "--help"])
    assert result.exit_code == 0
    assert "Manage" in result.output or "experiment" in result.output.lower()


def test_smoke_experiments_create_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "create", "--help"])
    assert result.exit_code == 0
    assert "--sku" in result.output
    assert "--hypothesis" in result.output


def test_smoke_experiments_list_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "list", "--help"])
    assert result.exit_code == 0
    assert "--status" in result.output
    assert "--json" in result.output


def test_smoke_experiments_show_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "show", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_ready_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "ready", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_start_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "start", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_pause_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "pause", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_resume_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "resume", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_complete_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "complete", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_cancel_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "cancel", "--help"])
    assert result.exit_code == 0
    assert "--reason" in result.output


def test_smoke_experiments_fail_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "fail", "--help"])
    assert result.exit_code == 0
    assert "--reason" in result.output


def test_smoke_experiments_metrics_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "metrics", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_events_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "events", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_evaluate_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "evaluate", "--help"])
    assert result.exit_code == 0


def test_smoke_experiments_report_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "report", "--help"])
    assert result.exit_code == 0
    assert "--json" in result.output


def test_smoke_experiments_create_from_recommendation_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["experiments", "create-from-recommendation", "--help"])
    assert result.exit_code == 0
