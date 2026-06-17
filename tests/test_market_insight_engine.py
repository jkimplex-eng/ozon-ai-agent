from __future__ import annotations

from datetime import UTC, datetime

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.research.insights.engine import (
    detect_opportunities,
    detect_risks,
    generate_market_insights,
)
from ozon_agent.research.insights.models import MarketInsightType
from ozon_agent.research.insights.report_builder import build_market_report
from ozon_agent.research.knowledge.insight_store import list_insights
from ozon_agent.research.knowledge.models import MarketKnowledgeSnapshot
from ozon_agent.research.knowledge.snapshot_store import save_snapshot
from ozon_agent.research.models import ResearchObservation


def test_generate_market_insights_persists_records(tmp_path) -> None:
    snapshots = [_snapshot("a", 1290, 100), _snapshot("b", 1090, 500)]

    insights = generate_market_insights(snapshots=snapshots, storage_dir=tmp_path)
    stored = list_insights(storage_dir=tmp_path)

    insight_types = {insight.insight_type for insight in insights}
    assert MarketInsightType.PRICE_DROP in insight_types
    assert MarketInsightType.REVIEW_SURGE in insight_types
    assert len(stored) == len(insights)
    assert stored[0].metrics["score"] >= 0


def test_detect_risks_and_opportunities() -> None:
    snapshots = [
        _snapshot("a", 1290, 100),
        _snapshot("b", 1090, 500),
        _snapshot("c", 1000, 800, extra_size="200x300"),
    ]
    insights = generate_market_insights(snapshots=snapshots, persist=False)

    risks = detect_risks(insights)
    opportunities = detect_opportunities(insights)

    assert any(risk.risk_type == "PRICE_WAR" for risk in risks)
    assert any(item.opportunity_type == "ASSORTMENT_COVERAGE" for item in opportunities)


def test_report_generation_groups_by_priority() -> None:
    insights = generate_market_insights(
        snapshots=[_snapshot("a", 1290, 100), _snapshot("b", 1090, 500)],
        persist=False,
    )

    report = build_market_report(insights)

    assert report.startswith("Market Insights")
    assert "PRICE_DROP" in report


def test_insight_cli_commands(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_MARKET_KNOWLEDGE_DIR", str(tmp_path))
    save_snapshot(_snapshot("a", 1290, 100).to_research_snapshot(), storage_dir=tmp_path)
    save_snapshot(_snapshot("b", 1090, 500).to_research_snapshot(), storage_dir=tmp_path)

    runner = CliRunner()
    generated = runner.invoke(main, ["research", "insights", "generate"])
    latest = runner.invoke(main, ["research", "insights", "latest"])
    risks = runner.invoke(main, ["research", "insights", "risks"])
    opportunities = runner.invoke(main, ["research", "insights", "opportunities"])

    assert generated.exit_code == 0
    assert "Market Insights" in generated.output
    assert latest.exit_code == 0
    assert "PRICE_DROP" in latest.output
    assert risks.exit_code == 0
    assert "Market Risks" in risks.output
    assert opportunities.exit_code == 0
    assert "Market Opportunities" in opportunities.output


def _snapshot(
    snapshot_id: str,
    price: float,
    reviews: int,
    extra_size: str | None = "160x230",
) -> MarketKnowledgeSnapshot:
    observations = [
        ResearchObservation(
            sku="SKU-1",
            seller_name="Seller A",
            source_url="https://example.test/a",
            price=price,
            review_count=reviews,
            attributes={"size": "160x230"},
        )
    ]
    if extra_size:
        observations.append(
            ResearchObservation(
                sku="SKU-2",
                seller_name="Seller B",
                source_url="https://example.test/b",
                price=price + 100,
                review_count=reviews + 10,
                attributes={"size": extra_size},
            )
        )
    return MarketKnowledgeSnapshot(
        id=snapshot_id,
        query="query",
        source_name="manual",
        captured_at=datetime(2026, 1, int(snapshot_id, 36) % 28 + 1, tzinfo=UTC),
        observations=observations,
    )
