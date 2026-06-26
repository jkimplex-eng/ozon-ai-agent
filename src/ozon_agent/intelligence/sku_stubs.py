"""SKU Intelligence stubs for telegram bot UI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    RISK = "RISK"


class TrendDirection(StrEnum):
    GROWING = "GROWING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


@dataclass(frozen=True)
class SkuMetrics:
    product_name: str | None = None
    revenue: float = 0.0
    orders: int = 0
    margin: float = 0.0
    advertising: float = 0.0
    drr: float = 0.0
    ctr: float = 0.0
    cvr: float = 0.0
    reviews: int = 0


@dataclass(frozen=True)
class HealthInfo:
    score: int = 0
    status: HealthStatus = HealthStatus.HEALTHY


@dataclass(frozen=True)
class TrendInfo:
    direction: TrendDirection = TrendDirection.STABLE
    revenue_change_pct: float = 0.0


@dataclass(frozen=True)
class RootCause:
    factor: str = "нет проблем"
    confidence: float = 0.0
    evidence: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.evidence is None:
            object.__setattr__(self, "evidence", [])


@dataclass(frozen=True)
class RecommendationInfo:
    action: str = ""
    expected_impact: str = ""
    confidence: float = 0.0


def analyze_sku(sku: str) -> dict[str, Any]:
    return {
        "metrics": SkuMetrics(),
        "health": HealthInfo(),
        "trend": TrendInfo(),
        "root_cause": RootCause(),
        "recommendation": None,
    }


def get_top_skus(limit: int = 10) -> list[dict[str, Any]]:
    return []


def get_worst_skus(limit: int = 10) -> list[dict[str, Any]]:
    return []
