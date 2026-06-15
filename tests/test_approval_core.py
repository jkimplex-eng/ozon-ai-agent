from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ozon_agent.approval.models import (
    InvalidRecommendationTransitionError,
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.approval.repository import (
    _build_list_recommendations_query,
    get_recommendation,
    list_recommendations,
    override_connection_factory,
    save_recommendation,
)
from ozon_agent.approval.serializers import recommendation_from_json, recommendation_to_json
from ozon_agent.approval.workflow import (
    approve_recommendation,
    close_recommendation,
    mark_executed,
    mark_observed,
    reject_recommendation,
)
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel


def test_save_list_and_get_recommendation() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        loaded = get_recommendation(recommendation.id)
        assert loaded is not None
        assert loaded.sku == recommendation.sku
        listed = list_recommendations()
        assert len(listed) == 1


def test_approve_recommendation() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        approved = approve_recommendation(recommendation.id, approved_by="mimo")
        assert approved.status is RecommendationStatus.APPROVED
        assert approved.approved_by == "mimo"


def test_reject_recommendation() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        rejected = reject_recommendation(recommendation.id, rejected_by="mimo", reason="too risky")
        assert rejected.status is RecommendationStatus.REJECTED
        assert rejected.rejection_reason == "too risky"


def test_invalid_transition_raises() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        approve_recommendation(recommendation.id, approved_by="mimo")
        with pytest_raises(InvalidRecommendationTransitionError):
            reject_recommendation(recommendation.id, rejected_by="mimo", reason="late reject")


def test_terminal_states_stay_terminal() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        rejected = reject_recommendation(recommendation.id, rejected_by="mimo", reason="stop")
        assert rejected.status is RecommendationStatus.REJECTED
        with pytest_raises(InvalidRecommendationTransitionError):
            approve_recommendation(recommendation.id, approved_by="again")


def test_full_lifecycle_progression() -> None:
    with fake_repository():
        recommendation = _sample_recommendation()
        save_recommendation(recommendation)
        approve_recommendation(recommendation.id, approved_by="mimo")
        executed = mark_executed(recommendation.id)
        observed = mark_observed(recommendation.id)
        closed = close_recommendation(recommendation.id)
        assert executed.status is RecommendationStatus.EXECUTED
        assert observed.status is RecommendationStatus.OBSERVED
        assert closed.status is RecommendationStatus.CLOSED


def test_json_serialization_round_trip() -> None:
    recommendation = _sample_recommendation()
    payload = recommendation_to_json(recommendation)
    restored = recommendation_from_json(payload)
    assert restored.id == recommendation.id
    assert restored.expected_effect == recommendation.expected_effect


def test_empty_database_results() -> None:
    with fake_repository():
        assert get_recommendation("missing") is None
        assert list_recommendations() == []


def test_list_recommendations_without_status_filter() -> None:
    sql, params = _build_list_recommendations_query(status=None, sku=None, limit=50)
    assert "status = %(status)s" not in sql
    assert "sku = %(sku)s" not in sql
    assert params == {"limit": 50}


def test_list_recommendations_with_pending_status_filter() -> None:
    sql, params = _build_list_recommendations_query(
        status=RecommendationStatus.PENDING,
        sku=None,
        limit=50,
    )
    assert "WHERE status = %(status)s" in sql
    assert params["status"] == "PENDING"


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
        if "INSERT INTO recommendations" in sql:
            record = deepcopy(params)
            record["expected_effect"] = recommendation_from_json(
                {
                    "id": params["id"],
                    "created_at": params["created_at"].isoformat(),
                    "updated_at": params["updated_at"].isoformat(),
                    "sku": params["sku"],
                    "product_name": params["product_name"],
                    "action": params["action"],
                    "reason": params["reason"],
                    "confidence_score": params["confidence_score"],
                    "confidence_level": params["confidence_level"],
                    "risk_score": params["risk_score"],
                    "risk_level": params["risk_level"],
                    "expected_effect": {},
                    "supporting_metrics": {},
                    "status": params["status"],
                }
            ).expected_effect
            existing = [
                row for row in self.storage["recommendations"] if row["id"] != params["id"]
            ]
            record["expected_effect"] = json_load(params["expected_effect"])
            record["supporting_metrics"] = json_load(params["supporting_metrics"])
            self.storage["recommendations"] = existing + [record]
            self.description = None
            self._rows = []
            return
        if sql.strip().startswith("SELECT * FROM recommendations WHERE id"):
            self._rows = [
                deepcopy(row)
                for row in self.storage["recommendations"]
                if row["id"] == params["id"]
            ]
            self.description = ["id"]
            return
        if sql.strip().startswith("SELECT * FROM recommendations"):
            rows = [deepcopy(row) for row in self.storage["recommendations"]]
            if "status" in params:
                rows = [row for row in rows if row["status"] == params["status"]]
            if "sku" in params:
                rows = [row for row in rows if row["sku"] == params["sku"]]
            rows.sort(key=lambda item: item["created_at"], reverse=True)
            self._rows = rows[: int(params["limit"])]
            self.description = ["id"]
            return
        if sql.strip().startswith("UPDATE recommendations"):
            for index, row in enumerate(self.storage["recommendations"]):
                if row["id"] != params["id"]:
                    continue
                updated = deepcopy(row)
                for key, value in params.items():
                    if key == "id":
                        continue
                    if value is not None:
                        updated[key] = value
                self.storage["recommendations"][index] = updated
                break
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


@contextmanager
def fake_repository() -> Any:
    storage = {"recommendations": []}

    @contextmanager
    def _factory() -> Any:
        yield _FakeConnection(storage)

    with override_connection_factory(_factory):
        yield storage


def _sample_recommendation() -> StoredRecommendation:
    now = datetime.now(UTC)
    return StoredRecommendation(
        id="rec-1",
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        product_name="Product 1",
        action=RecommendationAction.INCREASE_BUDGET,
        reason="Strong ad efficiency",
        confidence_score=0.82,
        confidence_level=ConfidenceLevel.HIGH,
        risk_score=0.25,
        risk_level=RiskLevel.LOW,
        expected_effect={"orders": {"delta_pct": 12.0}},
        supporting_metrics={"roas": 5.2},
        status=RecommendationStatus.PENDING,
        source="decision_engine",
    )


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


def json_load(value: str) -> dict[str, Any]:
    import json

    return dict(json.loads(value))
