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
    def fit(
        self, df: pd.DataFrame, target: str,
        features: list[str] | None = None, date_col: str = "date",
    ) -> None:
        ...

    @abstractmethod
    def predict(self, periods: int) -> ForecastResult:
        ...
