from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from ozon_agent.learning.experiment_store import list_experiments
from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentStatistics


def build_experiment_statistics(
    experiments: list[Experiment] | None = None,
) -> ExperimentStatistics:
    rows = experiments if experiments is not None else list_experiments()
    return ExperimentStatistics(
        total_experiments=len(rows),
        success_rate=build_success_rate(rows),
        by_category=build_category_statistics(rows),
        by_experiment_type=build_experiment_type_statistics(rows),
        average_metric_lift=_average_metric_lift(rows),
    )


def build_success_rate(experiments: list[Experiment]) -> float:
    comparable = [item for item in experiments if item.result is not ExperimentResult.UNKNOWN]
    if not comparable:
        return 0.0
    successful = sum(1 for item in comparable if item.result is ExperimentResult.SUCCESS)
    partial = sum(1 for item in comparable if item.result is ExperimentResult.PARTIAL_SUCCESS)
    return (successful + partial * 0.5) / len(comparable)


def build_category_statistics(experiments: list[Experiment]) -> dict[str, dict[str, object]]:
    return _group_statistics(experiments, lambda item: item.category or "UNKNOWN")


def build_experiment_type_statistics(experiments: list[Experiment]) -> dict[str, dict[str, object]]:
    return _group_statistics(experiments, lambda item: item.experiment_type.value)


def _group_statistics(
    experiments: list[Experiment],
    key_fn: Callable[[Experiment], str],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[Experiment]] = defaultdict(list)
    for experiment in experiments:
        grouped[str(key_fn(experiment))].append(experiment)
    return {
        key: {
            "count": len(group),
            "success_rate": build_success_rate(group),
            "average_metric_lift": _average_metric_lift(group),
        }
        for key, group in grouped.items()
    }


def _average_metric_lift(experiments: list[Experiment]) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for experiment in experiments:
        for key, value in experiment.metrics.items():
            if key.endswith("_delta_pct") and isinstance(value, int | float):
                metric_name = key.removesuffix("_delta_pct")
                values[metric_name].append(float(value))
    return {
        key: round(sum(metric_values) / len(metric_values), 4)
        for key, metric_values in values.items()
        if metric_values
    }
