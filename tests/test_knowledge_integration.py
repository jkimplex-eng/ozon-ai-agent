from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.decision import build_decision_features, generate_recommendations


def test_recommendation_contains_knowledge_context() -> None:
    features = _features()

    recommendations = generate_recommendations(features, include_market_context=False)

    assert recommendations
    recommendation = recommendations[0]
    assert recommendation.knowledge_signals
    assert recommendation.knowledge_rules
    assert recommendation.knowledge_sources


def test_recommendation_dict_contains_knowledge_context() -> None:
    from ozon_agent.decision.recommendation_summary import recommendation_to_dict

    recommendation = generate_recommendations(_features(), include_market_context=False)[0]
    payload = recommendation_to_dict(recommendation)

    assert payload["knowledge_signals"]
    assert payload["knowledge_rules"]
    assert payload["knowledge_sources"]


def test_knowledge_cli_commands() -> None:
    runner = CliRunner()

    domains = runner.invoke(main, ["knowledge", "domains"])
    rules = runner.invoke(main, ["knowledge", "rules"])
    search = runner.invoke(main, ["knowledge", "search", "CTR"])
    explain = runner.invoke(main, ["knowledge", "explain", "--query", "CTR"])

    assert domains.exit_code == 0
    assert "SEO" in domains.output
    assert rules.exit_code == 0
    assert "Marketplace Knowledge Rules" in rules.output
    assert search.exit_code == 0
    assert "CTR" in search.output
    assert explain.exit_code == 0
    assert "RULE" in explain.output


def test_recommendations_explain_includes_knowledge_rules() -> None:
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
    assert "Knowledge rules" in result.output


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
