from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.integrations.ozon_api.client_generator import generate_client_blueprint
from ozon_agent.integrations.ozon_api.client_stubs import (
    OzonApiExecutionDisabledError,
    generate_typed_client_stubs,
)
from ozon_agent.integrations.ozon_api.endpoint_mapper import build_category_map, build_endpoint_map
from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger


def test_generate_client_blueprint(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    blueprint = generate_client_blueprint()
    assert blueprint["client_name"] == "ozon_api_client"
    assert blueprint["request_execution"] == "disabled"
    assert blueprint["endpoint_count"] == 3
    assert blueprint["module_count"] >= 2
    assert blueprint["typed_stubs_available"] is True
    assert blueprint["execution_guard"] == "OzonApiExecutionDisabledError"
    module_names = {module["name"] for module in blueprint["modules"]}
    assert "stocks" in module_names
    assert "orders" in module_names


def test_build_endpoint_map_and_category_map(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    endpoint_map = build_endpoint_map()
    category_map = build_category_map()
    assert "product-info-stocks" in endpoint_map
    assert endpoint_map["product-info-stocks"]["category"] == "Stocks"
    assert "stocks" in category_map
    assert "product-info-stocks" in category_map["stocks"]


def test_generate_typed_client_stubs(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    client_stubs = generate_typed_client_stubs()
    method = client_stubs.get_method("product-info-stocks")
    request = method.prepare_request({"sku": "123"})
    assert method.category == "Stocks"
    assert request.endpoint_name == "product-info-stocks"
    assert request.method == "POST"
    assert request.path == "/v1/product/info/stocks"
    assert request.body == {"sku": "123"}


def test_typed_client_stubs_do_not_execute(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    client_stubs = generate_typed_client_stubs()
    try:
        client_stubs.execute("product-info-stocks", {"sku": "123"})
    except OzonApiExecutionDisabledError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("Expected OzonApiExecutionDisabledError")


def test_typed_client_stubs_filter_by_category(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    client_stubs = generate_typed_client_stubs()
    stock_methods = client_stubs.list_methods(category="stocks")
    assert stock_methods
    assert {method.category for method in stock_methods} == {"Stocks"}


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "Client Test API", "description": "test"},
        "paths": {
            "/v1/product/info/stocks": {
                "post": {
                    "summary": "Stocks info",
                    "description": "Get stock info",
                    "tags": ["Prices&StocksAPI"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"sku": {"type": "string"}},
                                }
                            }
                        }
                    },
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
            "/v3/posting/fbs/list": {
                "post": {
                    "summary": "List FBS orders",
                    "description": "Get postings",
                    "tags": ["FBS"],
                    "responses": {
                        "200": {
                            "description": "Ok",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/v1/analytics/data": {
                "post": {
                    "summary": "Analytics data",
                    "description": "Get analytics data",
                    "tags": ["AnalyticsAPI"],
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
