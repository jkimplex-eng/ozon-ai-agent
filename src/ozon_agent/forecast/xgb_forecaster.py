"""XGBoost multi-variate forecaster."""
import logging

import pandas as pd
import xgboost as xgb

from .base import BaseForecaster, ForecastResult

logger = logging.getLogger(__name__)


class XGBForecaster(BaseForecaster):
    def __init__(self, **xgb_kwargs):
        self._model = None
        self._target = ""
        self._features: list[str] = []
        self._kwargs = xgb_kwargs

    def fit(
        self, df: pd.DataFrame, target: str,
        features: list[str] | None = None, date_col: str = "date",
    ) -> None:
        self._target = target
        self._features = features or []

        train_df = df.copy()
        if date_col in train_df.columns:
            train_df["_dayofweek"] = pd.to_datetime(train_df[date_col]).dt.dayofweek
            train_df["_day"] = pd.to_datetime(train_df[date_col]).dt.day
            if "_dayofweek" not in self._features:
                self._features.append("_dayofweek")
            if "_day" not in self._features:
                self._features.append("_day")

        x = train_df[self._features].fillna(0)
        y = train_df[target].fillna(0)

        params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "objective": "reg:squarederror",
            **self._kwargs,
        }
        self._model = xgb.XGBRegressor(**params)
        self._model.fit(x, y)
        logger.info("XGBoost model fitted on %d rows, %d features", len(x), len(self._features))

    def predict(self, periods: int, future_df: pd.DataFrame | None = None) -> ForecastResult:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if future_df is None:
            future_df = pd.DataFrame()

        if "_dayofweek" not in future_df.columns and "date" in future_df.columns:
            future_df["_dayofweek"] = pd.to_datetime(future_df["date"]).dt.dayofweek
            future_df["_day"] = pd.to_datetime(future_df["date"]).dt.day

        x = future_df[self._features].fillna(0) if self._features else future_df.fillna(0)
        preds = self._model.predict(x)
        preds = [max(0, float(p)) for p in preds]

        dates = []
        if "date" in future_df.columns:
            dates = [str(d)[:10] for d in future_df["date"].tolist()]
        else:
            dates = [f"day_{i+1}" for i in range(len(preds))]

        return ForecastResult(
            dates=dates,
            lower=[p * 0.8 for p in preds],
            point=preds,
            upper=[p * 1.2 for p in preds],
            model="xgboost",
        )
