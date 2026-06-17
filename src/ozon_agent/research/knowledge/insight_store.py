from __future__ import annotations

from pathlib import Path

from ozon_agent.research.knowledge.models import MarketInsightRecord
from ozon_agent.research.knowledge.repository import (
    ensure_storage,
    insight_from_dict,
    insight_to_dict,
    insights_dir,
    read_json,
    write_json,
)


def save_insight(
    insight: MarketInsightRecord,
    storage_dir: str | Path | None = None,
) -> MarketInsightRecord:
    ensure_storage(storage_dir)
    write_json(_insight_path(insight.id, storage_dir), insight_to_dict(insight))
    return insight


def save_insights(
    insights: list[MarketInsightRecord],
    storage_dir: str | Path | None = None,
) -> list[MarketInsightRecord]:
    return [save_insight(insight, storage_dir=storage_dir) for insight in insights]


def list_insights(storage_dir: str | Path | None = None) -> list[MarketInsightRecord]:
    directory = insights_dir(storage_dir)
    if not directory.exists():
        return []
    insights = [insight_from_dict(read_json(path)) for path in directory.glob("*.json")]
    return sorted(insights, key=lambda insight: insight.created_at, reverse=True)


def delete_insight(insight_id: str, storage_dir: str | Path | None = None) -> bool:
    path = _insight_path(insight_id, storage_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def _insight_path(insight_id: str, storage_dir: str | Path | None = None) -> Path:
    return insights_dir(storage_dir) / f"{insight_id}.json"
