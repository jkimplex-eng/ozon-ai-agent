"""COGS data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class CogsStatus(StrEnum):
    OK = "OK"
    MISSING = "MISSING"
    INVALID = "INVALID"


@dataclass(slots=True)
class CogsRecord:
    id: str
    sku: str
    offer_id: str | None = None
    product_name: str | None = None
    unit_cost: float = 0.0
    logistics_cost: float = 0.0
    packaging_cost: float = 0.0
    source: str = "manual"
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class CogsCoverageReport:
    total_products: int
    with_cogs: int
    without_cogs: int
    coverage_pct: float
    missing_skus: list[str] = field(default_factory=list)


def create_cogs_record(
    sku: str,
    unit_cost: float,
    offer_id: str | None = None,
    product_name: str | None = None,
    logistics_cost: float = 0.0,
    packaging_cost: float = 0.0,
    source: str = "manual",
) -> CogsRecord:
    """Create a new COGS record."""
    return CogsRecord(
        id=str(uuid4()),
        sku=sku,
        offer_id=offer_id,
        product_name=product_name,
        unit_cost=unit_cost,
        logistics_cost=logistics_cost,
        packaging_cost=packaging_cost,
        source=source,
        updated_at=datetime.now(UTC),
    )
