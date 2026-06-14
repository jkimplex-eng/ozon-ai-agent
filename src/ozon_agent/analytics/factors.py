"""Factor analysis - correlations between marketplace factors and metrics."""
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class FactorCorrelation:
    factor: str
    metric: str
    correlation: float
    p_value: float
    significance: str  # strong, moderate, weak, none
    direction: str  # positive, negative


@dataclass
class FactorImportance:
    factor: str
    importance: float
    rank: int


def calculate_correlations(
    df: pd.DataFrame, factors: list[str], metrics: list[str]
) -> list[FactorCorrelation]:
    """Calculate Pearson correlations between factors and metrics."""
    results = []

    for factor in factors:
        if factor not in df.columns:
            continue
        for metric in metrics:
            if metric not in df.columns:
                continue

            valid = df[[factor, metric]].dropna()
            if len(valid) < 10:
                continue

            corr = valid[factor].corr(valid[metric])
            if np.isnan(corr):
                continue

            # Simple significance based on correlation strength
            abs_corr = abs(corr)
            if abs_corr >= 0.7:
                significance = "strong"
            elif abs_corr >= 0.4:
                significance = "moderate"
            elif abs_corr >= 0.2:
                significance = "weak"
            else:
                significance = "none"

            direction = "positive" if corr > 0 else "negative"

            results.append(FactorCorrelation(
                factor=factor,
                metric=metric,
                correlation=round(corr, 4),
                p_value=0.0,  # simplified
                significance=significance,
                direction=direction,
            ))

    return sorted(results, key=lambda x: abs(x.correlation), reverse=True)


def calculate_feature_importance(
    df: pd.DataFrame,
    features: list[str],
    target: str,
) -> list[FactorImportance]:
    """Calculate feature importance using correlation with target."""
    results: list[FactorImportance] = []

    if target not in df.columns:
        return results

    for feature in features:
        if feature not in df.columns:
            continue

        valid = df[[feature, target]].dropna()
        if len(valid) < 10:
            continue

        corr = abs(valid[feature].corr(valid[target]))
        if np.isnan(corr):
            continue

        results.append(FactorImportance(
            factor=feature,
            importance=round(corr, 4),
            rank=0,
        ))

    results.sort(key=lambda x: x.importance, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1

    return results


def analyze_price_impact(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze how price changes affect sales and revenue."""
    if "price" not in df.columns or "quantity" not in df.columns:
        return {}

    valid = df[["price", "quantity", "revenue"]].dropna()
    if len(valid) < 5:
        return {}

    price_corr_sales = valid["price"].corr(valid["quantity"])
    price_corr_revenue = valid["price"].corr(valid["revenue"])

    # Price elasticity estimate
    avg_price = valid["price"].mean()
    avg_qty = valid["quantity"].mean()
    if avg_price > 0 and avg_qty > 0:
        elasticity = price_corr_sales * (avg_qty / avg_price)
    else:
        elasticity = 0.0

    return {
        "price_sales_correlation": round(price_corr_sales, 4),
        "price_revenue_correlation": round(price_corr_revenue, 4),
        "estimated_elasticity": round(elasticity, 4),
        "avg_price": round(avg_price, 2),
        "avg_quantity": round(avg_qty, 2),
    }


def analyze_ad_efficiency(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze advertising efficiency metrics."""
    required = ["spend", "revenue", "clicks", "impressions"]
    if not all(col in df.columns for col in required):
        return {}

    valid = df[required].dropna()
    if len(valid) < 5:
        return {}

    total_spend = valid["spend"].sum()
    total_revenue = valid["revenue"].sum()
    total_clicks = valid["clicks"].sum()
    total_impressions = valid["impressions"].sum()

    return {
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "drr": round(total_spend / total_revenue * 100, 2) if total_revenue > 0 else 0,
        "ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
        "cpc": round(total_spend / total_clicks, 2) if total_clicks > 0 else 0,
        "roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
    }


def analyze_stock_health(df: pd.DataFrame, forecast_days: int = 7) -> dict[str, Any]:
    """Analyze stock health and predict stockout risk."""
    if "stock_total" not in df.columns or "quantity" not in df.columns:
        return {}

    valid = df[["stock_total", "quantity"]].dropna()
    if len(valid) < 7:
        return {}

    current_stock = valid["stock_total"].iloc[-1]
    avg_daily_sales = valid["quantity"].mean()
    days_of_stock = current_stock / avg_daily_sales if avg_daily_sales > 0 else float("inf")

    return {
        "current_stock": int(current_stock),
        "avg_daily_sales": round(avg_daily_sales, 2),
        "days_of_stock": round(days_of_stock, 1),
        "stockout_risk": "high" if days_of_stock < forecast_days else "low",
        "recommended_restock": max(0, int(avg_daily_sales * 30 - current_stock)),
    }


def generate_factor_report(df: pd.DataFrame) -> dict[str, Any]:
    """Generate comprehensive factor analysis report."""
    factors = [
        "price", "ctr", "conversion", "rating", "review_count",
        "delivery_days", "stock_total", "spend", " impressions",
    ]
    metrics = ["quantity", "revenue", "position"]

    # Filter to available columns
    available_factors = [f for f in factors if f in df.columns]
    available_metrics = [m for m in metrics if m in df.columns]

    correlations = calculate_correlations(df, available_factors, available_metrics)

    # Top factors for sales
    sales_importance = []
    if "quantity" in df.columns:
        sales_importance = calculate_feature_importance(df, available_factors, "quantity")

    return {
        "correlations": [
            {
                "factor": c.factor,
                "metric": c.metric,
                "correlation": c.correlation,
                "significance": c.significance,
                "direction": c.direction,
            }
            for c in correlations[:20]
        ],
        "top_sales_factors": [
            {"factor": f.factor, "importance": f.importance, "rank": f.rank}
            for f in sales_importance[:10]
        ],
        "price_impact": analyze_price_impact(df),
        "ad_efficiency": analyze_ad_efficiency(df),
        "stock_health": analyze_stock_health(df),
    }
