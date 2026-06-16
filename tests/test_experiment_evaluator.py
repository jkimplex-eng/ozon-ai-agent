from datetime import UTC, datetime

from ozon_agent.decision.models import RecommendationAction
from ozon_agent.experiments.evaluator import evaluate_experiment
from ozon_agent.experiments.models import Experiment, ExperimentStatus


def test_evaluator_positive_case() -> None:
    evaluation = evaluate_experiment(
        experiment=_sample_experiment(),
        baseline_metrics={"orders": 10.0, "drr": 20.0},
        final_metrics={"orders": 12.0, "drr": 18.0},
        expected_effect={"orders": {"delta_pct": 15.0}, "drr": {"delta_pct": 5.0}},
    )
    assert evaluation.success_score is not None
    assert evaluation.direction_accuracy == 1.0
    assert evaluation.actual_effect["orders"] == 20.0


def test_evaluator_negative_case() -> None:
    evaluation = evaluate_experiment(
        experiment=_sample_experiment(),
        baseline_metrics={"orders": 10.0},
        final_metrics={"orders": 8.0},
        expected_effect={"orders": {"delta_pct": 15.0}},
    )
    assert evaluation.direction_accuracy == 0.0
    assert evaluation.success_score is not None
    assert evaluation.success_score < 0.5


def test_zero_baseline_is_handled() -> None:
    evaluation = evaluate_experiment(
        experiment=_sample_experiment(),
        baseline_metrics={"orders": 0.0},
        final_metrics={"orders": 3.0},
        expected_effect={"orders": {"delta_pct": 100.0}},
    )
    assert evaluation.actual_effect["orders"] == 300.0


def test_lower_is_better_metric_direction() -> None:
    evaluation = evaluate_experiment(
        experiment=_sample_experiment(),
        baseline_metrics={"cpc": 10.0},
        final_metrics={"cpc": 8.0},
        expected_effect={"cpc": {"delta_pct": 10.0}},
    )
    assert evaluation.direction_accuracy == 1.0


def test_empty_metrics_generate_summary() -> None:
    evaluation = evaluate_experiment(
        experiment=_sample_experiment(),
        baseline_metrics={},
        final_metrics={},
        expected_effect={},
    )
    assert evaluation.success_score is None
    assert "no baseline metrics" in evaluation.summary.lower()


def _sample_experiment() -> Experiment:
    now = datetime.now(UTC)
    return Experiment(
        id="exp-1",
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        title="Budget test",
        hypothesis="Higher budget improves orders",
        action=RecommendationAction.INCREASE_BUDGET,
        status=ExperimentStatus.RUNNING,
    )
