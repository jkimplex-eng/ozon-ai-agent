from __future__ import annotations

from statistics import median as _statistics_median
from typing import Any


def safe_percentage_error(expected: float | int | None, actual: float | int | None) -> float | None:
    if expected is None or actual is None:
        return None
    expected_value = float(expected)
    actual_value = float(actual)
    denominator = abs(expected_value)
    if denominator == 0:
        return 0.0 if actual_value == 0 else abs(actual_value) * 100.0
    return abs(actual_value - expected_value) / denominator * 100.0


def direction_matches(
    expected_delta: float | int | None,
    actual_delta: float | int | None,
) -> bool | None:
    if expected_delta is None or actual_delta is None:
        return None
    expected_value = float(expected_delta)
    actual_value = float(actual_delta)
    if expected_value == 0 and actual_value == 0:
        return True
    if expected_value == 0 or actual_value == 0:
        return False
    return (expected_value > 0) == (actual_value > 0)


def success_score(
    expected_effect: dict[str, Any],
    actual_effect: dict[str, Any],
) -> float | None:
    metric_scores: list[float] = []
    for metric_name, expectation in expected_effect.items():
        if not isinstance(expectation, dict):
            continue
        expected_delta = _extract_expected_delta(expectation)
        actual_delta = _to_float_or_none(actual_effect.get(metric_name))
        if expected_delta is None or actual_delta is None:
            continue
        denominator = max(abs(expected_delta), 1.0)
        distance = abs(actual_delta - expected_delta) / denominator
        metric_scores.append(max(0.0, min(1.0, 1.0 - distance)))
    if not metric_scores:
        return None
    return sum(metric_scores) / len(metric_scores)


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(_statistics_median(values))


def bounded_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def extract_expected_delta(expectation: dict[str, Any]) -> float | None:
    return _extract_expected_delta(expectation)


def _extract_expected_delta(expectation: dict[str, Any]) -> float | None:
    for key in ("delta_pct", "expected_delta_pct", "change_pct", "target_pct"):
        raw_value = expectation.get(key)
        if raw_value is None:
            continue
        return float(raw_value)
    return None


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
