"""Tests for forecast module."""
import pytest

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
    with pytest.raises(TypeError):
        BaseForecaster()


def test_base_forecaster_requires_fit_predict():
    """Test subclass must implement fit and predict."""
    class IncompleteForecaster(BaseForecaster):
        pass

    with pytest.raises(TypeError):
        IncompleteForecaster()
