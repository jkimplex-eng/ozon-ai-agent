"""Stock shortage prediction."""
from typing import Any

import pandas as pd

from .prophet_forecaster import ProphetForecaster


class StockPredictor:
    def __init__(self):
        self._sales_fitter = ProphetForecaster()
        self._current_stock = 0
        self._fitted = False

    def fit(
        self, df: pd.DataFrame, stock_col: str = "stock_total", sales_col: str = "quantity"
    ) -> None:
        self._current_stock = float(df[stock_col].iloc[-1])
        self._sales_fitter.fit(df, target=sales_col)
        self._fitted = True

    def predict(self, days: int = 14) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")

        forecast = self._sales_fitter.predict(periods=days)
        predicted_sales = forecast.point

        remaining = self._current_stock
        days_until_stockout = days

        for i, daily_sales in enumerate(predicted_sales):
            remaining -= daily_sales
            if remaining <= 0:
                days_until_stockout = i + 1
                break

        if days_until_stockout <= 3:
            risk_level = "high"
        elif days_until_stockout <= 7:
            risk_level = "medium"
        else:
            risk_level = "low"

        avg_daily = sum(predicted_sales) / len(predicted_sales) if predicted_sales else 0
        recommended = max(0, int(avg_daily * 30 - self._current_stock))

        return {
            "current_stock": int(self._current_stock),
            "predicted_daily_sales": [round(s, 1) for s in predicted_sales],
            "days_until_stockout": days_until_stockout,
            "risk_level": risk_level,
            "recommended_restock": recommended,
        }
