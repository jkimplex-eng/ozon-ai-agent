"""Tests for forecast module."""
import numpy as np
import pandas as pd
import pytest

from ozon_agent.forecast.base import BaseForecaster, ForecastResult
from ozon_agent.forecast.prophet_forecaster import ProphetForecaster
from ozon_agent.forecast.xgb_forecaster import XGBForecaster


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
    with pytest.raises(TypeError):
        BaseForecaster()


def test_base_forecaster_requires_fit_predict():
    """Test subclass must implement fit and predict."""
    class IncompleteForecaster(BaseForecaster):
        pass

    with pytest.raises(TypeError):
        IncompleteForecaster()


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
