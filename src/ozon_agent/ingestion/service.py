from __future__ import annotations

from pathlib import Path

from ozon_agent.ingestion.client import LiveOzonReadOnlyClient
from ozon_agent.ingestion.endpoints import build_request_payload, get_read_only_endpoint
from ozon_agent.ingestion.models import (
    LiveOzonDataset,
    LiveOzonIngestionRequest,
    LiveOzonIngestionResult,
    utc_now_iso,
)
from ozon_agent.ingestion.normalizers import extract_raw_rows, normalize_rows
from ozon_agent.ingestion.store import save_normalized_rows, save_raw_payload


def ingest_live_ozon_dataset(
    request: LiveOzonIngestionRequest,
    *,
    client: LiveOzonReadOnlyClient | None = None,
    storage_root: str | Path | None = None,
) -> LiveOzonIngestionResult:
    endpoint = get_read_only_endpoint(request.dataset)
    requested_at = utc_now_iso()
    payload = build_request_payload(
        request.dataset,
        date_from=request.date_from,
        date_to=request.date_to,
        limit=request.limit,
    )
    if request.dry_run:
        return LiveOzonIngestionResult(
            dataset=request.dataset,
            endpoint=endpoint.path,
            requested_at=requested_at,
            raw_rows=0,
            normalized_rows=0,
            warnings=["dry_run: request built but HTTP call skipped"],
            dry_run=True,
        )

    active_client = client or LiveOzonReadOnlyClient.from_env()
    close_client = client is None
    try:
        response = active_client.post_read_only(endpoint.path, payload)
    finally:
        if close_client:
            active_client.close()

    raw_rows = extract_raw_rows(request.dataset, response)
    normalized_rows = normalize_rows(request.dataset, response)
    raw_path = (
        save_raw_payload(request.dataset, response, requested_at, storage_root)
        if request.save_raw
        else None
    )
    normalized_path = (
        save_normalized_rows(request.dataset, normalized_rows, requested_at, storage_root)
        if request.save_normalized
        else None
    )
    warnings: list[str] = []
    if endpoint.paginated:
        warnings.append("pagination support is prepared; this call fetches the first page only")
    return LiveOzonIngestionResult(
        dataset=request.dataset,
        endpoint=endpoint.path,
        requested_at=requested_at,
        raw_rows=len(raw_rows),
        normalized_rows=len(normalized_rows),
        raw_path=raw_path,
        normalized_path=normalized_path,
        warnings=warnings,
    )


def list_live_ozon_datasets() -> list[LiveOzonDataset]:
    return list(LiveOzonDataset)
