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
        abs_err = np.abs((actual_arr[nonzero] - predicted_arr[nonzero]) / actual_arr[nonzero])
        mape = float(np.mean(abs_err) * 100)
    else:
        mape = 0.0

    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 4)}


def compare_models(
    forecasts: dict[str, list[float]], actual: list[float]
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, pred in forecasts.items():
        results[name] = evaluate_forecast(actual, pred)

    best_model = min(results, key=lambda k: results[k]["rmse"])
    results["best_model"] = best_model

    return results
