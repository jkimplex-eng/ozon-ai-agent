from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.integrations.ozon_api.client_generator import generate_client_blueprint
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
