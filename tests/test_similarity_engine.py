from __future__ import annotations

from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso
from ozon_agent.learning.similarity import calculate_similarity, find_similar_experiments


def test_calculate_similarity_uses_market_factors() -> None:
    target = _experiment("target", ExperimentType.PRICE_CHANGE, "Rugs", 5)
    candidate = _experiment("candidate", ExperimentType.PRICE_CHANGE, "Rugs", 6)

    match = calculate_similarity(target, candidate)

    assert match.score >= 0.7
    assert "same category" in match.reasons
    assert "same experiment type" in match.reasons


def test_find_similar_experiments_ranks_best_first() -> None:
    target = _experiment("target", ExperimentType.PRICE_CHANGE, "Rugs", 5)
    strong = _experiment("strong", ExperimentType.PRICE_CHANGE, "Rugs", 5)
    weak = _experiment("weak", ExperimentType.IMAGE_CHANGE, "Shoes", 20)

    matches = find_similar_experiments(target, candidates=[weak, strong])

    assert [match.experiment_id for match in matches] == ["strong", "weak"]


def _experiment(
    experiment_id: str,
    experiment_type: ExperimentType,
    category: str,
    change_size: float,
) -> Experiment:
    now = utc_now_iso()
    return Experiment(
        id=experiment_id,
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        experiment_type=experiment_type,
        category=category,
        subcategory="Round",
        product_type="Carpet",
        price_range="1000-1500",
        shop_size="small",
        period="2026-06",
        change_size=change_size,
        result=ExperimentResult.SUCCESS,
    )
