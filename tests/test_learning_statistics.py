from __future__ import annotations

from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso
from ozon_agent.learning.statistics import (
    build_category_statistics,
    build_experiment_statistics,
    build_experiment_type_statistics,
    build_success_rate,
)


def test_build_success_rate_counts_partial_as_half() -> None:
    rows = [
        _experiment("success", ExperimentResult.SUCCESS),
        _experiment("partial", ExperimentResult.PARTIAL_SUCCESS),
        _experiment("failure", ExperimentResult.FAILURE),
    ]

    assert build_success_rate(rows) == 0.5


def test_statistics_group_by_category_and_type() -> None:
    rows = [_experiment("exp-1", ExperimentResult.SUCCESS)]

    stats = build_experiment_statistics(rows)

    assert stats.total_experiments == 1
    assert build_category_statistics(rows)["Rugs"]["count"] == 1
    assert build_experiment_type_statistics(rows)["PRICE_CHANGE"]["count"] == 1
    assert stats.average_metric_lift["orders"] == 12.0


def _experiment(experiment_id: str, result: ExperimentResult) -> Experiment:
    now = utc_now_iso()
    return Experiment(
        id=experiment_id,
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        experiment_type=ExperimentType.PRICE_CHANGE,
        category="Rugs",
        metrics={"orders_delta_pct": 12.0, "profit_delta_pct": 5.0},
        result=result,
    )
