from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.learning.models import ExperimentType, Hypothesis, new_learning_id, utc_now_iso
from ozon_agent.learning.repository import list_json, read_json, to_jsonable, write_json


def create_hypothesis(
    sku: str,
    experiment_type: ExperimentType | str,
    statement: str,
    expected_effect: dict[str, Any],
    success_criteria: dict[str, Any] | None = None,
    category: str = "",
    subcategory: str = "",
    product_type: str = "",
    metadata: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> Hypothesis:
    hypothesis = Hypothesis(
        id=new_learning_id("hypothesis"),
        created_at=utc_now_iso(),
        sku=sku,
        experiment_type=_coerce_type(experiment_type),
        statement=statement,
        expected_effect=dict(expected_effect),
        success_criteria=success_criteria or {},
        category=category,
        subcategory=subcategory,
        product_type=product_type,
        metadata=metadata or {},
    )
    validate_hypothesis(hypothesis)
    write_json("hypotheses", hypothesis.id, to_jsonable(hypothesis), root=root)
    return hypothesis


def validate_hypothesis(hypothesis: Hypothesis) -> bool:
    if not hypothesis.sku.strip():
        raise ValueError("Hypothesis requires sku")
    if not hypothesis.statement.strip():
        raise ValueError("Hypothesis requires statement")
    if not hypothesis.expected_effect:
        raise ValueError("Hypothesis requires expected_effect")
    return True


def get_hypothesis(hypothesis_id: str, root: str | Path | None = None) -> Hypothesis | None:
    payload = read_json("hypotheses", hypothesis_id, root=root)
    return _hypothesis_from_dict(payload) if payload is not None else None


def list_hypotheses(root: str | Path | None = None) -> list[Hypothesis]:
    hypotheses = [_hypothesis_from_dict(row) for row in list_json("hypotheses", root=root)]
    return sorted(hypotheses, key=lambda item: item.created_at, reverse=True)


def search_hypotheses(query: str, root: str | Path | None = None) -> list[Hypothesis]:
    normalized = query.strip().lower()
    if not normalized:
        return list_hypotheses(root=root)
    return [
        hypothesis
        for hypothesis in list_hypotheses(root=root)
        if normalized in _search_text(hypothesis)
    ]


def _hypothesis_from_dict(row: dict[str, Any]) -> Hypothesis:
    return Hypothesis(
        id=str(row["id"]),
        created_at=str(row.get("created_at", "")),
        sku=str(row.get("sku", "")),
        experiment_type=_coerce_type(row.get("experiment_type", ExperimentType.CUSTOM.value)),
        statement=str(row.get("statement", "")),
        expected_effect=dict(row.get("expected_effect", {})),
        success_criteria=dict(row.get("success_criteria", {})),
        category=str(row.get("category", "")),
        subcategory=str(row.get("subcategory", "")),
        product_type=str(row.get("product_type", "")),
        metadata=dict(row.get("metadata", {})),
    )


def _search_text(hypothesis: Hypothesis) -> str:
    return " ".join(
        [
            hypothesis.id,
            hypothesis.sku,
            hypothesis.experiment_type.value,
            hypothesis.statement,
            hypothesis.category,
            hypothesis.subcategory,
            hypothesis.product_type,
        ]
    ).lower()


def _coerce_type(value: ExperimentType | str | object) -> ExperimentType:
    if isinstance(value, ExperimentType):
        return value
    try:
        return ExperimentType(str(value))
    except ValueError:
        return ExperimentType.CUSTOM
