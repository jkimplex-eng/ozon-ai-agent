"""Tests for decision CLI integration."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from ozon_agent.cli import main


def test_recommendations_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations", "--help"])
    assert result.exit_code == 0
    assert "--sku" in result.output
    assert "--top" in result.output
    assert "--json" in result.output


@patch("ozon_agent.db.connection.execute_query", return_value=[])
def test_recommendations_empty_db(mock_query: object) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations"])
    assert result.exit_code == 0
    assert "No " in result.output


@patch("ozon_agent.db.connection.execute_query", return_value=[])
def test_recommendations_json_output(mock_query: object) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations", "--json"])
    assert result.exit_code == 0


@patch("ozon_agent.db.connection.execute_query", return_value=[])
def test_recommendations_sku_filter(mock_query: object) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommendations", "--sku", "NONEXISTENT"])
    assert result.exit_code == 0
    assert "No " in result.output
