from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.models import ResearchObservation, ResearchSnapshot
from ozon_agent.research.source_registry import get_source


def build_research_snapshot(
    query: str,
    observations: list[ResearchObservation] | None = None,
    source_name: str = "manual",
    captured_at: datetime | None = None,
) -> ResearchSnapshot:
    get_source(source_name)
    return ResearchSnapshot(
        query=query.strip(),
        source_name=source_name,
        captured_at=captured_at or datetime.now(UTC),
        observations=_normalize_observations(observations or []),
    )


def _normalize_observations(
    observations: list[ResearchObservation],
) -> list[ResearchObservation]:
    normalized: list[ResearchObservation] = []
    for observation in observations:
        normalized.append(
            ResearchObservation(
                sku=observation.sku.strip(),
                product_name=observation.product_name.strip(),
                seller_name=observation.seller_name.strip(),
                source_name=observation.source_name.strip() or "manual",
                source_url=observation.source_url.strip(),
                observed_at=observation.observed_at,
                price=_positive_float_or_none(observation.price),
                rating=_bounded_rating(observation.rating),
                review_count=_non_negative_int_or_none(observation.review_count),
                position=_non_negative_int_or_none(observation.position),
                available=observation.available,
                attributes=dict(observation.attributes),
            )
        )
    return normalized


def _positive_float_or_none(value: float | None) -> float | None:
    if value is None or value < 0:
        return None
    return float(value)


def _bounded_rating(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(float(value), 5.0))


def _non_negative_int_or_none(value: int | None) -> int | None:
    if value is None or value < 0:
        return None
    return int(value)
