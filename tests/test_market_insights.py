from __future__ import annotations

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.research.knowledge.history import compare_snapshots
from ozon_agent.research.knowledge.insight_store import (
    delete_insight,
    list_insights,
    save_insight,
    save_insights,
)
from ozon_agent.research.knowledge.models import MarketInsightRecord, MarketKnowledgeSnapshot
from ozon_agent.research.knowledge.snapshot_store import list_snapshots
from ozon_agent.research.models import ResearchObservation


def test_save_list_and_delete_insight(tmp_path) -> None:
    insight = MarketInsightRecord(
        id="insight-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        insight_type="PRICE_CHANGED",
        sku="SKU-1",
        message="Competitor price decreased",
        severity="HIGH",
        metrics={"delta_percent": -12},
    )

    save_insight(insight, storage_dir=tmp_path)
    insights = list_insights(storage_dir=tmp_path)

    assert insights == [insight]
    assert delete_insight("insight-1", storage_dir=tmp_path) is True
    assert list_insights(storage_dir=tmp_path) == []


def test_compare_results_can_be_saved_as_insights(tmp_path) -> None:
    previous = _snapshot("a", 100)
    current = _snapshot("b", 88)
    insights = compare_snapshots(previous, current)

    saved = save_insights(insights, storage_dir=tmp_path)

    assert saved
    assert list_insights(storage_dir=tmp_path)[0].insight_type == "PRICE_CHANGED"


def test_research_cli_ingest_compare_and_insights(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_MARKET_KNOWLEDGE_DIR", str(tmp_path))
    runner = CliRunner()
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text(
        json.dumps([{"sku": "SKU-1", "seller": "Seller A", "url": "u", "price": 100}]),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps([{"sku": "SKU-1", "seller": "Seller A", "url": "u", "price": 88}]),
        encoding="utf-8",
    )

    first = runner.invoke(main, ["research", "ingest", str(first_path), "--query", "q"])
    second = runner.invoke(main, ["research", "ingest", str(second_path), "--query", "q"])
    snapshots_result = runner.invoke(main, ["research", "snapshots"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert snapshots_result.exit_code == 0
    snapshots = [snapshot.id for snapshot in list_snapshots(storage_dir=tmp_path)]
    assert len(snapshots) == 2

    compare = runner.invoke(main, ["research", "compare", snapshots[1], snapshots[0]])
    insights = runner.invoke(main, ["research", "insights"])

    assert compare.exit_code == 0
    assert "PRICE_CHANGED" in compare.output
    assert insights.exit_code == 0
    assert "PRICE_CHANGED" in insights.output


def _snapshot(snapshot_id: str, price: float) -> MarketKnowledgeSnapshot:
    return MarketKnowledgeSnapshot(
        id=snapshot_id,
        query="query",
        source_name="manual",
        captured_at=datetime(2026, 1, int(snapshot_id, 36) % 28 + 1, tzinfo=UTC),
        observations=[
            ResearchObservation(
                sku="SKU-1",
                seller_name="Seller A",
                source_url="https://example.test/a",
                price=price,
            )
        ],
    )
