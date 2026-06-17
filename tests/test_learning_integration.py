from __future__ import annotations

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.decision.models import DecisionFeature, Opportunity, OpportunityType
from ozon_agent.decision.recommendation_engine import generate_recommendation
from ozon_agent.decision.recommendation_summary import (
    format_recommendation_text,
    recommendation_to_dict,
)
from ozon_agent.learning.experiment_store import save_experiment
from ozon_agent.learning.hypothesis_engine import create_hypothesis
from ozon_agent.learning.learning_engine import learn_from_experiment
from ozon_agent.learning.models import Experiment, ExperimentResult, ExperimentType, utc_now_iso


def test_recommendation_contains_learning_context(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_EXPERIMENT_ROOT", str(tmp_path))
    experiment = _experiment("exp-1")
    save_experiment(experiment, root=tmp_path)
    learn_from_experiment(experiment, root=tmp_path)

    recommendation = generate_recommendation(_feature(), _opportunity())
    payload = recommendation_to_dict(recommendation)
    text = format_recommendation_text(recommendation)

    assert payload["learning_signals"]
    assert payload["similar_experiments"]
    assert payload["historical_success_rate"] == 1.0
    assert "Learning:" in text


def test_experiment_learning_cli_commands(tmp_path) -> None:
    experiment = _experiment("exp-1")
    save_experiment(experiment, root=tmp_path)
    learn_from_experiment(experiment, root=tmp_path)
    create_hypothesis(
        sku="SKU-1",
        experiment_type=ExperimentType.AD_BUDGET_CHANGE,
        statement="Increase ad budget on efficient traffic",
        expected_effect={"orders_delta_pct": 10},
        category="Rugs",
        root=tmp_path,
    )
    runner = CliRunner()
    env = {"OZON_AGENT_EXPERIMENT_ROOT": str(tmp_path)}

    stats = runner.invoke(main, ["experiments", "stats"], env=env)
    insights = runner.invoke(main, ["experiments", "insights"], env=env)
    hypotheses = runner.invoke(main, ["experiments", "hypotheses"], env=env)
    similar = runner.invoke(main, ["experiments", "similar", "exp-1"], env=env)

    assert stats.exit_code == 0
    assert "Experiment Learning Statistics" in stats.output
    assert insights.exit_code == 0
    assert "Experiment Learning Insights" in insights.output
    assert hypotheses.exit_code == 0
    assert "Experiment Hypotheses" in hypotheses.output
    assert similar.exit_code == 0
    assert "Similar Experiments" in similar.output


def _feature() -> DecisionFeature:
    return DecisionFeature(
        sku="SKU-1",
        supporting_metrics={
            "category": "Rugs",
            "subcategory": "Round",
            "product_type": "Carpet",
            "price_range": "1000-1500",
            "shop_size": "small",
            "period": "2026-06",
        },
    )


def _opportunity() -> Opportunity:
    return Opportunity(
        opportunity_type=OpportunityType.AD_GROWTH,
        sku="SKU-1",
        severity="high",
        impact_score=0.9,
        reason="high ROAS and low DRR",
        metrics={},
    )


def _experiment(experiment_id: str) -> Experiment:
    now = utc_now_iso()
    return Experiment(
        id=experiment_id,
        created_at=now,
        updated_at=now,
        sku="SKU-1",
        experiment_type=ExperimentType.AD_BUDGET_CHANGE,
        title="Increase budget",
        category="Rugs",
        subcategory="Round",
        product_type="Carpet",
        price_range="1000-1500",
        shop_size="small",
        period="2026-06",
        change_size=10.0,
        metrics={"orders_delta_pct": 12.4, "profit_delta_pct": 5.0},
        result=ExperimentResult.SUCCESS,
    )
