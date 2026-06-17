from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ozon_agent.learning.experiment_store import list_experiments, load_experiment
from ozon_agent.learning.models import Experiment, SimilarityMatch


def find_similar_experiments(
    experiment: Experiment,
    candidates: Iterable[Experiment] | None = None,
    limit: int = 10,
    root: str | Path | None = None,
) -> list[SimilarityMatch]:
    source = list(candidates) if candidates is not None else list_experiments(root=root)
    matches = [
        calculate_similarity(experiment, candidate)
        for candidate in source
        if candidate.id != experiment.id
    ]
    return rank_similar_experiments(matches)[:limit]


def rank_similar_experiments(matches: list[SimilarityMatch]) -> list[SimilarityMatch]:
    return sorted(matches, key=lambda item: item.score, reverse=True)


def calculate_similarity(experiment: Experiment, candidate: Experiment) -> SimilarityMatch:
    score = 0.0
    reasons: list[str] = []
    score += _match(experiment.category, candidate.category, 0.18, "same category", reasons)
    score += _match(
        experiment.subcategory,
        candidate.subcategory,
        0.12,
        "same subcategory",
        reasons,
    )
    if experiment.experiment_type is candidate.experiment_type:
        score += 0.22
        reasons.append("same experiment type")
    score += _match(
        experiment.price_range,
        candidate.price_range,
        0.10,
        "same price range",
        reasons,
    )
    score += _match(experiment.shop_size, candidate.shop_size, 0.08, "same shop size", reasons)
    score += _match(experiment.period, candidate.period, 0.08, "same period", reasons)
    score += _match(
        experiment.product_type,
        candidate.product_type,
        0.12,
        "same product type",
        reasons,
    )
    score += _change_similarity(experiment.change_size, candidate.change_size, reasons)
    return SimilarityMatch(
        experiment_id=candidate.id,
        score=round(min(score, 1.0), 4),
        reasons=reasons,
        result=candidate.result,
        success_score=float(candidate.metrics.get("success_score", 0.0)),
    )


def find_similar_experiments_by_id(
    experiment_id: str,
    limit: int = 10,
    root: str | Path | None = None,
) -> list[SimilarityMatch]:
    experiment = load_experiment(experiment_id, root=root)
    if experiment is None:
        return []
    return find_similar_experiments(experiment, limit=limit, root=root)


def _match(left: str, right: str, weight: float, reason: str, reasons: list[str]) -> float:
    if left and right and left.strip().lower() == right.strip().lower():
        reasons.append(reason)
        return weight
    return 0.0


def _change_similarity(left: float | None, right: float | None, reasons: list[str]) -> float:
    if left is None or right is None:
        return 0.0
    distance = abs(left - right)
    if distance <= 2:
        reasons.append("similar change size")
        return 0.10
    if distance <= 5:
        reasons.append("near change size")
        return 0.05
    return 0.0
