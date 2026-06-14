"""Tests for approval CLI integration."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from ozon_agent.cli import main


def test_approvals_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["approvals", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "show" in result.output
    assert "approve" in result.output
    assert "reject" in result.output


def test_approvals_list_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["approvals", "list", "--help"])
    assert result.exit_code == 0
    assert "--status" in result.output


def test_approvals_list_empty() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.list_recommendations", return_value=[]):
        result = runner.invoke(main, ["approvals", "list"])
        assert result.exit_code == 0
        assert "No recommendations" in result.output


def test_approvals_show_not_found() -> None:
    runner = CliRunner()
    with patch("ozon_agent.approval.repository.get_recommendation", return_value=None):
        result = runner.invoke(main, ["approvals", "show", "missing-id"])
        assert result.exit_code == 0
        assert "not found" in result.output


def test_recommendations_save_pending_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations", "--help"])
    assert result.exit_code == 0
    assert "--save-pending" in result.output
    assert "--force" in result.output
