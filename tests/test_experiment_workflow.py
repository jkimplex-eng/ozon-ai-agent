from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from typing import Any

from ozon_agent.decision.models import RecommendationAction
from ozon_agent.experiments.models import (
    Experiment,
    ExperimentCreateRequest,
    ExperimentStatus,
    InvalidExperimentTransitionError,
)
from ozon_agent.experiments.repository import override_connection_factory
from ozon_agent.experiments.workflow import (
    cancel_experiment,
    complete_experiment,
    create_experiment,
    fail_experiment,
    mark_ready,
    pause_experiment,
    start_experiment,
)


def test_create_experiment() -> None:
    with fake_workflow_repository():
        experiment = create_experiment(
            ExperimentCreateRequest(
                sku="SKU-1",
                title="Budget test",
                hypothesis="Higher budget improves orders",
                action=RecommendationAction.INCREASE_BUDGET,
            )
        )
        assert experiment.status is ExperimentStatus.DRAFT


def test_valid_status_transitions() -> None:
    with fake_workflow_repository():
        experiment = _persisted_experiment()
        ready = mark_ready(experiment.id)
        running = start_experiment(experiment.id)
        paused = pause_experiment(experiment.id)
        resumed = start_experiment(experiment.id)
        completed = complete_experiment(experiment.id)
        assert ready.status is ExperimentStatus.READY
        assert running.status is ExperimentStatus.RUNNING
        assert paused.status is ExperimentStatus.PAUSED
        assert resumed.status is ExperimentStatus.RUNNING
        assert completed.status is ExperimentStatus.COMPLETED


def test_invalid_transition_raises() -> None:
    with fake_workflow_repository():
        experiment = _persisted_experiment()
        with pytest_raises(InvalidExperimentTransitionError):
            complete_experiment(experiment.id)


def test_terminal_states_remain_terminal() -> None:
    with fake_workflow_repository():
        experiment = _persisted_experiment()
        mark_ready(experiment.id)
        cancelled = cancel_experiment(experiment.id, "stop")
        assert cancelled.status is ExperimentStatus.CANCELLED
        with pytest_raises(InvalidExperimentTransitionError):
            start_experiment(experiment.id)


def test_fail_transition_from_non_terminal() -> None:
    with fake_workflow_repository():
        experiment = _persisted_experiment()
        failed = fail_experiment(experiment.id, "error")
        assert failed.status is ExperimentStatus.FAILED


@contextmanager
def fake_workflow_repository() -> Any:
    storage = {"experiments": [], "metrics": [], "events": [], "outcomes": []}

    @contextmanager
    def _factory() -> Any:
        yield _FakeConnection(storage)

    with override_connection_factory(_factory):
        yield storage


def _persisted_experiment() -> Experiment:
    experiment = create_experiment(
        ExperimentCreateRequest(
            sku="SKU-1",
            title="Budget test",
            hypothesis="Higher budget improves orders",
            action=RecommendationAction.INCREASE_BUDGET,
        )
    )
    return experiment


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
        if "INSERT INTO experiment_events" in sql:
            record = deepcopy(params)
            existing = [row for row in self.storage["events"] if row["id"] != params["id"]]
            self.storage["events"] = existing + [record]
            self.description = None
            self._rows = []
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


def pytest_raises(expected_exception: type[Exception]) -> Any:
    class _Raises:
        def __enter__(self) -> _Raises:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            if exc_type is None:
                raise AssertionError(f"Expected {expected_exception.__name__} to be raised")
            if not issubclass(exc_type, expected_exception):
                return False
            return True

    return _Raises()
