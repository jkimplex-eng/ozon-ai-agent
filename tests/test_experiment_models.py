from datetime import UTC, datetime

from ozon_agent.decision.models import RecommendationAction, RiskLevel
from ozon_agent.experiments.models import (
    ExperimentCreateRequest,
    ExperimentStatus,
    build_experiment,
    build_experiment_event,
    build_experiment_metric,
    build_experiment_outcome,
)
from ozon_agent.experiments.serializers import experiment_from_json, experiment_to_json


def test_build_experiment_defaults_to_draft() -> None:
    experiment = build_experiment(
        ExperimentCreateRequest(
            sku="SKU-1",
            title="Budget test",
            hypothesis="More budget increases revenue",
            action=RecommendationAction.INCREASE_BUDGET,
            risk_level=RiskLevel.MEDIUM,
        )
    )
    assert experiment.status is ExperimentStatus.DRAFT
    assert experiment.sku == "SKU-1"


def test_experiment_round_trip_json() -> None:
    now = datetime.now(UTC)
    payload = {
        "id": "exp-1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "recommendation_id": "rec-1",
        "sku": "SKU-1",
        "title": "Title",
        "hypothesis": "Hypothesis",
        "action": "INCREASE_BUDGET",
        "status": "READY",
        "risk_level": "LOW",
        "confidence_score": 0.7,
        "started_at": None,
        "ended_at": None,
        "created_by": "mimo",
        "notes": "note",
    }
    experiment = experiment_from_json(payload)
    assert experiment_to_json(experiment)["sku"] == "SKU-1"


def test_metric_event_and_outcome_builders() -> None:
    metric = build_experiment_metric("exp-1", "baseline", "orders", 10.0)
    event = build_experiment_event("exp-1", "created", "Created")
    outcome = build_experiment_outcome(
        "exp-1",
        success_score=0.8,
        direction_accuracy=1.0,
        actual_effect={"orders": 12.0},
        expected_effect={"orders": {"delta_pct": 10.0}},
        summary="Good",
    )
    assert metric.period == "baseline"
    assert event.metadata == {}
    assert outcome.summary == "Good"
