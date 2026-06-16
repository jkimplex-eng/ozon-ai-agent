from __future__ import annotations

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.research.comparator import compare_marketplace
from ozon_agent.research.engine import generate_marketplace_research_report
from ozon_agent.research.insight_engine import detect_research_insights
from ozon_agent.research.models import (
    MarketplaceSource,
    MarketplaceSourceType,
    PricePosition,
    ResearchInsightType,
    ResearchObservation,
    ResearchSourceStatus,
)
from ozon_agent.research.snapshot_builder import build_research_snapshot
from ozon_agent.research.source_registry import (
    get_source,
    list_sources,
    register_source,
    reload_sources,
    source_exists,
    unregister_source,
)


def test_source_registry_defaults_and_custom_source() -> None:
    reload_sources()
    assert source_exists("manual")
    assert get_source("firecrawl").requires_network is True
    custom = MarketplaceSource(
        name="fixture",
        source_type=MarketplaceSourceType.MANUAL,
        status=ResearchSourceStatus.ACTIVE,
        description="Fixture source",
    )
    register_source(custom)
    assert get_source("fixture") == custom
    unregister_source("fixture")
    assert not source_exists("fixture")


def test_snapshot_normalizes_unsafe_values() -> None:
    snapshot = build_research_snapshot(
        query="  shoes  ",
        observations=[
            ResearchObservation(
                sku=" SKU-1 ",
                price=-10,
                rating=7,
                review_count=-1,
                position=-5,
            )
        ],
    )
    row = snapshot.observations[0]
    assert snapshot.query == "shoes"
    assert row.sku == "SKU-1"
    assert row.price is None
    assert row.rating == 5.0
    assert row.review_count is None
    assert row.position is None


def test_compare_marketplace_price_position() -> None:
    comparisons = compare_marketplace(
        own_observations=[ResearchObservation(sku="A", price=120, rating=4.0, review_count=10)],
        competitor_observations=[
            ResearchObservation(sku="A", price=100, rating=4.5, review_count=50),
            ResearchObservation(sku="A", price=100, rating=4.7, review_count=70),
        ],
    )
    comparison = comparisons[0]
    assert comparison.price_position is PricePosition.ABOVE_MARKET
    assert comparison.avg_competitor_price == 100
    assert comparison.review_gap == -50


def test_insights_detect_price_review_and_rating_gaps() -> None:
    comparisons = compare_marketplace(
        own_observations=[ResearchObservation(sku="A", price=130, rating=4.0, review_count=10)],
        competitor_observations=[
            ResearchObservation(
                sku="A",
                price=100,
                rating=4.5,
                review_count=50,
                source_url="https://example.test/a",
            )
        ],
    )
    insight_types = {item.insight_type for item in detect_research_insights(comparisons)}
    assert ResearchInsightType.PRICE_POSITION in insight_types
    assert ResearchInsightType.REVIEW_GAP in insight_types
    assert ResearchInsightType.RATING_GAP in insight_types


def test_report_handles_empty_inputs() -> None:
    report = generate_marketplace_research_report("empty")
    assert report.summary["own_observations"] == 0
    assert report.summary["competitor_observations"] == 0
    assert report.summary["compared_skus"] == 0
    assert report.summary["execution"] == "disabled"


def test_report_marks_missing_competitor_observations() -> None:
    report = generate_marketplace_research_report(
        "single",
        own_observations=[ResearchObservation(sku="A", price=100)],
    )
    assert report.comparisons[0].competitor_count == 0
    assert report.insights[0].insight_type is ResearchInsightType.ASSORTMENT_GAP


def test_research_cli_sources_and_sample() -> None:
    runner = CliRunner()
    sources_result = runner.invoke(main, ["research", "sources"])
    assert sources_result.exit_code == 0
    assert "Marketplace Research Sources" in sources_result.output
    assert "firecrawl" in sources_result.output

    sample_result = runner.invoke(main, ["research", "sample"])
    assert sample_result.exit_code == 0
    assert "Marketplace Research Sample" in sample_result.output
    assert "External collection disabled" in sample_result.output


def test_list_sources_is_non_empty() -> None:
    assert list_sources()
