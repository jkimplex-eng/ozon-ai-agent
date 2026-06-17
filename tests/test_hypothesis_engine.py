from __future__ import annotations

import pytest

from ozon_agent.learning.hypothesis_engine import (
    create_hypothesis,
    list_hypotheses,
    search_hypotheses,
    validate_hypothesis,
)
from ozon_agent.learning.models import ExperimentType, Hypothesis, utc_now_iso


def test_create_list_and_search_hypotheses(tmp_path) -> None:
    hypothesis = create_hypothesis(
        sku="SKU-1",
        experiment_type=ExperimentType.PRICE_CHANGE,
        statement="Lower price by 5%",
        expected_effect={"orders_delta_pct": 10, "profit_min": 0},
        category="Rugs",
        root=tmp_path,
    )

    assert hypothesis in list_hypotheses(root=tmp_path)
    assert search_hypotheses("lower price", root=tmp_path) == [hypothesis]


def test_validate_hypothesis_rejects_missing_expected_effect() -> None:
    hypothesis = Hypothesis(
        id="hypothesis-1",
        created_at=utc_now_iso(),
        sku="SKU-1",
        experiment_type=ExperimentType.CUSTOM,
        statement="Test title",
        expected_effect={},
    )

    with pytest.raises(ValueError):
        validate_hypothesis(hypothesis)
