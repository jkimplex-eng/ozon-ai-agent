"""Forecasting V2 — daily forecasts with confidence and drift detection."""
from __future__ import annotations

import json
import logging
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FORECASTS_DIR = Path("data/forecasts")


@dataclass(frozen=True)
class ForecastPoint:
    date: str
    metric: str
    forecast_value: float
    confidence: str
    lower_bound: float
    upper_bound: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuForecast:
    sku: str
    generated_at: str
    forecasts_7d: list[ForecastPoint]
    forecasts_14d: list[ForecastPoint]
    forecasts_30d: list[ForecastPoint]
    confidence_level: str
    historical_stability: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "generated_at": self.generated_at,
            "forecasts_7d": [f.to_dict() for f in self.forecasts_7d],
            "forecasts_14d": [f.to_dict() for f in self.forecasts_14d],
            "forecasts_30d": [f.to_dict() for f in self.forecasts_30d],
            "confidence_level": self.confidence_level,
            "historical_stability": self.historical_stability,
        }


@dataclass(frozen=True)
class ForecastDrift:
    sku: str
    metric: str
    forecast_value: float
    actual_value: float
    drift_pct: float
    detected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _calculate_stability(values: list[float]) -> float:
    """Calculate historical stability (0-1, higher = more stable)."""
    if len(values) < 2:
        return 0.0
    cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 1.0
    return max(0.0, min(1.0, 1.0 - cv))


def _confidence_from_stability(stability: float) -> str:
    """Determine confidence level from stability."""
    if stability >= 0.7:
        return "High"
    if stability >= 0.4:
        return "Medium"
    return "Low"


def _simple_forecast(values: list[float], days: int) -> list[float]:
    """Simple moving average forecast."""
    if not values:
        return [0.0] * days
    window = min(7, len(values))
    avg = sum(values[-window:]) / window
    trend = 0.0
    if len(values) >= 2:
        trend = (values[-1] - values[-2]) / max(1, abs(values[-2])) if values[-2] != 0 else 0
    forecasts = []
    for i in range(1, days + 1):
        forecast = avg * (1 + trend * i)
        forecasts.append(max(0, forecast))
    return forecasts


def build_sku_forecast(
    sku: str,
    daily_data: list[dict[str, Any]],
) -> SkuForecast:
    """Build forecast for a single SKU."""
    now = datetime.now(UTC).isoformat()

    sku_data = [r for r in daily_data if str(r.get("sku", "")) == sku]
    if not sku_data:
        sku_data = daily_data[-30:]

    revenues = [float(r.get("revenue", 0)) for r in sku_data]

    stability = _calculate_stability(revenues)
    confidence = _confidence_from_stability(stability)

    def _make_forecast(metric: str, values: list[float], days: int) -> list[ForecastPoint]:
        points = []
        base_date = datetime.now(UTC)
        forecasts = _simple_forecast(values, days)
        for i, val in enumerate(forecasts):
            date = base_date.replace(day=base_date.day + i + 1)
            width = val * (1 - stability) * 0.2
            points.append(ForecastPoint(
                date=date.strftime("%Y-%m-%d"),
                metric=metric,
                forecast_value=round(val, 2),
                confidence=confidence,
                lower_bound=round(max(0, val - width), 2),
                upper_bound=round(val + width, 2),
            ))
        return points

    return SkuForecast(
        sku=sku,
        generated_at=now,
        forecasts_7d=_make_forecast("revenue", revenues, 7),
        forecasts_14d=_make_forecast("revenue", revenues, 14),
        forecasts_30d=_make_forecast("revenue", revenues, 30),
        confidence_level=confidence,
        historical_stability=stability,
    )


def detect_forecast_drift(
    sku: str,
    metric: str,
    forecast_value: float,
    actual_value: float,
) -> ForecastDrift | None:
    """Detect drift between forecast and reality."""
    if forecast_value == 0:
        return None
    drift_pct = (actual_value - forecast_value) / abs(forecast_value) * 100
    if abs(drift_pct) > 10:
        return ForecastDrift(
            sku=sku,
            metric=metric,
            forecast_value=forecast_value,
            actual_value=actual_value,
            drift_pct=drift_pct,
            detected_at=datetime.now(UTC).isoformat(),
        )
    return None


def save_forecast(forecast: SkuForecast) -> Path:
    """Save forecast to disk."""
    FORECASTS_DIR.mkdir(parents=True, exist_ok=True)
    path = FORECASTS_DIR / f"forecast_{forecast.sku}.json"
    path.write_text(
        json.dumps(forecast.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return path


def format_forecast(forecast: SkuForecast) -> str:
    """Format forecast for display."""
    lines = [
        f"FORECAST: {forecast.sku}",
        "=" * 40,
        f"Confidence: {forecast.confidence_level}",
        f"Stability: {forecast.historical_stability:.2f}",
        "",
        "7-Day Forecast:",
    ]
    for p in forecast.forecasts_7d[:7]:
        fb = f"{p.lower_bound:,.0f}-{p.upper_bound:,.0f}"
        lines.append(f"  {p.date}: {p.forecast_value:,.0f} [{fb}]")

    lines.append("")
    lines.append("14-Day Summary:")
    total_14 = sum(p.forecast_value for p in forecast.forecasts_14d)
    lines.append(f"  Total: {total_14:,.0f}")

    lines.append("")
    lines.append("30-Day Summary:")
    total_30 = sum(p.forecast_value for p in forecast.forecasts_30d)
    lines.append(f"  Total: {total_30:,.0f}")

    return "\n".join(lines)
