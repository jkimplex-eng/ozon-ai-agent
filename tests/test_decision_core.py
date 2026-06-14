from __future__ import annotations

import pandas as pd

from ozon_agent.decision import (
    ConfidenceLevel,
    OpportunityType,
    RiskLevel,
    build_decision_features,
    detect_ad_opportunities,
    detect_all_opportunities,
    detect_price_opportunities,
    detect_ranking_opportunities,
    detect_stock_opportunities,
    generate_recommendation,
    generate_recommendations,
    score_confidence,
    score_risk,
)


def test_empty_inputs_return_no_features() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame(),
        sales_df=pd.DataFrame(),
        advertising_df=pd.DataFrame(),
        forecasts_df=pd.DataFrame(),
    )
    assert features == []


def test_missing_optional_dataframes_do_not_crash() -> None:
    products = pd.DataFrame(
        [{"sku": "SKU1", "offer_id": "OF1", "name": "Product 1", "cost_price": 100}]
    )
    sales = pd.DataFrame(
        [{"sku": "SKU1", "date": "2026-06-10", "quantity": 2, "revenue": 500, "offer_id": "OF1"}]
    )
    advertising = pd.DataFrame(
        [
            {
                "sku": "SKU1",
                "campaign_id": "C1",
                "date": "2026-06-10",
                "spend": 50,
                "clicks": 10,
                "impressions": 400,
            }
        ]
    )
    features = build_decision_features(products, sales, advertising, pd.DataFrame())
    assert len(features) == 1
    assert features[0].sku == "SKU1"
    assert features[0].has_stock is False
    assert features[0].has_forecast is False


def test_stock_risk_detection() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU1", "name": "Stocked"}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU1", "date": "2026-06-13", "quantity": 5, "revenue": 1000}]
        ),
        advertising_df=pd.DataFrame(),
        forecasts_df=pd.DataFrame([{"sku": "SKU1", "stockout_probability": 0.85}]),
        stock_df=pd.DataFrame([{"sku": "SKU1", "current_stock": 12, "stock_days": 2}]),
    )
    opportunities = detect_stock_opportunities(features)
    assert len(opportunities) == 1
    assert opportunities[0].opportunity_type is OpportunityType.STOCK_RISK


def test_ad_growth_detection() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU1", "name": "Ad Winner", "cost_price": 100}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU1", "date": "2026-06-13", "quantity": 3, "revenue": 1000}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU1",
                    "campaign_id": "C1",
                    "date": "2026-06-13",
                    "spend": 100,
                    "impressions": 1000,
                    "clicks": 50,
                    "orders": 5,
                    "revenue": 500,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(),
    )
    opportunities = detect_ad_opportunities(features)
    assert len(opportunities) == 1
    assert opportunities[0].opportunity_type is OpportunityType.AD_GROWTH


def test_ad_waste_detection() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU2", "name": "Ad Waste"}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU2", "date": "2026-06-13", "quantity": 1, "revenue": 100}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU2",
                    "campaign_id": "C2",
                    "date": "2026-06-13",
                    "spend": 200,
                    "impressions": 800,
                    "clicks": 25,
                    "orders": 1,
                    "revenue": 100,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(),
    )
    opportunities = detect_ad_opportunities(features)
    assert len(opportunities) == 1
    assert opportunities[0].opportunity_type is OpportunityType.AD_WASTE


def test_price_opportunity_detection() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame(
            [{"sku": "SKU3", "name": "Margin SKU", "price": 600, "cost_price": 100}]
        ),
        sales_df=pd.DataFrame(
            [
                {"sku": "SKU3", "date": "2026-06-10", "quantity": 4, "revenue": 2400},
                {"sku": "SKU3", "date": "2026-06-11", "quantity": 4, "revenue": 2400},
            ]
        ),
        advertising_df=pd.DataFrame(),
        forecasts_df=pd.DataFrame(),
    )
    opportunities = detect_price_opportunities(features)
    assert len(opportunities) == 1
    assert opportunities[0].opportunity_type is OpportunityType.PRICE_MARGIN


def test_ranking_opportunity_detection() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU4", "name": "Ranking SKU", "cost_price": 100}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU4", "date": "2026-06-13", "quantity": 4, "revenue": 800}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU4",
                    "campaign_id": "C4",
                    "date": "2026-06-13",
                    "spend": 50,
                    "impressions": 1000,
                    "clicks": 40,
                    "orders": 4,
                    "revenue": 800,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(),
        ranking_df=pd.DataFrame(
            [
                {"sku": "SKU4", "date": "2026-06-10", "position": 12},
                {"sku": "SKU4", "date": "2026-06-13", "position": 20},
            ]
        ),
    )
    opportunities = detect_ranking_opportunities(features)
    assert len(opportunities) == 1
    assert opportunities[0].opportunity_type is OpportunityType.RANKING_RISK


def test_confidence_scoring() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU5", "name": "Confident", "cost_price": 100}]),
        sales_df=pd.DataFrame(
            [
                {"sku": "SKU5", "date": "2026-06-12", "quantity": 2, "revenue": 400},
                {"sku": "SKU5", "date": "2026-06-13", "quantity": 3, "revenue": 600},
                {"sku": "SKU5", "date": "2026-06-14", "quantity": 4, "revenue": 800},
            ]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU5",
                    "campaign_id": "C5",
                    "date": "2026-06-13",
                    "spend": 50,
                    "clicks": 20,
                    "impressions": 500,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(
            [{"sku": "SKU5", "forecast_quantity": 10, "forecast_revenue": 2000}]
        ),
    )
    opportunity = detect_all_opportunities(features)[0]
    confidence = score_confidence(features[0], opportunity)
    assert confidence.score > 0.0
    assert confidence.level in {ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}


def test_risk_scoring() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU6", "name": "Risky", "cost_price": 400}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU6", "date": "2026-06-13", "quantity": 1, "revenue": 300}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU6",
                    "campaign_id": "C6",
                    "date": "2026-06-13",
                    "spend": 250,
                    "clicks": 20,
                    "impressions": 500,
                    "orders": 1,
                    "revenue": 100,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(),
    )
    opportunity = detect_all_opportunities(features)[0]
    recommendation = generate_recommendation(features[0], opportunity)
    risk = score_risk(features[0], opportunity, recommendation.action)
    assert risk.score > 0.0
    assert risk.level in {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


def test_recommendation_generation() -> None:
    features = build_decision_features(
        products_df=pd.DataFrame([{"sku": "SKU7", "name": "Reco", "cost_price": 100}]),
        sales_df=pd.DataFrame(
            [{"sku": "SKU7", "date": "2026-06-13", "quantity": 6, "revenue": 1200}]
        ),
        advertising_df=pd.DataFrame(
            [
                {
                    "sku": "SKU7",
                    "campaign_id": "C7",
                    "date": "2026-06-13",
                    "spend": 100,
                    "impressions": 1000,
                    "clicks": 50,
                    "orders": 5,
                    "revenue": 600,
                }
            ]
        ),
        forecasts_df=pd.DataFrame(
            [{"sku": "SKU7", "forecast_quantity": 15, "forecast_revenue": 3000}]
        ),
    )
    recommendations = generate_recommendations(features)
    assert recommendations
    assert recommendations[0].sku == "SKU7"
    assert recommendations[0].supporting_metrics["sales_revenue"] == 1200.0
