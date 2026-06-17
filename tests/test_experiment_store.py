from __future__ import annotations

from ozon_agent.learning.experiment_store import (
    delete_experiment,
    list_experiments,
    load_experiment,
    save_experiment,
    search_experiments,
    update_experiment,
)
from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso


def test_experiment_store_round_trip(tmp_path) -> None:
    experiment = _experiment("exp-1")

    save_experiment(experiment, root=tmp_path)

    loaded = load_experiment("exp-1", root=tmp_path)
    assert loaded == experiment
    assert search_experiments("PRICE_CHANGE", root=tmp_path) == [experiment]


def test_update_and_delete_experiment(tmp_path) -> None:
    save_experiment(_experiment("exp-1"), root=tmp_path)

    updated = update_experiment("exp-1", root=tmp_path, result=ExperimentResult.SUCCESS)

    assert updated is not None
    assert updated.result is ExperimentResult.SUCCESS
    assert delete_experiment("exp-1", root=tmp_path)
    assert list_experiments(root=tmp_path) == []


def _experiment(experiment_id: str) -> Experiment:
    now = utc_now_iso()
    return Experiment(
        id=experiment_id,
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        experiment_type=ExperimentType.PRICE_CHANGE,
        title="Lower price by 5%",
        category="Rugs",
        subcategory="Round",
        product_type="Carpet",
        price_range="1000-1500",
        shop_size="small",
        period="2026-06",
        change_size=5.0,
        metrics={"orders_delta_pct": 12.0, "profit_delta_pct": 4.0},
        result=ExperimentResult.SUCCESS,
    )
