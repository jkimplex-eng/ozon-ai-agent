from __future__ import annotations

from ozon_agent.decision.models import OpportunityType, RecommendationAction
from ozon_agent.memory.models import MemoryResult, RecommendationMemoryRecord, utc_now_iso
from ozon_agent.memory.repository import (
    delete_memory_record,
    list_memory_records,
    load_memory_record,
    save_memory_record,
    search_memory_records,
)


def test_memory_record_round_trip(tmp_path) -> None:
    record = _record("memory-1")

    save_memory_record(record, root=tmp_path)

    assert load_memory_record("memory-1", root=tmp_path) == record
    assert search_memory_records("SKU-1", root=tmp_path) == [record]


def test_delete_memory_record(tmp_path) -> None:
    save_memory_record(_record("memory-1"), root=tmp_path)

    assert delete_memory_record("memory-1", root=tmp_path)
    assert list_memory_records(root=tmp_path) == []


def _record(record_id: str) -> RecommendationMemoryRecord:
    return RecommendationMemoryRecord(
        id=record_id,
        created_at=utc_now_iso(),
        sku="SKU-1",
        action=RecommendationAction.INCREASE_BUDGET,
        opportunity_type=OpportunityType.AD_GROWTH,
        reason="high ROAS",
        expected_effect="increase orders",
        supporting_metrics={"category": "Rugs", "price_range": "1000-1500"},
        confidence_score=0.8,
        risk_score=0.2,
        result=MemoryResult.SUCCESS,
        success_score=0.9,
        tags=["AD_GROWTH"],
    )
