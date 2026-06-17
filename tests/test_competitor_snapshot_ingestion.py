from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.research.snapshot_ingestion import (
    SnapshotIngestionError,
    ingest_competitor_snapshot,
)


def test_ingest_json_array_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "competitors.json"
    path.write_text(
        json.dumps(
            [
                {
                    "sku": "SKU-1",
                    "name": "Competitor product",
                    "seller": "Seller A",
                    "price": "999,50",
                    "rating": "4.7",
                    "reviewCount": "42",
                    "rank": "3",
                    "available": "yes",
                    "url": "https://example.test/sku-1",
                    "extra_field": "kept",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_competitor_snapshot(path, query="query-a")

    assert result.raw_rows == 1
    assert result.ingested_rows == 1
    assert result.skipped_rows == 0
    assert result.snapshot.query == "query-a"
    row = result.snapshot.observations[0]
    assert row.sku == "SKU-1"
    assert row.product_name == "Competitor product"
    assert row.seller_name == "Seller A"
    assert row.price == 999.5
    assert row.rating == 4.7
    assert row.review_count == 42
    assert row.position == 3
    assert row.available is True
    assert row.source_url == "https://example.test/sku-1"
    assert row.attributes["extra_field"] == "kept"


def test_ingest_json_object_rows_and_skips_missing_sku(tmp_path: Path) -> None:
    path = tmp_path / "competitors.json"
    path.write_text(
        json.dumps(
            {
                "observations": [
                    {"offerId": "OFFER-1", "price": 100},
                    {"price": 200},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = ingest_competitor_snapshot(path)

    assert result.raw_rows == 2
    assert result.ingested_rows == 1
    assert result.skipped_rows == 1
    assert "missing sku" in result.warnings[0]
    assert result.snapshot.observations[0].sku == "OFFER-1"


def test_ingest_csv_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "competitors.csv"
    path.write_text(
        "sku,product_name,seller_name,price,rating,review_count,available\n"
        "SKU-2,Product B,Seller B,1200,4.5,10,true\n",
        encoding="utf-8",
    )

    result = ingest_competitor_snapshot(path)

    assert result.raw_rows == 1
    assert result.snapshot.observations[0].sku == "SKU-2"
    assert result.snapshot.observations[0].available is True


def test_ingest_rejects_unsupported_file(tmp_path: Path) -> None:
    path = tmp_path / "competitors.txt"
    path.write_text("nope", encoding="utf-8")

    try:
        ingest_competitor_snapshot(path)
    except SnapshotIngestionError as exc:
        assert "JSON and CSV" in str(exc)
    else:
        raise AssertionError("Expected SnapshotIngestionError")


def test_research_ingest_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OZON_AGENT_MARKET_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    path = tmp_path / "competitors.json"
    path.write_text(json.dumps([{"sku": "SKU-3", "price": 500}]), encoding="utf-8")

    result = CliRunner().invoke(main, ["research", "ingest", str(path), "--query", "cli"])

    assert result.exit_code == 0
    assert "Competitor Snapshot" in result.output
    assert "Ingestion" in result.output
    assert "Ingested rows" in result.output
    assert "SKU-3" in result.output
