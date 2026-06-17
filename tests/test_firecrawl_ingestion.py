from __future__ import annotations

import json

import httpx
from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.research.adapters.firecrawl import (
    FIRECRAWL_SCRAPE_URL,
    FirecrawlConfig,
    FirecrawlIngestionError,
    ingest_firecrawl_snapshot,
)


def test_firecrawl_ingestion_uses_scrape_endpoint_and_schema(monkeypatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    captured_payload: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content.decode("utf-8")))
        assert request.url == FIRECRAWL_SCRAPE_URL
        assert request.headers["Authorization"] == "Bearer fc-test"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "json": {
                        "observations": [
                            {
                                "sku": "SKU-1",
                                "product_name": "Competitor product",
                                "seller_name": "Seller A",
                                "source_url": "https://example.test/p",
                                "price": 999,
                                "rating": 4.7,
                                "review_count": 42,
                                "available": True,
                            }
                        ]
                    },
                    "metadata": {"title": "Product page"},
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = ingest_firecrawl_snapshot(
        "https://example.test/p",
        query="sku-1",
        config=FirecrawlConfig(),
        client=client,
    )

    assert captured_payload["url"] == "https://example.test/p"
    assert "markdown" in captured_payload["formats"]
    assert result.ingestion.raw_rows == 1
    assert result.ingestion.ingested_rows == 1
    assert result.ingestion.snapshot.source_name == "firecrawl"
    assert result.ingestion.snapshot.observations[0].sku == "SKU-1"
    assert result.metadata["title"] == "Product page"


def test_firecrawl_ingestion_supports_json_list(monkeypatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "json": [
                        {"offer_id": "OFFER-1", "price": 100},
                        {"offer_id": "OFFER-2", "price": 120},
                    ]
                },
            },
        )

    result = ingest_firecrawl_snapshot(
        "https://example.test/list",
        query="list",
        config=FirecrawlConfig(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.ingestion.raw_rows == 2
    assert [row.sku for row in result.ingestion.snapshot.observations] == [
        "OFFER-1",
        "OFFER-2",
    ]


def test_firecrawl_ingestion_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    try:
        ingest_firecrawl_snapshot("https://example.test", query="q", config=FirecrawlConfig())
    except FirecrawlIngestionError as exc:
        assert "API key is missing" in str(exc)
    else:
        raise AssertionError("Expected FirecrawlIngestionError")


def test_firecrawl_ingestion_rejects_http_error(monkeypatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    try:
        ingest_firecrawl_snapshot(
            "https://example.test",
            query="q",
            config=FirecrawlConfig(),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
    except FirecrawlIngestionError as exc:
        assert "HTTP 429" in str(exc)
    else:
        raise AssertionError("Expected FirecrawlIngestionError")


def test_firecrawl_cli_missing_key_is_safe(monkeypatch) -> None:
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    result = CliRunner().invoke(
        main,
        ["research", "firecrawl", "ingest", "https://example.test", "--query", "q"],
    )

    assert result.exit_code != 0
    assert "API key is missing" in result.output
