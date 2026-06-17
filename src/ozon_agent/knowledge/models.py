from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class KnowledgeDomain(StrEnum):
    SEO = "SEO"
    RANKING = "RANKING"
    ADS = "ADS"
    CONTENT = "CONTENT"
    PRICING = "PRICING"
    LOGISTICS = "LOGISTICS"
    REVIEWS = "REVIEWS"
    EXPERIMENTS = "EXPERIMENTS"


@dataclass(frozen=True)
class KnowledgeSource:
    name: str
    path: str
    source_type: str = "file"


@dataclass(frozen=True)
class KnowledgeRule:
    id: str
    domain: KnowledgeDomain
    title: str
    condition: str
    recommendation: str
    rationale: str
    signals: list[str] = field(default_factory=list)
    source: KnowledgeSource | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeFact:
    id: str
    domain: KnowledgeDomain
    statement: str
    source: KnowledgeSource | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeRecommendation:
    rule_id: str
    domain: KnowledgeDomain
    title: str
    signal: str
    reason: str
    source: KnowledgeSource | None = None
    priority: str = "MEDIUM"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeExperiment:
    id: str
    title: str
    domain: KnowledgeDomain
    hypothesis: str
    metric: str
    source: str = "knowledge"
    metadata: dict[str, Any] = field(default_factory=dict)
