from __future__ import annotations

from datetime import UTC, datetime

from ozon_agent.research.knowledge.snapshot_store import (
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from ozon_agent.research.models import ResearchObservation, ResearchSnapshot


def test_save_load_list_and_delete_snapshot(tmp_path) -> None:
    snapshot = ResearchSnapshot(
        query="query",
        source_name="manual",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        observations=[
            ResearchObservation(
                sku="SKU-1",
                seller_name="Seller A",
                source_url="https://example.test/a",
                price=100,
            )
        ],
    )

    saved = save_snapshot(snapshot, storage_dir=tmp_path)
    loaded = load_snapshot(saved.id, storage_dir=tmp_path)
    listed = list_snapshots(storage_dir=tmp_path)

    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.query == "query"
    assert loaded.observations[0].sku == "SKU-1"
    assert listed[0].id == saved.id
    assert delete_snapshot(saved.id, storage_dir=tmp_path) is True
    assert load_snapshot(saved.id, storage_dir=tmp_path) is None


def test_list_snapshots_empty_storage(tmp_path) -> None:
    assert list_snapshots(storage_dir=tmp_path) == []
