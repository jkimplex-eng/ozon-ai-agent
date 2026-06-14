"""Performance metrics calculation."""
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SKUMetrics:
    product_id: int
    offer_id: str
    sku: str
    name: str
    total_quantity: int
    total_revenue: float
    total_spend: float
    drr: float
    avg_rating: float
    total_reviews: int
    stock_days: float
    gross_profit: float
    margin: float


@dataclass
class DailyPnL:
    date: str
    revenue: float
    quantity: int
    returns: float
    advertising: float
    commission: float
    logistics: float
    partner_services: float
    fbo_services: float
    cogs: float
    gross_profit: float


def calculate_sku_metrics(
    products_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    advertising_df: pd.DataFrame,
    review_df: pd.DataFrame | None = None,
) -> list[SKUMetrics]:
    """Calculate comprehensive metrics per SKU."""
    results: list[SKUMetrics] = []

    if products_df.empty:
        return results

    for _, product in products_df.iterrows():
        pid = product.get("product_id") or product.get("id")
        offer_id = product.get("offer_id", "")
        sku = product.get("sku", "")
        name = product.get("name", "")
        cost_price = float(product.get("cost_price", 0) or 0)

        # Sales metrics
        if not sales_df.empty:
            sku_sales = sales_df[sales_df["product_id"] == pid]
        else:
            sku_sales = pd.DataFrame()
        total_quantity = 0
        if not sku_sales.empty and "quantity" in sku_sales.columns:
            total_quantity = int(sku_sales["quantity"].sum())
        total_revenue = 0.0
        if not sku_sales.empty and "revenue" in sku_sales.columns:
            total_revenue = float(sku_sales["revenue"].sum())

        # Advertising metrics
        if not advertising_df.empty:
            sku_ads = advertising_df[advertising_df["product_id"] == pid]
        else:
            sku_ads = pd.DataFrame()
        total_spend = 0.0
        if not sku_ads.empty and "spend" in sku_ads.columns:
            total_spend = float(sku_ads["spend"].sum())

        # DRR (Доля рекламных расходов)
        drr = (total_spend / total_revenue * 100) if total_revenue > 0 else 0.0

        # Review metrics
        avg_rating = 0.0
        total_reviews = 0
        if review_df is not None and not review_df.empty:
            sku_reviews = review_df[review_df["product_id"] == pid]
            if not sku_reviews.empty:
                if "rating" in sku_reviews.columns:
                    avg_rating = float(sku_reviews["rating"].mean())
                total_reviews = len(sku_reviews)

        # Stock metrics
        stock_days = 0.0
        if "stock_total" in products_df.columns:
            stock = float(product.get("stock_total", 0) or 0)
            avg_daily_sales = total_quantity / 30 if total_quantity > 0 else 0
            stock_days = stock / avg_daily_sales if avg_daily_sales > 0 else float("inf")

        # Profit metrics
        cogs = cost_price * total_quantity
        gross_profit = total_revenue - total_spend - cogs
        margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        results.append(SKUMetrics(
            product_id=int(pid) if pid else 0,
            offer_id=offer_id,
            sku=sku,
            name=name,
            total_quantity=total_quantity,
            total_revenue=round(total_revenue, 2),
            total_spend=round(total_spend, 2),
            drr=round(drr, 2),
            avg_rating=round(avg_rating, 2),
            total_reviews=total_reviews,
            stock_days=round(stock_days, 1),
            gross_profit=round(gross_profit, 2),
            margin=round(margin, 2),
        ))

    return sorted(results, key=lambda x: x.total_revenue, reverse=True)


def calculate_daily_pnl(
    sales_df: pd.DataFrame,
    finance_df: pd.DataFrame,
    advertising_df: pd.DataFrame,
    products_df: pd.DataFrame,
) -> list[DailyPnL]:
    """Calculate daily P&L breakdown."""
    results: list[DailyPnL] = []

    if sales_df.empty:
        return results

    dates = sorted(sales_df["date"].unique()) if "date" in sales_df.columns else []

    for date in dates:
        day_sales = sales_df[sales_df["date"] == date]
        has_finance_date = not finance_df.empty and "date" in finance_df.columns
        day_finance = finance_df[finance_df["date"] == date] if has_finance_date else pd.DataFrame()
        has_ads_date = not advertising_df.empty and "date" in advertising_df.columns
        day_ads = advertising_df[advertising_df["date"] == date] if has_ads_date else pd.DataFrame()

        revenue = float(day_sales["revenue"].sum()) if "revenue" in day_sales.columns else 0.0
        quantity = int(day_sales["quantity"].sum()) if "quantity" in day_sales.columns else 0

        # Finance breakdown
        returns = 0.0
        commission = 0.0
        logistics = 0.0
        partner_services = 0.0
        fbo_services = 0.0
        if not day_finance.empty:
            returns = float(day_finance.get("returns", pd.Series([0])).sum())
            commission = float(day_finance.get("ozon_commission", pd.Series([0])).sum())
            logistics = float(day_finance.get("logistics", pd.Series([0])).sum())
            partner_services = float(day_finance.get("partner_services", pd.Series([0])).sum())
            fbo_services = float(day_finance.get("fbo_services", pd.Series([0])).sum())

        advertising = 0.0
        if not day_ads.empty and "spend" in day_ads.columns:
            advertising = float(day_ads["spend"].sum())

        # COGS
        cogs = 0.0
        if "product_id" in day_sales.columns and "cost_price" in products_df.columns:
            for _, sale in day_sales.iterrows():
                pid = sale.get("product_id")
                qty = sale.get("quantity", 0)
                product = products_df[products_df["product_id"] == pid]
                if not product.empty:
                    cost = float(product.iloc[0].get("cost_price", 0) or 0)
                    cogs += cost * qty

        expenses = advertising + commission + logistics + partner_services + fbo_services + cogs
        gross_profit = revenue + returns - expenses

        results.append(DailyPnL(
            date=str(date),
            revenue=round(revenue, 2),
            quantity=quantity,
            returns=round(returns, 2),
            advertising=round(advertising, 2),
            commission=round(commission, 2),
            logistics=round(logistics, 2),
            partner_services=round(partner_services, 2),
            fbo_services=round(fbo_services, 2),
            cogs=round(cogs, 2),
            gross_profit=round(gross_profit, 2),
        ))

    return results


def calculate_trends(metrics: list[SKUMetrics], period_days: int = 30) -> dict[str, Any]:
    """Calculate trends and growth rates."""
    if not metrics:
        return {}

    total_revenue = sum(m.total_revenue for m in metrics)
    total_quantity = sum(m.total_quantity for m in metrics)
    total_spend = sum(m.total_spend for m in metrics)
    avg_drr = sum(m.drr for m in metrics) / len(metrics) if metrics else 0
    avg_margin = sum(m.margin for m in metrics) / len(metrics) if metrics else 0

    profitable_skus = [m for m in metrics if m.gross_profit > 0]
    unprofitable_skus = [m for m in metrics if m.gross_profit <= 0]

    return {
        "total_revenue": round(total_revenue, 2),
        "total_quantity": total_quantity,
        "total_spend": round(total_spend, 2),
        "avg_drr": round(avg_drr, 2),
        "avg_margin": round(avg_margin, 2),
        "total_skus": len(metrics),
        "profitable_skus": len(profitable_skus),
        "unprofitable_skus": len(unprofitable_skus),
        "top_revenue_sku": metrics[0].sku if metrics else "",
        "top_profit_sku": max(metrics, key=lambda x: x.gross_profit).sku if metrics else "",
    }
