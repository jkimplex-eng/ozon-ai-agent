# Phase 3: Forecasting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build forecasting models for sales, advertising spend, stock shortages, profit, and ROI using Prophet and gradient boosting.

**Architecture:** Modular forecasting with Prophet for time-series univariate forecasts and XGBoost/LightGBM for multi-variate predictions. Each model type is a separate class with a common interface. Models are trained on historical data from the data warehouse and produce confidence intervals.

**Tech Stack:** Prophet, XGBoost, LightGBM, scikit-learn, pandas, numpy, joblib (for model persistence)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/ozon_agent/forecast/base.py` | Abstract base class for all forecasters |
| `src/ozon_agent/forecast/prophet_forecaster.py` | Prophet-based time-series forecasts |
| `src/ozon_agent/forecast/xgb_forecaster.py` | XGBoost multi-variate forecasts |
| `src/ozon_agent/forecast/lgbm_forecaster.py` | LightGBM multi-variate forecasts |
| `src/ozon_agent/forecast/stock_predictor.py` | Stock shortage prediction |
| `src/ozon_agent/forecast/roi_calculator.py` | ROI and profit forecasting |
| `src/ozon_agent/forecast/ensemble.py` | Model selection and ensemble |
| `src/ozon_agent/forecast/evaluate.py` | Model evaluation metrics |
| `src/ozon_agent/cli.py` | Add forecast CLI commands |
| `tests/test_forecast.py` | Tests for all forecast modules |

---

### Task 1: Base Forecaster Interface

**Covers:** Common forecast interface for all models

**Files:**
- Create: `src/ozon_agent/forecast/__init__.py`
- Create: `src/ozon_agent/forecast/base.py`
- Create: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_forecast.py
"""Tests for forecast module."""
import pandas as pd
import numpy as np

from ozon_agent.forecast.base import BaseForecaster, ForecastResult


def test_forecast_result_dataclass():
    """Test ForecastResult holds predictions correctly."""
    result = ForecastResult(
        dates=["2026-06-14", "2026-06-15"],
        lower=[10.0, 12.0],
        point=[15.0, 18.0],
        upper=[20.0, 24.0],
        model="test",
    )
    assert len(result.dates) == 2
    assert result.point[0] == 15.0
    assert result.model == "test"


def test_base_forecaster_is_abstract():
    """Test BaseForecaster cannot be instantiated directly."""
    import pytest
    with pytest.raises(TypeError):
        BaseForecaster()


def test_base_forecaster_requires_fit_predict():
    """Test subclass must implement fit and predict."""
    class IncompleteForecaster(BaseForecaster):
        pass

    with pytest.raises(TypeError):
        IncompleteForecaster()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ozon_agent.forecast'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/ozon_agent/forecast/__init__.py
"""Forecasting module for Ozon AI Agent."""

# src/ozon_agent/forecast/base.py
"""Abstract base class for forecasters."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class ForecastResult:
    dates: list[str]
    lower: list[float]
    point: list[float]
    upper: list[float]
    model: str


class BaseForecaster(ABC):
    @abstractmethod
    def fit(self, df: pd.DataFrame, target: str, date_col: str = "date") -> None:
        ...

    @abstractmethod
    def predict(self, periods: int) -> ForecastResult:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/__init__.py src/ozon_agent/forecast/base.py tests/test_forecast.py
git commit -m "feat: add base forecaster interface and ForecastResult"
```

---

### Task 2: Prophet Forecaster

**Covers:** Time-series univariate forecasting for sales

**Files:**
- Create: `src/ozon_agent/forecast/prophet_forecaster.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.prophet_forecaster import ProphetForecaster


def test_prophet_forecaster_fit_predict():
    """Test Prophet forecaster produces valid forecasts."""
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "quantity": np.random.poisson(20, 60),
    })

    fitter = ProphetForecaster()
    fitter.fit(df, target="quantity")
    result = fitter.predict(periods=7)

    assert len(result.dates) == 7
    assert len(result.point) == 7
    assert result.model == "prophet"
    assert all(p >= 0 for p in result.point)


def test_prophet_forecaster_short_data():
    """Test Prophet handles short data gracefully."""
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5, freq="D"),
        "quantity": [10, 12, 14, 13, 15],
    })

    fitter = ProphetForecaster()
    fitter.fit(df, target="quantity")
    result = fitter.predict(periods=3)

    assert len(result.dates) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_prophet_forecaster_fit_predict -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/prophet_forecaster.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/prophet_forecaster.py tests/test_forecast.py
git commit -m "feat: add Prophet time-series forecaster"
```

---

### Task 3: XGBoost Forecaster

**Covers:** Multi-variate forecasting with exogenous features

**Files:**
- Create: `src/ozon_agent/forecast/xgb_forecaster.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.xgb_forecaster import XGBForecaster


def test_xgb_forecaster_fit_predict():
    """Test XGBoost forecaster with exogenous features."""
    n = 60
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "quantity": np.random.poisson(20, n),
        "price": np.random.uniform(100, 500, n),
        "spend": np.random.uniform(50, 500, n),
    })

    fitter = XGBForecaster()
    fitter.fit(df, target="quantity", features=["price", "spend"])
    result = fitter.predict(periods=7, future_df=pd.DataFrame({
        "date": pd.date_range("2026-03-01", periods=7, freq="D"),
        "price": [200] * 7,
        "spend": [100] * 7,
    }))

    assert len(result.dates) == 7
    assert len(result.point) == 7
    assert result.model == "xgboost"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_xgb_forecaster_fit_predict -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/xgb_forecaster.py
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

        X = train_df[self._features].fillna(0)
        y = train_df[target].fillna(0)

        params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "objective": "reg:squarederror",
            **self._kwargs,
        }
        self._model = xgb.XGBRegressor(**params)
        self._model.fit(X, y)
        logger.info("XGBoost model fitted on %d rows, %d features", len(X), len(self._features))

    def predict(self, periods: int, future_df: pd.DataFrame | None = None) -> ForecastResult:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if future_df is None:
            future_df = pd.DataFrame()

        if "_dayofweek" not in future_df.columns and "date" in future_df.columns:
            future_df["_dayofweek"] = pd.to_datetime(future_df["date"]).dt.dayofweek
            future_df["_day"] = pd.to_datetime(future_df["date"]).dt.day

        X = future_df[self._features].fillna(0) if self._features else future_df.fillna(0)
        preds = self._model.predict(X)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/xgb_forecaster.py tests/test_forecast.py
git commit -m "feat: add XGBoost multi-variate forecaster"
```

---

### Task 4: LightGBM Forecaster

**Covers:** Alternative gradient boosting forecaster

**Files:**
- Create: `src/ozon_agent/forecast/lgbm_forecaster.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.lgbm_forecaster import LGBMForecaster


def test_lgbm_forecaster_fit_predict():
    """Test LightGBM forecaster."""
    n = 60
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=n, freq="D"),
        "quantity": np.random.poisson(20, n),
        "price": np.random.uniform(100, 500, n),
    })

    fitter = LGBMForecaster()
    fitter.fit(df, target="quantity", features=["price"])
    result = fitter.predict(periods=5, future_df=pd.DataFrame({
        "date": pd.date_range("2026-03-01", periods=5, freq="D"),
        "price": [250] * 5,
    }))

    assert len(result.dates) == 5
    assert result.model == "lightgbm"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_lgbm_forecaster_fit_predict -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/lgbm_forecaster.py
"""LightGBM multi-variate forecaster."""
import logging

import pandas as pd
import lightgbm as lgb

from .base import BaseForecaster, ForecastResult

logger = logging.getLogger(__name__)


class LGBMForecaster(BaseForecaster):
    def __init__(self, **lgbm_kwargs):
        self._model = None
        self._target = ""
        self._features: list[str] = []
        self._kwargs = lgbm_kwargs

    def fit(
        self, df: pd.DataFrame, target: str,
        features: list[str] | None = None, date_col: str = "date",
    ) -> None:
        self._target = target
        self._features = features or []

        train_df = df.copy()
        if date_col in train_df.columns:
            train_df["_dayofweek"] = pd.to_datetime(train_df[date_col]).dt.dayofweek
            if "_dayofweek" not in self._features:
                self._features.append("_dayofweek")

        X = train_df[self._features].fillna(0)
        y = train_df[target].fillna(0)

        params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "objective": "regression",
            "verbose": -1,
            **self._kwargs,
        }
        self._model = lgb.LGBMRegressor(**params)
        self._model.fit(X, y)
        logger.info("LightGBM model fitted on %d rows", len(X))

    def predict(self, periods: int, future_df: pd.DataFrame | None = None) -> ForecastResult:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if future_df is None:
            future_df = pd.DataFrame()

        if "_dayofweek" not in future_df.columns and "date" in future_df.columns:
            future_df["_dayofweek"] = pd.to_datetime(future_df["date"]).dt.dayofweek

        X = future_df[self._features].fillna(0) if self._features else future_df.fillna(0)
        preds = self._model.predict(X)
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
            model="lightgbm",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/lgbm_forecaster.py tests/test_forecast.py
git commit -m "feat: add LightGBM multi-variate forecaster"
```

---

### Task 5: Stock Predictor

**Covers:** Stock shortage prediction and restock recommendations

**Files:**
- Create: `src/ozon_agent/forecast/stock_predictor.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.stock_predictor import StockPredictor


def test_stock_predictor_predicts_stockout():
    """Test stock predictor identifies stockout risk."""
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=30, freq="D"),
        "stock_total": list(range(100, 70, -1)),
        "quantity": [1] * 30,
    })

    predictor = StockPredictor()
    predictor.fit(df)
    result = predictor.predict(days=14)

    assert result["days_until_stockout"] <= 30
    assert result["risk_level"] in ["high", "medium", "low"]
    assert "recommended_restock" in result


def test_stock_predictor_healthy_stock():
    """Test stock predictor with healthy stock levels."""
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=30, freq="D"),
        "stock_total": [500] * 30,
        "quantity": [5] * 30,
    })

    predictor = StockPredictor()
    predictor.fit(df)
    result = predictor.predict(days=14)

    assert result["risk_level"] == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_stock_predictor_predicts_stockout -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/stock_predictor.py
"""Stock shortage prediction."""
from typing import Any

import pandas as pd

from .prophet_forecaster import ProphetForecaster


class StockPredictor:
    def __init__(self):
        self._sales_fitter = ProphetForecaster()
        self._current_stock = 0
        self._fitted = False

    def fit(self, df: pd.DataFrame, stock_col: str = "stock_total", sales_col: str = "quantity") -> None:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/stock_predictor.py tests/test_forecast.py
git commit -m "feat: add stock shortage predictor"
```

---

### Task 6: ROI Calculator

**Covers:** Advertising ROI and profit forecasting

**Files:**
- Create: `src/ozon_agent/forecast/roi_calculator.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.roi_calculator import ROICalculator


def test_roi_calculator_forecasts_roi():
    """Test ROI calculator produces valid forecasts."""
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=30, freq="D"),
        "revenue": np.random.uniform(5000, 15000, 30),
        "spend": np.random.uniform(500, 2000, 30),
        "quantity": np.random.poisson(20, 30),
    })

    calculator = ROICalculator()
    calculator.fit(df)
    result = calculator.forecast_roi(days=7)

    assert "daily_roi" in result
    assert "total_roi" in result
    assert "forecasted_profit" in result
    assert len(result["daily_roi"]) == 7


def test_roi_calculator_forecasts_profit():
    """Test profit forecast with cost data."""
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=30, freq="D"),
        "revenue": [10000] * 30,
        "spend": [1000] * 30,
        "quantity": [20] * 30,
    })

    calculator = ROICalculator(cost_per_unit=100)
    calculator.fit(df)
    result = calculator.forecast_profit(days=7, ad_budget=1500)

    assert "daily_profit" in result
    assert "total_profit" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_roi_calculator_forecasts_roi -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/roi_calculator.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/roi_calculator.py tests/test_forecast.py
git commit -m "feat: add ROI and profit forecaster"
```

---

### Task 7: Model Evaluation

**Covers:** Model quality metrics and comparison

**Files:**
- Create: `src/ozon_agent/forecast/evaluate.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from ozon_agent.forecast.evaluate import evaluate_forecast, compare_models


def test_evaluate_forecast():
    """Test forecast evaluation metrics."""
    actual = [100, 110, 120, 115, 130]
    predicted = [105, 108, 118, 120, 125]

    metrics = evaluate_forecast(actual, predicted)

    assert "mae" in metrics
    assert "rmse" in metrics
    assert "mape" in metrics
    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0


def test_compare_models():
    """Test model comparison."""
    forecasts = {
        "prophet": [100, 110, 120],
        "xgboost": [105, 108, 118],
    }
    actual = [102, 112, 119]

    comparison = compare_models(forecasts, actual)

    assert "prophet" in comparison
    assert "xgboost" in comparison
    assert "best_model" in comparison
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_evaluate_forecast -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write implementation**

```python
# src/ozon_agent/forecast/evaluate.py
"""Model evaluation and comparison."""
from typing import Any

import numpy as np


def evaluate_forecast(actual: list[float], predicted: list[float]) -> dict[str, float]:
    actual_arr = np.array(actual, dtype=float)
    predicted_arr = np.array(predicted, dtype=float)

    mae = float(np.mean(np.abs(actual_arr - predicted_arr)))
    rmse = float(np.sqrt(np.mean((actual_arr - predicted_arr) ** 2)))

    nonzero = actual_arr != 0
    if nonzero.any():
        mape = float(np.mean(np.abs((actual_arr[nonzero] - predicted_arr[nonzero]) / actual_arr[nonzero])) * 100)
    else:
        mape = 0.0

    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 4)}


def compare_models(
    forecasts: dict[str, list[float]], actual: list[float]
) -> dict[str, Any]:
    results = {}
    for name, pred in forecasts.items():
        results[name] = evaluate_forecast(actual, pred)

    best_model = min(results, key=lambda k: results[k]["rmse"])
    results["best_model"] = best_model

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/forecast/evaluate.py tests/test_forecast.py
git commit -m "feat: add model evaluation and comparison"
```

---

### Task 8: CLI Integration

**Covers:** CLI commands for forecasting

**Files:**
- Modify: `src/ozon_agent/cli.py`
- Modify: `tests/test_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_forecast.py

from click.testing import CliRunner
from ozon_agent.cli import main


def test_forecast_cli_help():
    """Test forecast CLI command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["forecast", "--help"])
    assert result.exit_code == 0
    assert "Forecast" in result.output or "forecast" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forecast.py::test_forecast_cli_help -v`
Expected: FAIL (command not found)

- [ ] **Step 3: Write implementation**

```python
# Add to src/ozon_agent/cli.py (at end, before if __name__)

@main.command()
@click.option("--target", "-t", default="quantity", help="Target column to forecast")
@click.option("--periods", "-p", default=7, help="Number of days to forecast")
@click.option("--model", "-m", default="prophet", type=click.Choice(["prophet", "xgboost", "lightgbm"]))
def forecast(target: str, periods: int, model: str) -> None:
    """Forecast sales and metrics."""
    import pandas as pd

    from .db.connection import execute_query
    from .forecast.prophet_forecaster import ProphetForecaster
    from .forecast.xgb_forecaster import XGBForecaster
    from .forecast.lgbm_forecaster import LGBMForecaster

    console.print(f"[bold blue]Loading data for {target}...[/]")
    sales = pd.DataFrame(execute_query(
        "SELECT date, SUM(quantity) as quantity, SUM(revenue) as revenue FROM sales GROUP BY date ORDER BY date"
    ))

    if sales.empty:
        console.print("[red]No sales data found. Run sync first.[/]")
        return

    console.print(f"  Loaded {len(sales)} days of data")

    if model == "prophet":
        fitter = ProphetForecaster()
        fitter.fit(sales, target=target)
    elif model == "xgboost":
        fitter = XGBForecaster()
        features = [c for c in ["revenue", "spend"] if c in sales.columns]
        fitter.fit(sales, target=target, features=features)
    else:
        fitter = LGBMForecaster()
        features = [c for c in ["revenue", "spend"] if c in sales.columns]
        fitter.fit(sales, target=target, features=features)

    result = fitter.predict(periods=periods)

    console.print(f"\n[bold green]Forecast ({model}, {periods} days):[/]")
    for date, val in zip(result.dates, result.point):
        console.print(f"  {date}: {val:.1f}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forecast.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ozon_agent/cli.py tests/test_forecast.py
git commit -m "feat: add forecast CLI command"
```

---

### Task 9: Final Verification

**Covers:** All code quality checks

**Files:** None (verification only)

- [ ] **Step 1: Run linter**

Run: `python -m ruff check src/ tests/`
Expected: All checks passed

- [ ] **Step 2: Run type checker**

Run: `python -m mypy src/`
Expected: Success

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: Phase 3 forecasting complete - Prophet, XGBoost, LightGBM, stock predictor, ROI calculator"
```
