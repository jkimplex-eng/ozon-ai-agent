from __future__ import annotations

from typing import Any

LOWER_IS_BETTER_METRICS = {"drr", "cpc", "stockout_probability", "search_position"}
HIGHER_IS_BETTER_METRICS = {
    "orders",
    "revenue",
    "profit",
    "roas",
    "ctr",
    "conversion_rate",
}
SUPPORTED_METRICS = LOWER_IS_BETTER_METRICS | HIGHER_IS_BETTER_METRICS


def calculate_baseline(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        metric_name: metric_value
        for metric_name, metric_value in (
            (name, _to_float_or_none(value)) for name, value in metrics.items()
        )
        if metric_value is not None
    }


def calculate_delta(baseline: float | int | None, current: float | int | None) -> float | None:
    if baseline is None or current is None:
        return None
    return float(current) - float(baseline)


def calculate_percent_change(
    baseline: float | int | None,
    current: float | int | None,
) -> float | None:
    if baseline is None or current is None:
        return None
    baseline_value = float(baseline)
    current_value = float(current)
    if baseline_value == 0:
        return 0.0 if current_value == 0 else current_value * 100.0
    return (current_value - baseline_value) / abs(baseline_value) * 100.0


def compare_metric_direction(
    expected_delta: float | None,
    actual_delta: float | None,
) -> bool | None:
    if expected_delta is None or actual_delta is None:
        return None
    if expected_delta == 0 and actual_delta == 0:
        return True
    if expected_delta == 0 or actual_delta == 0:
        return False
    return (expected_delta > 0) == (actual_delta > 0)


def is_lower_better(metric_name: str) -> bool:
    return metric_name in LOWER_IS_BETTER_METRICS


def normalize_expected_delta(metric_name: str, expected_value: Any) -> float | None:
    if isinstance(expected_value, dict):
        for key in ("delta_pct", "expected_delta_pct", "change_pct", "target_pct"):
            raw_value = expected_value.get(key)
            if raw_value is not None:
                expected_delta = float(raw_value)
                return -abs(expected_delta) if is_lower_better(metric_name) else expected_delta
    numeric = _to_float_or_none(expected_value)
    if numeric is None:
        return None
    return -abs(numeric) if is_lower_better(metric_name) else numeric


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return float(value)
