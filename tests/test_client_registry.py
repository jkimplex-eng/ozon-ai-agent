from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.integrations.ozon_api.client_registry import (
    get_client,
    get_method,
    list_clients,
    list_methods,
)
from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger


def test_list_and_get_clients(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    clients = list_clients()
    assert "products" in clients
    assert "stocks" in clients
    products_client = get_client("products")
    assert products_client.category.value == "Products"


def test_list_and_get_methods(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    methods = list_methods("products")
    assert "product_info" in methods
    descriptor = get_method("products", "product_info")
    description = descriptor.describe()
    assert description["path"] == "/v2/product/info"
    assert description["method"] == "POST"


def test_unknown_client_raises(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    try:
        get_client("missing")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "Registry Test API", "description": "test"},
        "paths": {
            "/v2/product/info": {
                "post": {
                    "summary": "Product info",
                    "description": "Get product info",
                    "tags": ["ProductAPI"],
                    "responses": {
                        "200": {
                            "description": "Ok",
                            "content": {"application/json": {"schema": {"type": "object"}}},
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
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
        },
    }
    swagger_path = tmp_path / "swagger.json"
    swagger_path.write_text(json.dumps(payload), encoding="utf-8")
    return swagger_path
