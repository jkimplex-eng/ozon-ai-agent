from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger
from ozon_agent.skills.ozon_api.swagger_models import EndpointCategory, EndpointNotFoundError
from ozon_agent.skills.ozon_api.swagger_registry import (
    count_endpoints,
    count_endpoints_by_category,
    get_endpoint,
    list_endpoints,
    search_endpoints,
)


def test_list_and_count_endpoints(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    assert count_endpoints() == 4
    assert len(list_endpoints()) == 4


def test_search_endpoints(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    matches = search_endpoints("stock")
    assert matches
    assert any(endpoint.category is EndpointCategory.STOCKS for endpoint in matches)


def test_get_endpoint(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    endpoint = get_endpoint("product-info-stocks")
    assert endpoint.method == "POST"
    assert endpoint.path == "/v1/product/info/stocks"


def test_get_endpoint_raises_for_missing(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    try:
        get_endpoint("missing-endpoint")
    except EndpointNotFoundError:
        pass
    else:
        raise AssertionError("Expected EndpointNotFoundError")


def test_category_stats(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    reload_swagger(swagger_path)
    stats = count_endpoints_by_category()
    assert stats[EndpointCategory.STOCKS] >= 1
    assert stats[EndpointCategory.ORDERS] >= 1
    assert stats[EndpointCategory.FINANCE] >= 1


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "description": "test"},
        "paths": {
            "/v1/product/info/stocks": {
                "post": {
                    "summary": "Stocks info",
                    "description": "Get stock info",
                    "tags": ["ProductAPI", "Prices&StocksAPI"],
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                    "responses": {
                        "200": {
                            "description": "Ok",
                            "content": {"application/json": {"schema": {"type": "object"}}},
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
            "/v3/finance/transaction/list": {
                "post": {
                    "summary": "Finance list",
                    "description": "Get finance data",
                    "tags": ["FinanceAPI"],
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
