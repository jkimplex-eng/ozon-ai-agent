"""Tests for experiment CLI commands."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.experiments.models import ExperimentStatus
from ozon_agent.experiments.repository import (
    override_connection_factory,
)
from ozon_agent.experiments.workflow import (
    create_new_experiment,
    mark_ready,
    mark_running,
)


def _sample_experiment() -> Any:
    from ozon_agent.experiments.models import Experiment

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


class _FakeCursor:
    def __init__(self, storage: dict[str, list[dict[str, Any]]]) -> None:
        self.storage = storage
        self.description: list[str] | None = None
        self._rows: list[dict[str, Any]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: dict[str, Any]) -> None:
        if "INSERT INTO experiments" in sql:
            record = deepcopy(params)
            for key in ("actual_effect", "expected_effect", "metrics"):
                if key in record and isinstance(record[key], str):
                    import json
                    record[key] = json.loads(record[key])
            existing = [
                row for row in self.storage["experiments"] if row["id"] != params["id"]
            ]
            self.storage["experiments"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if "INSERT INTO experiment_events" in sql:
            record = deepcopy(params)
            import json
            if "metadata" in record and isinstance(record["metadata"], str):
                record["metadata"] = json.loads(record["metadata"])
            self.storage["events"].append(record)
            self.description = None
            self._rows = []
            return
        if sql.strip().startswith("SELECT * FROM experiments WHERE id"):
            self._rows = [
                deepcopy(row)
                for row in self.storage["experiments"]
                if row["id"] == params["id"]
            ]
            self.description = ["id"]
            return
        if sql.strip().startswith("SELECT * FROM experiments"):
            rows = [deepcopy(row) for row in self.storage["experiments"]]
            if "status" in params:
                rows = [row for row in rows if row["status"] == params["status"]]
            if "sku" in params:
                rows = [row for row in rows if row["sku"] == params["sku"]]
            rows.sort(key=lambda item: item["created_at"], reverse=True)
            self._rows = rows[: int(params["limit"])]
            self.description = ["id"]
            return
        if sql.strip().startswith("SELECT * FROM experiment_events"):
            rows = [
                deepcopy(row)
                for row in self.storage["events"]
                if row["experiment_id"] == params["experiment_id"]
            ]
            rows.sort(key=lambda item: item["created_at"], reverse=True)
            self._rows = rows
            self.description = ["id"]
            return
        if sql.strip().startswith("UPDATE experiments"):
            for index, row in enumerate(self.storage["experiments"]):
                if row["id"] != params["id"]:
                    continue
                updated = deepcopy(row)
                for key, value in params.items():
                    if key == "id":
                        continue
                    if value is not None:
                        updated[key] = value
                self.storage["experiments"][index] = updated
                break
            self.description = None
            self._rows = []
            return
        raise AssertionError(f"Unexpected SQL: {sql[:80]}")

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeConnection:
    def __init__(self, storage: dict[str, list[dict[str, Any]]]) -> None:
        self.storage = storage

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.storage)

    def commit(self) -> None:
        return None


@contextmanager
def fake_repository() -> Any:
    storage: dict[str, list[dict[str, Any]]] = {"experiments": [], "events": []}

    @contextmanager
    def _factory() -> Any:
        yield _FakeConnection(storage)

    with override_connection_factory(_factory):
        yield storage


def test_experiments_create_command() -> None:
    runner = CliRunner()
    with fake_repository():
        result = runner.invoke(main, [
            "experiments", "create",
            "--sku", "SKU-1",
            "--hypothesis", "Test hypothesis",
            "--action", "INCREASE_BUDGET",
        ])
        assert result.exit_code == 0
        assert "Created experiment" in result.output


def test_experiments_list_command() -> None:
    runner = CliRunner()
    with fake_repository():
        create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "list"])
        assert result.exit_code == 0
        assert "SKU-1" in result.output


def test_experiments_list_empty() -> None:
    runner = CliRunner()
    with fake_repository():
        result = runner.invoke(main, ["experiments", "list"])
        assert result.exit_code == 0
        assert "No experiments found" in result.output


def test_experiments_list_json() -> None:
    runner = CliRunner()
    with fake_repository():
        create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "list", "--json"])
        assert result.exit_code == 0
        assert "SKU-1" in result.output
        assert '"sku"' in result.output


def test_experiments_list_by_status() -> None:
    runner = CliRunner()
    with fake_repository():
        create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "list", "--status", "DRAFT"])
        assert result.exit_code == 0
        assert "SKU-1" in result.output


def test_experiments_show_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "show", exp.id])
        assert result.exit_code == 0
        assert "SKU-1" in result.output
        assert "H1" in result.output


def test_experiments_show_json() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "show", exp.id, "--json"])
        assert result.exit_code == 0
        assert '"sku"' in result.output


def test_experiments_show_not_found() -> None:
    runner = CliRunner()
    with fake_repository():
        result = runner.invoke(main, ["experiments", "show", "nonexistent"])
        assert result.exit_code == 0
        assert "not found" in result.output


def test_experiments_lifecycle_commands() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )

        result = runner.invoke(main, ["experiments", "ready", exp.id])
        assert result.exit_code == 0
        assert "READY" in result.output

        result = runner.invoke(main, ["experiments", "start", exp.id])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

        result = runner.invoke(main, ["experiments", "pause", exp.id])
        assert result.exit_code == 0
        assert "PAUSED" in result.output

        result = runner.invoke(main, ["experiments", "resume", exp.id])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

        result = runner.invoke(main, ["experiments", "complete", exp.id])
        assert result.exit_code == 0
        assert "COMPLETED" in result.output


def test_experiments_cancel_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, [
            "experiments", "cancel", exp.id, "--reason", "no longer needed",
        ])
        assert result.exit_code == 0
        assert "cancelled" in result.output


def test_experiments_fail_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        mark_ready(exp.id)
        mark_running(exp.id)
        result = runner.invoke(main, [
            "experiments", "fail", exp.id, "--reason", "data issue",
        ])
        assert result.exit_code == 0
        assert "failed" in result.output


def test_experiments_events_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "events", exp.id])
        assert result.exit_code == 0
        assert "CREATED" in result.output


def test_experiments_evaluate_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        mark_ready(exp.id)
        mark_running(exp.id)
        result = runner.invoke(main, ["experiments", "evaluate", exp.id])
        assert result.exit_code == 0
        assert "Evaluated" in result.output


def test_experiments_report_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "report", exp.id])
        assert result.exit_code == 0
        assert "EXPERIMENT REPORT" in result.output
        assert "SKU-1" in result.output


def test_experiments_report_json() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, ["experiments", "report", exp.id, "--json"])
        assert result.exit_code == 0
        assert '"sku"' in result.output


def test_experiments_metrics_command() -> None:
    runner = CliRunner()
    with fake_repository():
        exp = create_new_experiment(
            sku="SKU-1", hypothesis="H1", action="INCREASE_BUDGET", created_by="test",
        )
        result = runner.invoke(main, [
            "experiments", "metrics", exp.id,
            "--baseline-orders", "10",
            "--current-orders", "15",
        ])
        assert result.exit_code == 0
        assert "Updated metrics" in result.output


def test_experiments_create_from_recommendation() -> None:
    runner = CliRunner()
    with fake_repository():
        with patch("ozon_agent.approval.repository.get_recommendation") as mock_get:
            from ozon_agent.approval.models import (
                RecommendationStatus,
                StoredRecommendation,
            )
            from ozon_agent.decision.models import (
                ConfidenceLevel,
                RecommendationAction,
                RiskLevel,
            )

            now = datetime.now(UTC)
            rec = StoredRecommendation(
                id="rec-test-1234-5678-9012",
                created_at=now,
                updated_at=now,
                sku="SKU-REC",
                action=RecommendationAction.INCREASE_BUDGET,
                reason="Test reason",
                confidence_score=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                risk_score=0.2,
                risk_level=RiskLevel.LOW,
                expected_effect={"orders": {"delta_pct": 15.0}},
                supporting_metrics={},
                status=RecommendationStatus.APPROVED,
            )
            mock_get.return_value = rec

            result = runner.invoke(main, [
                "experiments", "create-from-recommendation", "rec-test-1234-5678-9012",
            ])
            assert result.exit_code == 0
            assert "Created experiment" in result.output


def test_experiments_create_from_recommendation_wrong_status() -> None:
    runner = CliRunner()
    with fake_repository():
        with patch("ozon_agent.approval.repository.get_recommendation") as mock_get:
            from ozon_agent.approval.models import (
                RecommendationStatus,
                StoredRecommendation,
            )
            from ozon_agent.decision.models import RecommendationAction

            now = datetime.now(UTC)
            rec = StoredRecommendation(
                id="rec-test-1234-5678-9012",
                created_at=now,
                updated_at=now,
                sku="SKU-REC",
                action=RecommendationAction.INCREASE_BUDGET,
                reason="Test reason",
                status=RecommendationStatus.PENDING,
            )
            mock_get.return_value = rec

            result = runner.invoke(main, [
                "experiments", "create-from-recommendation", "rec-test-1234-5678-9012",
            ])
            assert result.exit_code == 0
            assert "APPROVED or EXECUTED" in result.output
