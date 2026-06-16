from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ozon_agent.decision.models import RecommendationAction, RiskLevel
from ozon_agent.experiments.models import (
    Experiment,
    ExperimentEvent,
    ExperimentMetric,
    ExperimentOutcome,
    ExperimentStatus,
)
from ozon_agent.experiments.repository import (
    _build_list_experiments_query,
    get_experiment,
    get_experiment_outcome,
    list_experiment_events,
    list_experiment_metrics,
    list_experiments,
    override_connection_factory,
    save_experiment,
    save_experiment_event,
    save_experiment_metric,
    save_experiment_outcome,
)


def test_create_list_and_get_experiment() -> None:
    with fake_repository():
        experiment = _sample_experiment()
        save_experiment(experiment)
        loaded = get_experiment(experiment.id)
        assert loaded is not None
        assert loaded.sku == experiment.sku
        listed = list_experiments()
        assert len(listed) == 1


def test_list_experiments_without_filters() -> None:
    sql, params = _build_list_experiments_query(status=None, sku=None, limit=25)
    assert "status = %(status)s" not in sql
    assert "sku = %(sku)s" not in sql
    assert params == {"limit": 25}


def test_list_experiments_with_status_filter() -> None:
    sql, params = _build_list_experiments_query(
        status=ExperimentStatus.READY,
        sku=None,
        limit=25,
    )
    assert "status = %(status)s" in sql
    assert params["status"] == "READY"


def test_metric_save_and_list() -> None:
    with fake_repository():
        experiment = _sample_experiment()
        save_experiment(experiment)
        metric = ExperimentMetric(
            id="metric-1",
            experiment_id=experiment.id,
            period="baseline",
            metric_name="orders",
            metric_value=10.0,
            created_at=datetime.now(UTC),
        )
        save_experiment_metric(metric)
        metrics = list_experiment_metrics(experiment.id)
        assert len(metrics) == 1
        assert metrics[0].metric_name == "orders"


def test_event_save_and_list() -> None:
    with fake_repository():
        experiment = _sample_experiment()
        save_experiment(experiment)
        event = ExperimentEvent(
            id="event-1",
            experiment_id=experiment.id,
            created_at=datetime.now(UTC),
            event_type="created",
            message="Created",
            metadata={"actor": "mimo"},
        )
        save_experiment_event(event)
        events = list_experiment_events(experiment.id)
        assert len(events) == 1
        assert events[0].metadata["actor"] == "mimo"


def test_outcome_save_and_get() -> None:
    with fake_repository():
        experiment = _sample_experiment()
        save_experiment(experiment)
        outcome = ExperimentOutcome(
            id="out-1",
            experiment_id=experiment.id,
            created_at=datetime.now(UTC),
            success_score=0.8,
            direction_accuracy=1.0,
            actual_effect={"orders": 12.0},
            expected_effect={"orders": {"delta_pct": 10.0}},
            summary="Solid",
        )
        save_experiment_outcome(outcome)
        loaded = get_experiment_outcome(experiment.id)
        assert loaded is not None
        assert loaded.summary == "Solid"


def test_empty_db_results() -> None:
    with fake_repository():
        assert get_experiment("missing") is None
        assert list_experiments() == []
        assert list_experiment_metrics("missing") == []
        assert list_experiment_events("missing") == []
        assert get_experiment_outcome("missing") is None


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
        stripped = sql.strip()
        if "INSERT INTO experiments" in sql:
            record = deepcopy(params)
            existing = [row for row in self.storage["experiments"] if row["id"] != params["id"]]
            self.storage["experiments"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if stripped.startswith("SELECT * FROM experiments WHERE id"):
            self._rows = [
                deepcopy(row)
                for row in self.storage["experiments"]
                if row["id"] == params["id"]
            ]
            self.description = ["id"]
            return
        if stripped.startswith("SELECT * FROM experiments"):
            rows = [deepcopy(row) for row in self.storage["experiments"]]
            if "status" in params:
                rows = [row for row in rows if row["status"] == params["status"]]
            if "sku" in params:
                rows = [row for row in rows if row["sku"] == params["sku"]]
            rows.sort(key=lambda item: item["created_at"], reverse=True)
            self._rows = rows[: int(params["limit"])]
            self.description = ["id"]
            return
        if stripped.startswith("UPDATE experiments"):
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
        if "INSERT INTO experiment_metrics" in sql:
            record = deepcopy(params)
            existing = [row for row in self.storage["metrics"] if row["id"] != params["id"]]
            self.storage["metrics"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if stripped.startswith("SELECT * FROM experiment_metrics"):
            rows = [
                deepcopy(row)
                for row in self.storage["metrics"]
                if row["experiment_id"] == params["experiment_id"]
            ]
            if "period" in params:
                rows = [row for row in rows if row["period"] == params["period"]]
            rows.sort(key=lambda item: item["created_at"])
            self._rows = rows
            self.description = ["id"]
            return
        if "INSERT INTO experiment_events" in sql:
            record = deepcopy(params)
            record["metadata"] = _json_load(params["metadata"])
            existing = [row for row in self.storage["events"] if row["id"] != params["id"]]
            self.storage["events"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if stripped.startswith("SELECT * FROM experiment_events"):
            rows = [
                deepcopy(row)
                for row in self.storage["events"]
                if row["experiment_id"] == params["experiment_id"]
            ]
            rows.sort(key=lambda item: item["created_at"])
            self._rows = rows
            self.description = ["id"]
            return
        if "INSERT INTO experiment_outcomes" in sql:
            record = deepcopy(params)
            record["actual_effect"] = _json_load(params["actual_effect"])
            record["expected_effect"] = _json_load(params["expected_effect"])
            existing = [row for row in self.storage["outcomes"] if row["id"] != params["id"]]
            self.storage["outcomes"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if stripped.startswith("SELECT * FROM experiment_outcomes WHERE experiment_id"):
            self._rows = [
                deepcopy(row)
                for row in self.storage["outcomes"]
                if row["experiment_id"] == params["experiment_id"]
            ]
            self.description = ["id"]
            return
        raise AssertionError(f"Unexpected SQL: {sql}")

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
    storage = {"experiments": [], "metrics": [], "events": [], "outcomes": []}

    @contextmanager
    def _factory() -> Any:
        yield _FakeConnection(storage)

    with override_connection_factory(_factory):
        yield storage


def _sample_experiment() -> Experiment:
    now = datetime.now(UTC)
    return Experiment(
        id="exp-1",
        created_at=now,
        updated_at=now,
        recommendation_id="rec-1",
        sku="SKU-1",
        title="Budget test",
        hypothesis="Higher budget improves orders",
        action=RecommendationAction.INCREASE_BUDGET,
        status=ExperimentStatus.DRAFT,
        risk_level=RiskLevel.MEDIUM,
        confidence_score=0.7,
        created_by="mimo",
        notes="note",
    )


def _json_load(value: str) -> dict[str, Any]:
    return dict(json.loads(value))
