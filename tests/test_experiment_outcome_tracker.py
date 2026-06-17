from __future__ import annotations

from ozon_agent.learning.models import ExperimentMetric, ExperimentResult
from ozon_agent.learning.outcome_tracker import calculate_delta, evaluate_success, record_outcome


def test_record_success_outcome(tmp_path) -> None:
    metrics = [
        ExperimentMetric(
            name="orders",
            baseline=100,
            actual=118,
            expected_delta_pct=10,
            actual_delta_pct=18,
        ),
        ExperimentMetric(
            name="profit",
            baseline=1000,
            actual=1060,
            expected_delta_pct=0,
            actual_delta_pct=6,
        ),
    ]

    outcome = record_outcome("exp-1", metrics, root=tmp_path)

    assert outcome.result is ExperimentResult.SUCCESS
    assert outcome.success_score > 0.9


def test_partial_success_when_profit_falls() -> None:
    metrics = [
        ExperimentMetric(name="orders", expected_delta_pct=10, actual_delta_pct=12),
        ExperimentMetric(name="profit", expected_delta_pct=0, actual_delta_pct=-15),
    ]

    assert evaluate_success(metrics) is ExperimentResult.PARTIAL_SUCCESS


def test_failure_when_orders_decline() -> None:
    metrics = [ExperimentMetric(name="orders", expected_delta_pct=10, actual_delta_pct=-10)]

    assert evaluate_success(metrics) is ExperimentResult.FAILURE


def test_calculate_delta() -> None:
    assert calculate_delta(100, 118) == 18
    assert calculate_delta(0, 100) is None
