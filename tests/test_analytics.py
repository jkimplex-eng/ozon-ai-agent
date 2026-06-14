"""Tests for analytics module."""
import pandas as pd

from ozon_agent.analytics.diagnostics import (
    check_date_continuity,
    check_duplicates,
    check_missing_data,
    check_negative_values,
    check_outliers,
    run_full_diagnostics,
)
from ozon_agent.analytics.factors import (
    analyze_ad_efficiency,
    analyze_price_impact,
    analyze_stock_health,
    calculate_correlations,
    calculate_feature_importance,
)
from ozon_agent.analytics.metrics import (
    calculate_sku_metrics,
    calculate_trends,
)
from ozon_agent.analytics.summary import format_summary_text, generate_analytics_summary


def test_calculate_correlations():
    """Test correlation calculation."""
    df = pd.DataFrame({
        "price": list(range(100, 110)),
        "quantity": list(range(50, 40, -1)),
        "revenue": list(range(5000, 6000, 100)),
    })

    results = calculate_correlations(df, ["price"], ["quantity", "revenue"])
    assert len(results) == 2
    assert results[0].factor == "price"
    assert results[0].significance in ["strong", "moderate", "weak", "none"]


def test_calculate_feature_importance():
    """Test feature importance calculation."""
    df = pd.DataFrame({
        "price": list(range(100, 110)),
        "quantity": list(range(50, 40, -1)),
        "rating": [4.5, 4.4, 4.3, 4.2, 4.1, 4.0, 3.9, 3.8, 3.7, 3.6],
    })

    results = calculate_feature_importance(df, ["price", "rating"], "quantity")
    assert len(results) == 2
    assert results[0].rank == 1


def test_analyze_price_impact():
    """Test price impact analysis."""
    df = pd.DataFrame({
        "price": [100, 200, 300, 400, 500],
        "quantity": [50, 40, 30, 20, 10],
        "revenue": [5000, 8000, 9000, 8000, 5000],
    })

    result = analyze_price_impact(df)
    assert "price_sales_correlation" in result
    assert "estimated_elasticity" in result


def test_analyze_ad_efficiency():
    """Test advertising efficiency analysis."""
    df = pd.DataFrame({
        "spend": [1000, 1200, 1400, 1600, 1800],
        "revenue": [5000, 6000, 7000, 8000, 9000],
        "clicks": [100, 120, 140, 160, 180],
        "impressions": [10000, 12000, 14000, 16000, 18000],
    })

    result = analyze_ad_efficiency(df)
    assert result["total_spend"] == 7000
    assert result["total_revenue"] == 35000
    assert result["drr"] > 0
    assert result["roas"] > 0


def test_analyze_stock_health():
    """Test stock health analysis."""
    df = pd.DataFrame({
        "stock_total": [100, 90, 80, 70, 60, 50, 40],
        "quantity": [10, 10, 10, 10, 10, 10, 10],
    })

    result = analyze_stock_health(df)
    assert result["current_stock"] == 40
    assert result["avg_daily_sales"] == 10.0
    assert result["days_of_stock"] == 4.0
    assert result["stockout_risk"] == "high"


def test_check_missing_data():
    """Test missing data check."""
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", None],
        "quantity": [10, None, 30],
    })

    results = check_missing_data(df, ["date", "quantity"])
    assert len(results) == 2
    assert any(r.status == "warn" for r in results)


def test_check_duplicates():
    """Test duplicate check."""
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "product_id": [1, 1, 2, 3, 4],
    })

    results = check_duplicates(df, ["date", "product_id"])
    assert len(results) == 1
    assert results[0].status in ["warn", "fail"]


def test_check_date_continuity():
    """Test date continuity check."""
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-05"],
    })

    results = check_date_continuity(df, "date")
    assert len(results) == 1
    assert results[0].status == "warn"


def test_check_outliers():
    """Test outlier check."""
    df = pd.DataFrame({
        "revenue": [100, 110, 120, 130, 140, 150, 160, 170, 180, 10000],
    })

    results = check_outliers(df, ["revenue"])
    assert len(results) == 1


def test_check_negative_values():
    """Test negative values check."""
    df = pd.DataFrame({
        "quantity": [10, -5, 30],
    })

    results = check_negative_values(df, ["quantity"])
    assert len(results) == 1
    assert results[0].status == "warn"


def test_run_full_diagnostics():
    """Test full diagnostics run."""
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "product_id": [1, 1, 1],
        "quantity": [10, 20, 30],
        "revenue": [1000, 2000, 3000],
    })

    result = run_full_diagnostics(df)
    assert result["total_checks"] > 0
    assert result["passed"] > 0


def test_calculate_sku_metrics():
    """Test SKU metrics calculation."""
    products = pd.DataFrame({
        "product_id": [1, 2],
        "offer_id": ["O1", "O2"],
        "sku": ["SKU1", "SKU2"],
        "name": ["Product 1", "Product 2"],
        "cost_price": [100, 200],
    })

    sales = pd.DataFrame({
        "product_id": [1, 1, 2],
        "date": ["2026-01-01", "2026-01-02", "2026-01-01"],
        "quantity": [10, 20, 15],
        "revenue": [1000, 2000, 1500],
    })

    advertising = pd.DataFrame({
        "product_id": [1, 2],
        "date": ["2026-01-01", "2026-01-01"],
        "spend": [100, 200],
    })

    metrics = calculate_sku_metrics(products, sales, advertising)
    assert len(metrics) == 2
    assert metrics[0].total_revenue > 0


def test_calculate_trends():
    """Test trends calculation."""
    from ozon_agent.analytics.metrics import SKUMetrics

    metrics = [
        SKUMetrics(1, "O1", "SKU1", "P1", 30, 3000, 300, 10.0, 4.5, 50, 30, 1500, 50.0),
        SKUMetrics(2, "O2", "SKU2", "P2", 15, 1500, 200, 13.3, 4.0, 30, 60, 600, 40.0),
    ]

    trends = calculate_trends(metrics)
    assert trends["total_revenue"] == 4500
    assert trends["profitable_skus"] == 2


def test_generate_analytics_summary():
    """Test summary generation."""
    products = pd.DataFrame({
        "product_id": [1],
        "offer_id": ["O1"],
        "sku": ["SKU1"],
        "name": ["Product 1"],
    })

    sales = pd.DataFrame({
        "product_id": [1],
        "date": ["2026-01-01"],
        "quantity": [10],
        "revenue": [1000],
    })

    advertising = pd.DataFrame(columns=["product_id", "date", "spend"])
    finance = pd.DataFrame(columns=["date", "sales", "returns"])

    summary = generate_analytics_summary(products, sales, advertising, finance)
    assert "summary" in summary
    assert "sku_metrics" in summary
    assert "diagnostics" in summary


def test_format_summary_text():
    """Test summary text formatting."""
    summary = {
        "generated_at": "2026-01-01T00:00:00",
        "summary": {
            "total_revenue": 10000,
            "total_quantity": 100,
            "total_spend": 1000,
            "avg_drr": 10.0,
            "avg_margin": 30.0,
            "total_skus": 5,
            "profitable_skus": 4,
        },
        "sku_metrics": [],
        "diagnostics": {"passed": 10, "warnings": 2, "failed": 0},
    }

    text = format_summary_text(summary)
    assert "OZON AI AGENT" in text
    assert "10,000" in text
