from __future__ import annotations

from ozon_agent.learning.experiment_store import list_experiments, load_experiment
from ozon_agent.learning.learning_engine import aggregate_results
from ozon_agent.learning.models import Experiment, ExperimentStatistics
from ozon_agent.learning.statistics import build_experiment_statistics


def build_learning_report(experiments: list[Experiment] | None = None) -> str:
    rows = experiments if experiments is not None else list_experiments()
    stats = build_experiment_statistics(rows)
    lines = [
        "Experiment Learning Report",
        f"Total experiments: {stats.total_experiments}",
        f"Success rate: {stats.success_rate:.0%}",
    ]
    if stats.average_metric_lift:
        lines.append("Average metric lift:")
        for metric, value in sorted(stats.average_metric_lift.items()):
            lines.append(f"  - {metric}: {value:+.2f}%")
    return "\n".join(lines)


def build_category_report(category: str, experiments: list[Experiment] | None = None) -> str:
    rows = [
        experiment
        for experiment in (experiments if experiments is not None else list_experiments())
        if experiment.category == category
    ]
    aggregate = aggregate_results(rows)
    lines = [
        f"Category Learning Report: {category}",
        f"Experiments: {aggregate['experiment_count']}",
        f"Success rate: {float(aggregate['success_rate']):.0%}",
    ]
    for metric, value in dict(aggregate["average_metric_lift"]).items():
        lines.append(f"  - {metric}: {float(value):+.2f}%")
    return "\n".join(lines)


def build_experiment_report(experiment_id: str) -> str:
    experiment = load_experiment(experiment_id)
    if experiment is None:
        return f"Experiment {experiment_id} not found."
    return "\n".join(
        [
            f"Experiment: {experiment.id}",
            f"SKU: {experiment.sku}",
            f"Type: {experiment.experiment_type.value}",
            f"Result: {experiment.result.value}",
            f"Category: {experiment.category or 'unknown'}",
            f"Title: {experiment.title}",
        ]
    )


def statistics_to_dict(stats: ExperimentStatistics) -> dict[str, object]:
    return {
        "total_experiments": stats.total_experiments,
        "success_rate": stats.success_rate,
        "by_category": stats.by_category,
        "by_experiment_type": stats.by_experiment_type,
        "average_metric_lift": stats.average_metric_lift,
    }
