from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ozon_agent.research.knowledge.models import (
    CompetitorHistoryRecord,
    MarketInsightRecord,
    MarketKnowledgeSnapshot,
    MarketTrend,
)
from ozon_agent.research.models import ResearchObservation

DEFAULT_KNOWLEDGE_DIR = Path("data") / "market_knowledge"


def knowledge_root(storage_dir: str | Path | None = None) -> Path:
    if storage_dir is not None:
        return Path(storage_dir)
    env_dir = os.environ.get("OZON_AGENT_MARKET_KNOWLEDGE_DIR")
    return Path(env_dir) if env_dir else DEFAULT_KNOWLEDGE_DIR


def snapshots_dir(storage_dir: str | Path | None = None) -> Path:
    return knowledge_root(storage_dir) / "snapshots"


def insights_dir(storage_dir: str | Path | None = None) -> Path:
    return knowledge_root(storage_dir) / "insights"


def ensure_storage(storage_dir: str | Path | None = None) -> None:
    snapshots_dir(storage_dir).mkdir(parents=True, exist_ok=True)
    insights_dir(storage_dir).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def snapshot_to_dict(snapshot: MarketKnowledgeSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "query": snapshot.query,
        "source_name": snapshot.source_name,
        "captured_at": _datetime_to_str(snapshot.captured_at),
        "created_at": _datetime_to_str(snapshot.created_at),
        "observations": [observation_to_dict(item) for item in snapshot.observations],
    }


def snapshot_from_dict(payload: dict[str, Any]) -> MarketKnowledgeSnapshot:
    return MarketKnowledgeSnapshot(
        id=str(payload["id"]),
        query=str(payload.get("query", "")),
        source_name=str(payload.get("source_name", "manual")),
        captured_at=_datetime_from_value(payload.get("captured_at")),
        created_at=_datetime_from_value(payload.get("created_at")),
        observations=[
            observation_from_dict(item)
            for item in payload.get("observations", [])
            if isinstance(item, dict)
        ],
    )


def observation_to_dict(observation: ResearchObservation) -> dict[str, Any]:
    return {
        "sku": observation.sku,
        "product_name": observation.product_name,
        "seller_name": observation.seller_name,
        "source_name": observation.source_name,
        "source_url": observation.source_url,
        "observed_at": _datetime_to_str(observation.observed_at),
        "price": observation.price,
        "rating": observation.rating,
        "review_count": observation.review_count,
        "position": observation.position,
        "available": observation.available,
        "attributes": observation.attributes,
    }


def observation_from_dict(payload: dict[str, Any]) -> ResearchObservation:
    attributes = payload.get("attributes", {})
    return ResearchObservation(
        sku=str(payload.get("sku", "")),
        product_name=str(payload.get("product_name", "")),
        seller_name=str(payload.get("seller_name", "")),
        source_name=str(payload.get("source_name", "manual")),
        source_url=str(payload.get("source_url", "")),
        observed_at=_datetime_from_value(payload.get("observed_at")),
        price=_optional_float(payload.get("price")),
        rating=_optional_float(payload.get("rating")),
        review_count=_optional_int(payload.get("review_count")),
        position=_optional_int(payload.get("position")),
        available=_optional_bool(payload.get("available")),
        attributes=attributes if isinstance(attributes, dict) else {},
    )


def insight_to_dict(insight: MarketInsightRecord) -> dict[str, Any]:
    return {
        "id": insight.id,
        "created_at": _datetime_to_str(insight.created_at),
        "insight_type": insight.insight_type,
        "sku": insight.sku,
        "message": insight.message,
        "severity": insight.severity,
        "snapshot_id": insight.snapshot_id,
        "previous_snapshot_id": insight.previous_snapshot_id,
        "current_snapshot_id": insight.current_snapshot_id,
        "competitor_key": insight.competitor_key,
        "metrics": insight.metrics,
    }


def insight_from_dict(payload: dict[str, Any]) -> MarketInsightRecord:
    metrics = payload.get("metrics", {})
    return MarketInsightRecord(
        id=str(payload["id"]),
        created_at=_datetime_from_value(payload.get("created_at")),
        insight_type=str(payload.get("insight_type", "")),
        sku=str(payload.get("sku", "")),
        message=str(payload.get("message", "")),
        severity=str(payload.get("severity", "LOW")),
        snapshot_id=_optional_str(payload.get("snapshot_id")),
        previous_snapshot_id=_optional_str(payload.get("previous_snapshot_id")),
        current_snapshot_id=_optional_str(payload.get("current_snapshot_id")),
        competitor_key=_optional_str(payload.get("competitor_key")),
        metrics=metrics if isinstance(metrics, dict) else {},
    )


def history_record_from_observation(
    snapshot_id: str,
    observation: ResearchObservation,
) -> CompetitorHistoryRecord:
    return CompetitorHistoryRecord(
        snapshot_id=snapshot_id,
        sku=observation.sku,
        competitor_key=competitor_key(observation),
        seller_name=observation.seller_name,
        source_url=observation.source_url,
        observed_at=observation.observed_at,
        price=observation.price,
        rating=observation.rating,
        review_count=observation.review_count,
        position=observation.position,
        available=observation.available,
    )


def trend_to_dict(trend: MarketTrend) -> dict[str, Any]:
    return {
        "sku": trend.sku,
        "competitor_key": trend.competitor_key,
        "metric": trend.metric,
        "direction": trend.direction,
        "first_value": trend.first_value,
        "last_value": trend.last_value,
        "delta": trend.delta,
        "delta_percent": trend.delta_percent,
        "snapshot_count": trend.snapshot_count,
    }


def competitor_key(observation: ResearchObservation) -> str:
    seller = observation.seller_name.strip().lower()
    url = observation.source_url.strip().lower()
    sku = observation.sku.strip().lower()
    if seller and url:
        return f"{sku}|{seller}|{url}"
    if seller:
        return f"{sku}|{seller}"
    if url:
        return f"{sku}|{url}"
    return sku


def _datetime_to_str(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.isoformat()


def _datetime_from_value(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
