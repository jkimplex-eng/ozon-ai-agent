"""ROI and profit forecasting."""
from typing import Any

import pandas as pd

from .prophet_forecaster import ProphetForecaster


class ROICalculator:
    def __init__(self, cost_per_unit: float = 0):
        self._revenue_fitter = ProphetForecaster()
        self._spend_fitter = ProphetForecaster()
        self._cost_per_unit = cost_per_unit
        self._avg_daily_quantity = 0.0
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> None:
        self._revenue_fitter.fit(df, target="revenue")
        self._spend_fitter.fit(df, target="spend")
        self._avg_daily_quantity = float(df["quantity"].mean()) if "quantity" in df.columns else 0
        self._fitted = True

    def forecast_roi(self, days: int = 7) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")

        rev_forecast = self._revenue_fitter.predict(periods=days)
        spend_forecast = self._spend_fitter.predict(periods=days)

        daily_roi = []
        for rev, spend in zip(rev_forecast.point, spend_forecast.point):
            roi = ((rev - spend) / spend * 100) if spend > 0 else 0
            daily_roi.append(round(roi, 2))

        total_revenue = sum(rev_forecast.point)
        total_spend = sum(spend_forecast.point)
        total_roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0

        return {
            "dates": rev_forecast.dates,
            "daily_roi": daily_roi,
            "total_roi": round(total_roi, 2),
            "forecasted_revenue": round(total_revenue, 2),
            "forecasted_spend": round(total_spend, 2),
            "forecasted_profit": round(total_revenue - total_spend, 2),
        }

    def forecast_profit(self, days: int = 7, ad_budget: float = 0) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")

        rev_forecast = self._revenue_fitter.predict(periods=days)

        daily_profit = []
        for rev in rev_forecast.point:
            cogs = self._avg_daily_quantity * self._cost_per_unit
            profit = rev - ad_budget - cogs
            daily_profit.append(round(profit, 2))

        return {
            "dates": rev_forecast.dates,
            "daily_profit": daily_profit,
            "total_profit": round(sum(daily_profit), 2),
        }
