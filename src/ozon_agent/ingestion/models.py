from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class LiveOzonDataset(StrEnum):
    PRODUCTS = "products"
    STOCKS = "stocks"
    ORDERS_FBO = "orders_fbo"
    ORDERS_FBS = "orders_fbs"
    FINANCE_OPERATIONS = "finance_operations"


@dataclass(frozen=True, slots=True)
class LiveOzonCredentials:
    client_id: str
    api_key: str


@dataclass(frozen=True, slots=True)
class LiveOzonEndpoint:
    dataset: LiveOzonDataset
    path: str
    description: str
    paginated: bool = False


@dataclass(slots=True)
class LiveOzonIngestionRequest:
    dataset: LiveOzonDataset
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 1000
    dry_run: bool = False
    save_raw: bool = True
    save_normalized: bool = True


@dataclass(slots=True)
class LiveOzonIngestionResult:
    dataset: LiveOzonDataset
    endpoint: str
    requested_at: str
    raw_rows: int
    normalized_rows: int
    raw_path: Path | None = None
    normalized_path: Path | None = None
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
