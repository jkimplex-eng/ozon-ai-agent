from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ozon_agent.research.knowledge.models import MarketKnowledgeSnapshot
from ozon_agent.research.knowledge.repository import (
    ensure_storage,
    read_json,
    snapshot_from_dict,
    snapshot_to_dict,
    snapshots_dir,
    write_json,
)
from ozon_agent.research.models import ResearchSnapshot


def save_snapshot(
    snapshot: ResearchSnapshot | MarketKnowledgeSnapshot,
    storage_dir: str | Path | None = None,
) -> MarketKnowledgeSnapshot:
    ensure_storage(storage_dir)
    knowledge_snapshot = _coerce_snapshot(snapshot)
    path = _snapshot_path(knowledge_snapshot.id, storage_dir)
    write_json(path, snapshot_to_dict(knowledge_snapshot))
    return knowledge_snapshot


def load_snapshot(
    snapshot_id: str,
    storage_dir: str | Path | None = None,
) -> MarketKnowledgeSnapshot | None:
    path = _snapshot_path(snapshot_id, storage_dir)
    if not path.exists():
        return None
    return snapshot_from_dict(read_json(path))


def list_snapshots(storage_dir: str | Path | None = None) -> list[MarketKnowledgeSnapshot]:
    directory = snapshots_dir(storage_dir)
    if not directory.exists():
        return []
    snapshots = [snapshot_from_dict(read_json(path)) for path in directory.glob("*.json")]
    return sorted(snapshots, key=lambda snapshot: snapshot.captured_at, reverse=True)


def delete_snapshot(snapshot_id: str, storage_dir: str | Path | None = None) -> bool:
    path = _snapshot_path(snapshot_id, storage_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def _coerce_snapshot(
    snapshot: ResearchSnapshot | MarketKnowledgeSnapshot,
) -> MarketKnowledgeSnapshot:
    if isinstance(snapshot, MarketKnowledgeSnapshot):
        return snapshot
    return MarketKnowledgeSnapshot(
        id=_new_snapshot_id(snapshot),
        query=snapshot.query,
        source_name=snapshot.source_name,
        captured_at=snapshot.captured_at,
        created_at=datetime.now(UTC),
        observations=list(snapshot.observations),
    )


def _new_snapshot_id(snapshot: ResearchSnapshot) -> str:
    prefix = snapshot.captured_at.strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{uuid4().hex[:8]}"


def _snapshot_path(snapshot_id: str, storage_dir: str | Path | None = None) -> Path:
    return snapshots_dir(storage_dir) / f"{snapshot_id}.json"
