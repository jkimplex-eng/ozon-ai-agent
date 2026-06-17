from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso
from ozon_agent.learning.repository import (
    delete_json,
    list_json,
    read_json,
    to_jsonable,
    write_json,
)


def save_experiment(experiment: Experiment, root: str | Path | None = None) -> str:
    write_json("experiments", experiment.id, to_jsonable(experiment), root=root)
    return experiment.id


def load_experiment(experiment_id: str, root: str | Path | None = None) -> Experiment | None:
    payload = read_json("experiments", experiment_id, root=root)
    if payload is None:
        return None
    return _experiment_from_dict(payload)


def list_experiments(root: str | Path | None = None, limit: int | None = None) -> list[Experiment]:
    experiments = [_experiment_from_dict(row) for row in list_json("experiments", root=root)]
    experiments.sort(key=lambda item: item.updated_at, reverse=True)
    return experiments if limit is None else experiments[:limit]


def search_experiments(query: str, root: str | Path | None = None) -> list[Experiment]:
    normalized = query.strip().lower()
    if not normalized:
        return list_experiments(root=root)
    return [
        experiment
        for experiment in list_experiments(root=root)
        if normalized in _search_text(experiment)
    ]


def delete_experiment(experiment_id: str, root: str | Path | None = None) -> bool:
    return delete_json("experiments", experiment_id, root=root)


def update_experiment(
    experiment_id: str,
    root: str | Path | None = None,
    **fields: Any,
) -> Experiment | None:
    experiment = load_experiment(experiment_id, root=root)
    if experiment is None:
        return None
    for key, value in fields.items():
        if hasattr(experiment, key) and value is not None:
            setattr(experiment, key, value)
    experiment.updated_at = utc_now_iso()
    save_experiment(experiment, root=root)
    return experiment


def _experiment_from_dict(row: dict[str, Any]) -> Experiment:
    return Experiment(
        id=str(row["id"]),
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", row.get("created_at", ""))),
        sku=str(row.get("sku", "")),
        experiment_type=_coerce_type(row.get("experiment_type", ExperimentType.CUSTOM.value)),
        hypothesis_id=(
            str(row["hypothesis_id"]) if row.get("hypothesis_id") is not None else None
        ),
        title=str(row.get("title", "")),
        category=str(row.get("category", "")),
        subcategory=str(row.get("subcategory", "")),
        product_type=str(row.get("product_type", "")),
        price_range=str(row.get("price_range", "")),
        shop_size=str(row.get("shop_size", "")),
        period=str(row.get("period", "")),
        change_size=_optional_float(row.get("change_size")),
        expected_effect=_dict(row.get("expected_effect")),
        metrics=_dict(row.get("metrics")),
        result=_coerce_result(row.get("result", ExperimentResult.UNKNOWN.value)),
        metadata=_dict(row.get("metadata")),
    )


def _search_text(experiment: Experiment) -> str:
    return " ".join(
        [
            experiment.id,
            experiment.sku,
            experiment.experiment_type.value,
            experiment.title,
            experiment.category,
            experiment.subcategory,
            experiment.product_type,
            experiment.result.value,
        ]
    ).lower()


def _coerce_type(value: object) -> ExperimentType:
    try:
        return ExperimentType(str(value))
    except ValueError:
        return ExperimentType.CUSTOM


def _coerce_result(value: object) -> ExperimentResult:
    try:
        return ExperimentResult(str(value))
    except ValueError:
        return ExperimentResult.UNKNOWN


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
