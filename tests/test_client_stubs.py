from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.integrations.ozon_api.clients.products import ProductsClient
from ozon_agent.integrations.ozon_api.clients.stocks import StocksClient
from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger


def test_client_introspection_and_describe(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    products = ProductsClient()
    descriptor = products.get_method("product_info")
    assert products.product_info.describe() == descriptor.describe()
    description = descriptor.describe()
    assert description["path"] == "/v2/product/info"
    assert description["request_schema"] == {}
    assert description["response_schema"]


def test_client_stores_schema_maps(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    stocks = StocksClient()
    assert "product_info_stocks" in stocks.response_schemas
    assert stocks.endpoint_metadata["product_info_stocks"].metadata.category == "Stocks"


def test_client_method_alias_resolves_shortest_prefix(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    products = ProductsClient()
    descriptor = products.get_method("product")
    assert descriptor.metadata.method_name == "product_info"


def test_cli_clients_methods_and_describe() -> None:
    runner = CliRunner()
    clients_result = runner.invoke(main, ["api", "clients"])
    assert clients_result.exit_code == 0
    assert "products" in clients_result.output

    methods_result = runner.invoke(main, ["api", "methods", "products"])
    assert methods_result.exit_code == 0
    assert "product_info" in methods_result.output

    describe_result = runner.invoke(main, ["api", "describe", "products", "product_info"])
    assert describe_result.exit_code == 0
    assert "Path" in describe_result.output
    assert "/v" in describe_result.output


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "Stubs Test API", "description": "test"},
        "paths": {
            "/v2/product/info": {
                "post": {
                    "summary": "Product info",
                    "description": "Get product info",
                    "tags": ["ProductAPI"],
                    "responses": {
                        "200": {
                            "description": "Ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"result": {"type": "object"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/v1/product/info/stocks": {
                "post": {
                    "summary": "Stocks info",
                    "description": "Get stock info",
                    "tags": ["Prices&StocksAPI"],
                    "responses": {
                        "200": {
                            "description": "Ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"items": {"type": "array"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }
    swagger_path = tmp_path / "swagger.json"
    swagger_path.write_text(json.dumps(payload), encoding="utf-8")
    return swagger_path
