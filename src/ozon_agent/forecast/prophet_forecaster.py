"""Prophet-based time-series forecaster."""
import logging

import pandas as pd
from prophet import Prophet

from .base import BaseForecaster, ForecastResult

logger = logging.getLogger(__name__)


class ProphetForecaster(BaseForecaster):
    def __init__(self, **prophet_kwargs):
        self._model = None
        self._target = ""
        self._kwargs = prophet_kwargs

    def fit(self, df: pd.DataFrame, target: str, date_col: str = "date") -> None:
        self._target = target
        prophet_df = df[[date_col, target]].copy()
        prophet_df.columns = ["ds", "y"]
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
        prophet_df = prophet_df.dropna()

        self._model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            **self._kwargs,
        )
        self._model.fit(prophet_df)
        logger.info("Prophet model fitted on %d rows", len(prophet_df))

    def predict(self, periods: int) -> ForecastResult:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        future = self._model.make_future_dataframe(periods=periods)
        forecast = self._model.predict(future)

        tail = forecast.tail(periods)
        dates = [d.strftime("%Y-%m-%d") for d in tail["ds"]]
        point = tail["yhat"].clip(lower=0).tolist()
        lower = tail["yhat_lower"].clip(lower=0).tolist()
        upper = tail["yhat_upper"].clip(lower=0).tolist()

        return ForecastResult(
            dates=dates,
            lower=lower,
            point=point,
            upper=upper,
            model="prophet",
        )
