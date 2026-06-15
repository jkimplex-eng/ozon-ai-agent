from __future__ import annotations

from collections import defaultdict

from ozon_agent.learning.metrics import bounded_score
from ozon_agent.learning.models import ActionCalibration, CalibrationResult, LearningSample
from ozon_agent.learning.outcome_learning import calculate_recommendation_accuracy


def calibrate_confidence(samples: list[LearningSample]) -> CalibrationResult:
    overall_accuracy = calculate_recommendation_accuracy(samples)
    overall_factor, reasons = _build_calibration_factor(samples)
    return CalibrationResult(
        overall_factor=overall_factor,
        overall_accuracy=overall_accuracy,
        by_action=_build_dimension_calibration(samples, "action"),
        by_sku=_build_dimension_calibration(samples, "sku"),
        by_risk_level=_build_dimension_calibration(samples, "risk_level"),
        by_confidence_level=_build_dimension_calibration(samples, "confidence_level"),
        reasons=reasons,
    )


def get_calibration_factor(
    samples: list[LearningSample],
    action: str | None = None,
    sku: str | None = None,
    risk_level: str | None = None,
) -> float:
    filtered = [
        sample
        for sample in samples
        if (action is None or sample.action.value == action)
        and (sku is None or sample.sku == sku)
        and (risk_level is None or _risk_value(sample) == risk_level)
    ]
    factor, _reasons = _build_calibration_factor(filtered)
    return factor


def apply_calibration(original_confidence: float, calibration_factor: float) -> float:
    return bounded_score(original_confidence * calibration_factor)


def _build_dimension_calibration(
    samples: list[LearningSample],
    dimension: str,
) -> dict[str, ActionCalibration]:
    grouped: dict[str, list[LearningSample]] = defaultdict(list)
    for sample in samples:
        key = _dimension_value(sample, dimension)
        grouped[key].append(sample)
    calibrations: dict[str, ActionCalibration] = {}
    for key, group_samples in grouped.items():
        factor, reasons = _build_calibration_factor(group_samples)
        accuracy = calculate_recommendation_accuracy(group_samples)
        calibrations[key] = ActionCalibration(
            dimension=dimension,
            key=key,
            sample_size=len(group_samples),
            calibration_factor=factor,
            direction_accuracy=accuracy.direction_accuracy,
            average_error=accuracy.average_percentage_error,
            reasons=reasons,
        )
    return calibrations


def _build_calibration_factor(samples: list[LearningSample]) -> tuple[float, list[str]]:
    if not samples:
        return 0.6, ["no historical samples"]

    accuracy = calculate_recommendation_accuracy(samples)
    factor = 1.0
    reasons: list[str] = []

    if accuracy.average_percentage_error >= 50.0:
        factor -= 0.25
        reasons.append("high historical error lowers confidence")
    elif accuracy.average_percentage_error >= 25.0:
        factor -= 0.15
        reasons.append("moderate historical error lowers confidence")
    else:
        factor += 0.05
        reasons.append("low historical error supports confidence")

    if accuracy.direction_accuracy >= 0.75:
        factor += 0.1
        reasons.append("strong direction accuracy improves confidence")
    elif accuracy.direction_accuracy < 0.5:
        factor -= 0.1
        reasons.append("weak direction accuracy lowers confidence")

    if len(samples) < 3:
        factor -= 0.2
        reasons.append("low sample size penalty")
    elif len(samples) < 5:
        factor -= 0.1
        reasons.append("limited sample size penalty")
    else:
        reasons.append("sample size is acceptable")

    success_scores = [
        sample.success_score for sample in samples if sample.success_score is not None
    ]
    if success_scores:
        average_success = sum(success_scores) / len(success_scores)
        if average_success >= 0.75:
            factor += 0.05
            reasons.append("historical success score is strong")
        elif average_success < 0.5:
            factor -= 0.1
            reasons.append("historical success score is weak")

    if len(samples) < 3:
        factor = min(factor, 0.9)

    return bounded_score(factor), reasons


def _dimension_value(sample: LearningSample, dimension: str) -> str:
    if dimension == "action":
        return sample.action.value
    if dimension == "sku":
        return sample.sku
    if dimension == "risk_level":
        return _risk_value(sample)
    if dimension == "confidence_level":
        return sample.confidence_level.value if sample.confidence_level is not None else "UNKNOWN"
    raise ValueError(f"Unsupported dimension: {dimension}")


def _risk_value(sample: LearningSample) -> str:
    return sample.risk_level.value if sample.risk_level is not None else "UNKNOWN"
