from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from ozon_agent.decision.models import OpportunityType, RecommendationAction


class MemoryResult(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class RecommendationMemoryRecord:
    id: str
    created_at: str
    sku: str
    action: RecommendationAction
    opportunity_type: OpportunityType | None = None
    reason: str = ""
    expected_effect: str | dict[str, Any] = ""
    actual_effect: dict[str, Any] = field(default_factory=dict)
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    risk_score: float = 0.0
    result: MemoryResult = MemoryResult.UNKNOWN
    success_score: float = 0.0
    source_recommendation_id: str | None = None
    campaign_id: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MemoryMatch:
    record_id: str
    score: float
    reasons: list[str]
    result: MemoryResult
    success_score: float
    action: RecommendationAction
    sku: str


@dataclass(slots=True)
class MemoryInsight:
    id: str
    created_at: str
    action: RecommendationAction
    opportunity_type: OpportunityType | None
    sku: str | None
    sample_size: int
    success_rate: float
    average_success_score: float
    message: str
    supporting_records: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RecommendationMemoryStats:
    total_records: int
    success_rate: float
    average_success_score: float
    by_action: dict[str, dict[str, Any]]
    by_sku: dict[str, dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_memory_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"
