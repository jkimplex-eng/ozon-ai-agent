from __future__ import annotations

import json

import httpx
import pytest
from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.ingestion.client import LiveOzonReadOnlyClient
from ozon_agent.ingestion.endpoints import build_request_payload, validate_read_only_path
from ozon_agent.ingestion.models import (
    LiveOzonCredentials,
    LiveOzonDataset,
    LiveOzonIngestionRequest,
)
from ozon_agent.ingestion.normalizers import normalize_rows
from ozon_agent.ingestion.service import ingest_live_ozon_dataset


def test_read_only_path_guard_blocks_mutation_markers() -> None:
    with pytest.raises(ValueError):
        validate_read_only_path("/v1/product/import/prices")


def test_build_orders_request_requires_dates() -> None:
    with pytest.raises(ValueError):
        build_request_payload(LiveOzonDataset.ORDERS_FBO)


def test_normalize_products() -> None:
    payload = {
        "result": {
            "items": [
                {"product_id": 10, "offer_id": "A1", "sku": 123, "name": "Product"}
            ]
        }
    }

    rows = normalize_rows(LiveOzonDataset.PRODUCTS, payload)

    assert rows[0]["product_id"] == 10
    assert rows[0]["sku"] == "123"


def test_live_client_uses_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/product/list"
        return httpx.Response(200, json={"result": {"items": [{"product_id": 1}]}})

    client = LiveOzonReadOnlyClient(
        LiveOzonCredentials(client_id="cid", api_key="key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://test"),
    )

    payload = client.post_read_only("/v2/product/list", {"limit": 1})

    assert payload["result"]["items"][0]["product_id"] == 1


def test_ingest_live_ozon_dataset_saves_raw_and_normalized(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": {
                    "items": [
                        {"product_id": 1, "offer_id": "A1", "sku": 100, "name": "Rug"}
                    ]
                }
            },
        )

    client = LiveOzonReadOnlyClient(
        LiveOzonCredentials(client_id="cid", api_key="key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://test"),
    )

    result = ingest_live_ozon_dataset(
        LiveOzonIngestionRequest(dataset=LiveOzonDataset.PRODUCTS),
        client=client,
        storage_root=tmp_path,
    )

    assert result.raw_rows == 1
    assert result.normalized_rows == 1
    assert result.raw_path is not None and result.raw_path.exists()
    assert result.normalized_path is not None and result.normalized_path.exists()
    normalized = json.loads(result.normalized_path.read_text(encoding="utf-8"))
    assert normalized["rows"][0]["offer_id"] == "A1"


def test_ingest_dry_run_skips_credentials_and_http() -> None:
    result = ingest_live_ozon_dataset(
        LiveOzonIngestionRequest(dataset=LiveOzonDataset.PRODUCTS, dry_run=True)
    )

    assert result.dry_run
    assert result.raw_rows == 0
    assert result.warnings


def test_live_ozon_cli_datasets_and_dry_run() -> None:
    runner = CliRunner()

    datasets = runner.invoke(main, ["ingest", "ozon", "datasets"])
    dry_run = runner.invoke(main, ["ingest", "ozon", "run", "products", "--dry-run"])

    assert datasets.exit_code == 0
    assert "products" in datasets.output
    assert dry_run.exit_code == 0
    assert "Live Ozon Ingestion" in dry_run.output
    assert "dry_run" in dry_run.output
