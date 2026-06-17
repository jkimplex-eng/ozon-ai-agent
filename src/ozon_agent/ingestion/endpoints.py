from __future__ import annotations

from datetime import datetime
from typing import Any

from ozon_agent.ingestion.models import LiveOzonDataset, LiveOzonEndpoint

READ_ONLY_ENDPOINTS: dict[LiveOzonDataset, LiveOzonEndpoint] = {
    LiveOzonDataset.PRODUCTS: LiveOzonEndpoint(
        dataset=LiveOzonDataset.PRODUCTS,
        path="/v2/product/list",
        description="Product identifiers list",
        paginated=True,
    ),
    LiveOzonDataset.STOCKS: LiveOzonEndpoint(
        dataset=LiveOzonDataset.STOCKS,
        path="/v4/product/info/stocks",
        description="Product stock information",
        paginated=True,
    ),
    LiveOzonDataset.ORDERS_FBO: LiveOzonEndpoint(
        dataset=LiveOzonDataset.ORDERS_FBO,
        path="/v3/posting/fbo/list",
        description="FBO posting list",
        paginated=True,
    ),
    LiveOzonDataset.ORDERS_FBS: LiveOzonEndpoint(
        dataset=LiveOzonDataset.ORDERS_FBS,
        path="/v3/posting/fbs/list",
        description="FBS posting list",
        paginated=True,
    ),
    LiveOzonDataset.FINANCE_OPERATIONS: LiveOzonEndpoint(
        dataset=LiveOzonDataset.FINANCE_OPERATIONS,
        path="/v3/finance/transaction/list",
        description="Finance transaction list",
        paginated=True,
    ),
}

FORBIDDEN_PATH_MARKERS = (
    "/import",
    "/update",
    "/delete",
    "/archive",
    "/unarchive",
    "/price",
    "/discount",
    "/campaign",
    "/bid",
    "/budget",
)


def get_read_only_endpoint(dataset: LiveOzonDataset) -> LiveOzonEndpoint:
    return READ_ONLY_ENDPOINTS[dataset]


def validate_read_only_path(path: str) -> None:
    normalized = path.lower()
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in normalized:
            raise ValueError(f"Ozon endpoint is not allowed for live ingestion: {path}")


def build_request_payload(
    dataset: LiveOzonDataset,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 1000,
    offset: int = 0,
    last_id: str = "",
    page: int = 1,
) -> dict[str, Any]:
    if dataset is LiveOzonDataset.PRODUCTS:
        return {"filter": {}, "last_id": last_id, "limit": limit}
    if dataset is LiveOzonDataset.STOCKS:
        return {"filter": {}, "limit": limit, "last_id": last_id}
    if dataset in {LiveOzonDataset.ORDERS_FBO, LiveOzonDataset.ORDERS_FBS}:
        return {
            "dir": "ASC",
            "filter": {
                "since": _required_date(date_from, "date_from"),
                "to": _required_date(date_to, "date_to"),
            },
            "limit": min(limit, 1000),
            "offset": offset,
            "with": {"analytics_data": True, "financial_data": True},
        }
    if dataset is LiveOzonDataset.FINANCE_OPERATIONS:
        return {
            "filter": {
                "date": {
                    "from": _required_date(date_from, "date_from"),
                    "to": _required_date(date_to, "date_to"),
                }
            },
            "page": page,
            "page_size": min(limit, 1000),
        }
    raise ValueError(f"Unsupported live Ozon dataset: {dataset.value}")


def _required_date(value: str | None, name: str) -> str:
    if value is None:
        raise ValueError(f"{name} is required for this dataset")
    parsed = datetime.fromisoformat(value)
    return parsed.isoformat()
