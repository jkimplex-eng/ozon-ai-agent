from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from ozon_agent.decision.models import OpportunityType, RecommendationAction
from ozon_agent.memory.models import (
    MemoryInsight,
    MemoryResult,
    RecommendationMemoryRecord,
)

DEFAULT_MEMORY_ROOT = Path("data") / "recommendation_memory"


def memory_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("OZON_AGENT_RECOMMENDATION_MEMORY_ROOT")
    return Path(env_root) if env_root else DEFAULT_MEMORY_ROOT


def ensure_memory_storage(root: str | Path | None = None) -> Path:
    base = memory_root(root)
    for folder in ("records", "insights", "statistics"):
        (base / folder).mkdir(parents=True, exist_ok=True)
    return base


def save_memory_record(
    record: RecommendationMemoryRecord,
    root: str | Path | None = None,
) -> str:
    _write_json("records", record.id, _to_jsonable(record), root=root)
    return record.id


def load_memory_record(
    record_id: str,
    root: str | Path | None = None,
) -> RecommendationMemoryRecord | None:
    payload = _read_json("records", record_id, root=root)
    return _record_from_dict(payload) if payload is not None else None


def list_memory_records(
    root: str | Path | None = None,
    limit: int | None = None,
) -> list[RecommendationMemoryRecord]:
    rows = [_record_from_dict(row) for row in _list_json("records", root=root)]
    rows.sort(key=lambda item: item.created_at, reverse=True)
    return rows if limit is None else rows[:limit]


def search_memory_records(
    query: str,
    root: str | Path | None = None,
) -> list[RecommendationMemoryRecord]:
    normalized = query.strip().lower()
    if not normalized:
        return list_memory_records(root=root)
    return [
        record
        for record in list_memory_records(root=root)
        if normalized in _record_search_text(record)
    ]


def delete_memory_record(record_id: str, root: str | Path | None = None) -> bool:
    path = memory_root(root) / "records" / f"{record_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def save_memory_insight(insight: MemoryInsight, root: str | Path | None = None) -> str:
    _write_json("insights", insight.id, _to_jsonable(insight), root=root)
    return insight.id


def list_memory_insights(root: str | Path | None = None) -> list[MemoryInsight]:
    rows = [_insight_from_dict(row) for row in _list_json("insights", root=root)]
    rows.sort(key=lambda item: item.created_at, reverse=True)
    return rows


def _write_json(
    folder: str,
    item_id: str,
    payload: dict[str, Any],
    root: str | Path | None = None,
) -> Path:
    base = ensure_memory_storage(root)
    path = base / folder / f"{item_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _read_json(
    folder: str,
    item_id: str,
    root: str | Path | None = None,
) -> dict[str, Any] | None:
    path = memory_root(root) / folder / f"{item_id}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _list_json(folder: str, root: str | Path | None = None) -> list[dict[str, Any]]:
    base = memory_root(root) / folder
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _record_from_dict(row: dict[str, Any]) -> RecommendationMemoryRecord:
    return RecommendationMemoryRecord(
        id=str(row["id"]),
        created_at=str(row.get("created_at", "")),
        sku=str(row.get("sku", "")),
        action=_coerce_action(row.get("action", RecommendationAction.NO_ACTION.value)),
        opportunity_type=_coerce_opportunity(row.get("opportunity_type")),
        reason=str(row.get("reason", "")),
        expected_effect=row.get("expected_effect", ""),
        actual_effect=_dict(row.get("actual_effect")),
        supporting_metrics=_dict(row.get("supporting_metrics")),
        confidence_score=_float(row.get("confidence_score")),
        risk_score=_float(row.get("risk_score")),
        result=_coerce_result(row.get("result", MemoryResult.UNKNOWN.value)),
        success_score=_float(row.get("success_score")),
        source_recommendation_id=(
            str(row["source_recommendation_id"])
            if row.get("source_recommendation_id") is not None
            else None
        ),
        campaign_id=str(row.get("campaign_id", "")),
        tags=[str(tag) for tag in row.get("tags", [])],
    )


def _insight_from_dict(row: dict[str, Any]) -> MemoryInsight:
    return MemoryInsight(
        id=str(row["id"]),
        created_at=str(row.get("created_at", "")),
        action=_coerce_action(row.get("action", RecommendationAction.NO_ACTION.value)),
        opportunity_type=_coerce_opportunity(row.get("opportunity_type")),
        sku=str(row["sku"]) if row.get("sku") else None,
        sample_size=int(row.get("sample_size", 0)),
        success_rate=_float(row.get("success_rate")),
        average_success_score=_float(row.get("average_success_score")),
        message=str(row.get("message", "")),
        supporting_records=[str(item) for item in row.get("supporting_records", [])],
    )


def _record_search_text(record: RecommendationMemoryRecord) -> str:
    return " ".join(
        [
            record.id,
            record.sku,
            record.action.value,
            record.opportunity_type.value if record.opportunity_type else "",
            record.reason,
            record.result.value,
            " ".join(record.tags),
        ]
    ).lower()


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _to_jsonable(item)
            for key, item in asdict(value).items()  # type: ignore[arg-type]
        }
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _coerce_action(value: object) -> RecommendationAction:
    try:
        return RecommendationAction(str(value))
    except ValueError:
        return RecommendationAction.NO_ACTION


def _coerce_opportunity(value: object) -> OpportunityType | None:
    if value is None or value == "":
        return None
    try:
        return OpportunityType(str(value))
    except ValueError:
        return None


def _coerce_result(value: object) -> MemoryResult:
    try:
        return MemoryResult(str(value))
    except ValueError:
        return MemoryResult.UNKNOWN


def _float(value: object) -> float:
    if not isinstance(value, int | float | str):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
