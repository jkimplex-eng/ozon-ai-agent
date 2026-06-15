"""Tests for learning CLI integration."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from ozon_agent.cli import main


def test_learning_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["learning", "--help"])
    assert result.exit_code == 0
    assert "summary" in result.output
    assert "calibrate" in result.output
    assert "backtest" in result.output
    assert "by-action" in result.output
    assert "by-sku" in result.output


def test_learning_summary_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["learning", "summary"])
        assert result.exit_code == 0
        assert "No observed" in result.output


def test_learning_summary_with_empty_db_does_not_fail() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        with patch("ozon_agent.approval.repository.list_outcomes", return_value=[]):
            result = runner.invoke(main, ["learning", "summary"])
    assert result.exit_code == 0
    assert "No observed" in result.output


def test_learning_calibrate_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["learning", "calibrate"])
        assert result.exit_code == 0
        assert "No observed" in result.output


def test_learning_backtest_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["learning", "backtest"])
        assert result.exit_code == 0
        assert "No observed" in result.output


def test_learning_by_action_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["learning", "by-action"])
        assert result.exit_code == 0
        assert "No observed" in result.output


def test_learning_by_sku_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["learning", "by-sku"])
        assert result.exit_code == 0
        assert "No observed" in result.output


def test_recommendations_calibrated_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations", "--help"])
    assert result.exit_code == 0
    assert "--calibrated" in result.output
