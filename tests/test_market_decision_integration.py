from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pandas as pd
from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.decision import build_decision_features, generate_recommendations
from ozon_agent.decision.market_context import build_market_context
from ozon_agent.research.knowledge.insight_store import save_insights
from ozon_agent.research.knowledge.models import MarketInsightRecord


def test_recommendation_enrichment_with_market_context(tmp_path) -> None:
    save_insights(
        [
            _record("PRICE_DROP", "SKU-1", 90, "3 competitors lowered price"),
            _record("REVIEW_SURGE", "SKU-1", 88, "2 competitors gained reviews"),
        ],
        storage_dir=tmp_path,
    )
    features = _features()
    contexts = {"SKU-1": build_market_context("SKU-1", storage_dir=tmp_path)}

    recommendations = generate_recommendations(features, market_contexts=contexts)

    assert recommendations
    recommendation = recommendations[0]
    assert recommendation.market_signals
    assert recommendation.market_risks
    assert "market context" in recommendation.reason
    assert recommendation.supporting_metrics["market_context"]["price_pressure"] == "HIGH"


def test_recommendation_without_market_context_remains_supported() -> None:
    recommendations = generate_recommendations(_features(), include_market_context=False)

    assert recommendations
    assert recommendations[0].market_signals == []
    assert recommendations[0].supporting_metrics["market_context"]["price_pressure"] == "LOW"


def test_recommendations_market_context_cli(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_MARKET_KNOWLEDGE_DIR", str(tmp_path))
    save_insights([_record("PRICE_DROP", "SKU-1", 90)], storage_dir=tmp_path)

    result = CliRunner().invoke(main, ["recommendations", "market-context", "--sku", "SKU-1"])

    assert result.exit_code == 0
    assert "Recommendation Market Context" in result.output
    assert "Price pressure" in result.output
    assert "HIGH" in result.output


def test_recommendations_explain_cli(monkeypatch) -> None:
    rows = {
        "SELECT * FROM products": [{"sku": "SKU-1", "name": "Product", "cost_price": 100}],
        "SELECT * FROM sales": [
            {"sku": "SKU-1", "date": "2026-06-13", "quantity": 6, "revenue": 1200}
        ],
        "SELECT * FROM advertising": [
            {
                "sku": "SKU-1",
                "campaign_id": "C1",
                "date": "2026-06-13",
                "spend": 100,
                "impressions": 1000,
                "clicks": 50,
                "orders": 5,
                "revenue": 600,
            }
        ],
        "SELECT * FROM forecasts": [],
        "SELECT * FROM stock": [],
    }

    with patch("ozon_agent.db.connection.execute_query", side_effect=lambda query: rows[query]):
        result = CliRunner().invoke(main, ["recommendations", "explain", "--top", "1"])

    assert result.exit_code == 0
    assert "Recommendation 1" in result.output
    assert "Market signals" in result.output or "Supporting metrics" in result.output


def _features():
    return build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU-1", "name": "Product", "cost_price": 100}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU-1", "date": "2026-06-13", "quantity": 6, "revenue": 1200}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU-1",
                    "campaign_id": "C1",
                    "date": "2026-06-13",
                    "spend": 100,
                    "impressions": 1000,
                    "clicks": 50,
                    "orders": 5,
                    "revenue": 600,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(),
    )


def _record(
    insight_type: str,
    sku: str,
    score: float,
    message: str = "market insight",
) -> MarketInsightRecord:
    return MarketInsightRecord(
        id=f"{insight_type}-{sku}",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        insight_type=insight_type,
        sku=sku,
        message=message,
        severity="HIGH",
        metrics={"score": score, "priority": "HIGH"},
    )
