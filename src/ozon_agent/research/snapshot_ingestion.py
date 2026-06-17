from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ozon_agent.research.models import (
    ResearchObservation,
    SnapshotIngestionResult,
)
from ozon_agent.research.snapshot_builder import build_research_snapshot


class SnapshotIngestionError(ValueError):
    pass


def ingest_competitor_snapshot(
    path: str | Path,
    query: str | None = None,
    source_name: str = "manual",
) -> SnapshotIngestionResult:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        raise SnapshotIngestionError(f"Snapshot file not found: {snapshot_path}")

    rows = _load_rows(snapshot_path)
    return ingest_competitor_rows(
        rows=rows,
        query=query or snapshot_path.stem,
        source_name=source_name,
    )


def ingest_competitor_rows(
    rows: list[dict[str, Any]],
    query: str,
    source_name: str = "manual",
) -> SnapshotIngestionResult:
    observations: list[ResearchObservation] = []
    warnings: list[str] = []
    for index, row in enumerate(rows, start=1):
        try:
            observations.append(_row_to_observation(row, source_name=source_name))
        except SnapshotIngestionError as exc:
            warnings.append(f"row {index}: {exc}")

    snapshot = build_research_snapshot(
        query=query,
        observations=observations,
        source_name=source_name,
    )
    return SnapshotIngestionResult(
        snapshot=snapshot,
        raw_rows=len(rows),
        ingested_rows=len(snapshot.observations),
        skipped_rows=len(rows) - len(snapshot.observations),
        warnings=warnings,
    )


def _load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json_rows(path)
    if suffix == ".csv":
        return _load_csv_rows(path)
    raise SnapshotIngestionError("Only JSON and CSV competitor snapshots are supported")


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotIngestionError(f"Invalid JSON snapshot: {exc}") from exc

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        candidate_rows = payload.get("observations") or payload.get("rows") or payload.get("items")
        if not isinstance(candidate_rows, list):
            raise SnapshotIngestionError("JSON snapshot must contain observations, rows, or items")
        rows = candidate_rows
    else:
        raise SnapshotIngestionError("JSON snapshot must be an object or array")

    return [_ensure_mapping(row) for row in rows]


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _row_to_observation(row: dict[str, Any], source_name: str) -> ResearchObservation:
    sku = _string_value(row, "sku", "offer_id", "offerId", "product_id", "productId")
    if not sku:
        raise SnapshotIngestionError("missing sku/offer_id/product_id")

    return ResearchObservation(
        sku=sku,
        product_name=_string_value(row, "product_name", "productName", "name", "title"),
        seller_name=_string_value(row, "seller_name", "sellerName", "seller"),
        source_name=_string_value(row, "source_name", "sourceName") or source_name,
        source_url=_string_value(row, "source_url", "sourceUrl", "url"),
        observed_at=_datetime_value(row.get("observed_at") or row.get("observedAt")),
        price=_float_value(row.get("price")),
        rating=_float_value(row.get("rating")),
        review_count=_int_value(row.get("review_count") or row.get("reviewCount")),
        position=_int_value(row.get("position") or row.get("rank")),
        available=_bool_value(row.get("available")),
        attributes={
            key: value
            for key, value in row.items()
            if key
            not in {
                "sku",
                "offer_id",
                "offerId",
                "product_id",
                "productId",
                "product_name",
                "productName",
                "name",
                "title",
                "seller_name",
                "sellerName",
                "seller",
                "source_name",
                "sourceName",
                "source_url",
                "sourceUrl",
                "url",
                "observed_at",
                "observedAt",
                "price",
                "rating",
                "review_count",
                "reviewCount",
                "position",
                "rank",
                "available",
            }
        },
    )


def _ensure_mapping(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise SnapshotIngestionError("snapshot rows must be objects")
    return row


def _string_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _float_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def _bool_value(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "available", "in_stock"}:
        return True
    if normalized in {"0", "false", "no", "n", "unavailable", "out_of_stock"}:
        return False
    return None


def _datetime_value(value: Any) -> datetime:
    if value in (None, ""):
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
