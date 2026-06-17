from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from ozon_agent.research.models import SnapshotIngestionResult
from ozon_agent.research.snapshot_ingestion import ingest_competitor_rows

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"


class FirecrawlIngestionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FirecrawlConfig:
    api_key: str | None = None
    api_key_env: str = "FIRECRAWL_API_KEY"
    endpoint_url: str = FIRECRAWL_SCRAPE_URL
    timeout_seconds: float = 60.0
    only_main_content: bool = True
    zero_data_retention: bool = False
    source_name: str = "firecrawl"

    def resolved_api_key(self) -> str:
        value = self.api_key or os.environ.get(self.api_key_env)
        if not value:
            raise FirecrawlIngestionError(
                f"Firecrawl API key is missing. Set {self.api_key_env}."
            )
        return value


@dataclass(frozen=True)
class FirecrawlIngestionResult:
    url: str
    ingestion: SnapshotIngestionResult
    metadata: dict[str, Any] = field(default_factory=dict)
    warning: str = ""


def ingest_firecrawl_snapshot(
    url: str,
    query: str,
    config: FirecrawlConfig | None = None,
    client: httpx.Client | None = None,
) -> FirecrawlIngestionResult:
    active_config = config or FirecrawlConfig()
    payload = _build_scrape_payload(url, active_config)
    response_payload = _post_scrape(payload, active_config, client)
    data = response_payload.get("data")
    if not isinstance(data, dict):
        raise FirecrawlIngestionError("Firecrawl response does not contain data object")

    rows = _extract_rows(data)
    ingestion = ingest_competitor_rows(
        rows=rows,
        query=query,
        source_name=active_config.source_name,
    )
    metadata = data.get("metadata", {})
    return FirecrawlIngestionResult(
        url=url,
        ingestion=ingestion,
        metadata=metadata if isinstance(metadata, dict) else {},
        warning=str(data.get("warning", "") or ""),
    )


def _build_scrape_payload(url: str, config: FirecrawlConfig) -> dict[str, Any]:
    return {
        "url": url,
        "formats": [
            "markdown",
            {
                "type": "json",
                "prompt": (
                    "Extract competitor product observations from this marketplace page. "
                    "Return an object with observations array. Each observation should include "
                    "sku or offer_id if visible, product_name, seller_name, source_url, price, "
                    "rating, review_count, position, and available."
                ),
                "schema": _observations_schema(),
            },
        ],
        "onlyMainContent": config.only_main_content,
        "zeroDataRetention": config.zero_data_retention,
    }


def _post_scrape(
    payload: dict[str, Any],
    config: FirecrawlConfig,
    client: httpx.Client | None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {config.resolved_api_key()}",
        "Content-Type": "application/json",
    }
    if client is None:
        with httpx.Client(timeout=config.timeout_seconds) as owned_client:
            response = owned_client.post(config.endpoint_url, headers=headers, json=payload)
    else:
        response = client.post(config.endpoint_url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise FirecrawlIngestionError(
            f"Firecrawl request failed with HTTP {response.status_code}: {response.text[:300]}"
        )
    payload_json = response.json()
    if not isinstance(payload_json, dict):
        raise FirecrawlIngestionError("Firecrawl response is not a JSON object")
    if payload_json.get("success") is False:
        raise FirecrawlIngestionError(f"Firecrawl request failed: {payload_json}")
    return payload_json


def _extract_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    structured = data.get("json")
    if isinstance(structured, list):
        return [_ensure_row(item) for item in structured]
    if isinstance(structured, dict):
        for key in ("observations", "rows", "items", "products"):
            value = structured.get(key)
            if isinstance(value, list):
                return [_ensure_row(item) for item in value]
        return [structured]
    raise FirecrawlIngestionError(
        "Firecrawl response does not contain structured json observations"
    )


def _ensure_row(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FirecrawlIngestionError("Firecrawl structured rows must be objects")
    return value


def _observations_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "observations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "offer_id": {"type": "string"},
                        "product_name": {"type": "string"},
                        "seller_name": {"type": "string"},
                        "source_url": {"type": "string"},
                        "price": {"type": "number"},
                        "rating": {"type": "number"},
                        "review_count": {"type": "integer"},
                        "position": {"type": "integer"},
                        "available": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
            }
        },
        "required": ["observations"],
        "additionalProperties": True,
    }
