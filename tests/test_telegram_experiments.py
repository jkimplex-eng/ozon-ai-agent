"""Tests for Telegram experiment commands."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from ozon_agent.experiments.models import Experiment, ExperimentStatus
from ozon_agent.telegram.bot import handle_message


def _sample_experiment() -> Experiment:
    now = datetime.now(UTC)
    return Experiment(
        id="exp-test-0001-0002-0003",
        created_at=now,
        updated_at=now,
        sku="SKU-TEST",
        hypothesis="Test hypothesis",
        action="INCREASE_BUDGET",
        risk="LOW",
        confidence="HIGH",
        status=ExperimentStatus.DRAFT,
        created_by="test",
    )


def test_handle_message_experiments_help() -> None:
    response = handle_message("/experiments unknown", "user")
    assert "usage" in response.lower() or "Experiments" in response


def test_handle_message_experiments_list_empty() -> None:
    with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
        response = handle_message("/experiments", "user")
        assert "No experiments" in response


def test_handle_message_experiments_list() -> None:
    exp = _sample_experiment()
    with patch("ozon_agent.experiments.repository.list_experiments", return_value=[exp]):
        response = handle_message("/experiments", "user")
        assert "SKU-TEST" in response


def test_handle_message_experiments_list_command() -> None:
    exp = _sample_experiment()
    with patch("ozon_agent.experiments.repository.list_experiments", return_value=[exp]):
        response = handle_message("/experiments list", "user")
        assert "SKU-TEST" in response


def test_handle_message_experiments_show() -> None:
    exp = _sample_experiment()
    with patch("ozon_agent.experiments.repository.get_experiment", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments show exp-test", "user")
            assert "SKU-TEST" in response
            assert "Test hypothesis" in response


def test_handle_message_experiments_show_not_found() -> None:
    with patch("ozon_agent.experiments.repository.get_experiment", return_value=None):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments show missing", "user")
            assert "not found" in response


def test_handle_message_experiments_ready() -> None:
    exp = _sample_experiment()
    exp.status = ExperimentStatus.READY
    with patch("ozon_agent.experiments.workflow.mark_ready", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments ready exp-123", "Pavel")
            assert "READY" in response


def test_handle_message_experiments_start() -> None:
    exp = _sample_experiment()
    exp.status = ExperimentStatus.RUNNING
    with patch("ozon_agent.experiments.workflow.mark_running", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments start exp-123", "Pavel")
            assert "RUNNING" in response


def test_handle_message_experiments_pause() -> None:
    exp = _sample_experiment()
    exp.status = ExperimentStatus.PAUSED
    with patch("ozon_agent.experiments.workflow.mark_paused", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments pause exp-123", "Pavel")
            assert "PAUSED" in response


def test_handle_message_experiments_complete() -> None:
    exp = _sample_experiment()
    exp.status = ExperimentStatus.COMPLETED
    with patch("ozon_agent.experiments.workflow.mark_completed", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments complete exp-123", "Pavel")
            assert "COMPLETED" in response


def test_handle_message_experiments_cancel() -> None:
    exp = _sample_experiment()
    exp.status = ExperimentStatus.CANCELLED
    with patch("ozon_agent.experiments.workflow.mark_cancelled", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message(
                "/experiments cancel exp-123 no longer needed", "Pavel"
            )
            assert "cancelled" in response


def test_handle_message_experiments_report() -> None:
    exp = _sample_experiment()
    with patch("ozon_agent.experiments.repository.get_experiment", return_value=exp):
        with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
            response = handle_message("/experiments report exp-123", "user")
            assert "EXPERIMENT REPORT" in response


def test_telegram_experiments_no_write_actions() -> None:
    with patch("ozon_agent.experiments.repository.list_experiments", return_value=[]):
        response = handle_message("/experiments", "user")
        assert "execute" not in response.lower() or "not" in response.lower()


def test_help_text_includes_experiments() -> None:
    response = handle_message("unknown", "user")
    assert "/experiments" in response
