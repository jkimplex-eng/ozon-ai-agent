from __future__ import annotations

from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel
from ozon_agent.learning.confidence_calibration import (
    apply_calibration,
    calibrate_confidence,
    get_calibration_factor,
)
from ozon_agent.learning.models import LearningSample


def test_high_error_lowers_confidence() -> None:
    samples = [
        _sample(percentage_error=70.0, direction_match=False, success=0.2),
        _sample(percentage_error=60.0, direction_match=False, success=0.3),
        _sample(percentage_error=55.0, direction_match=False, success=0.4),
    ]
    result = calibrate_confidence(samples)
    assert result.overall_factor < 1.0


def test_low_sample_size_penalty() -> None:
    samples = [_sample(percentage_error=10.0, direction_match=True, success=0.9)]
    factor = get_calibration_factor(samples)
    assert factor < 1.0


def test_action_and_sku_level_calibration() -> None:
    samples = [
        _sample(
            percentage_error=12.0,
            direction_match=True,
            success=0.9,
            action="INCREASE_BUDGET",
            sku="SKU-1",
        ),
        _sample(
            percentage_error=18.0,
            direction_match=True,
            success=0.8,
            action="INCREASE_BUDGET",
            sku="SKU-1",
        ),
        _sample(
            percentage_error=45.0,
            direction_match=False,
            success=0.3,
            action="DECREASE_PRICE",
            sku="SKU-2",
        ),
    ]
    result = calibrate_confidence(samples)
    assert "INCREASE_BUDGET" in result.by_action
    assert "SKU-1" in result.by_sku


def test_bounded_confidence_scores() -> None:
    assert apply_calibration(0.9, 1.5) == 1.0
    assert apply_calibration(0.2, 0.0) == 0.0


def _sample(
    percentage_error: float,
    direction_match: bool,
    success: float,
    action: str = "INCREASE_BUDGET",
    sku: str = "SKU-1",
) -> LearningSample:
    return LearningSample(
        recommendation_id=f"{action}-{sku}-{percentage_error}",
        action=RecommendationAction(action),
        sku=sku,
        risk_level=RiskLevel.LOW,
        confidence_level=ConfidenceLevel.HIGH,
        opportunity_type=None,
        time_window_days=7,
        expected_effect={"orders": {"delta_pct": 10.0}},
        actual_effect={"orders": 8.0},
        absolute_errors={"orders": 2.0},
        percentage_errors={"orders": percentage_error},
        direction_matches={"orders": direction_match},
        success_score=success,
        forecast_error=percentage_error,
    )
