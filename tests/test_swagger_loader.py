from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.skills.ozon_api.swagger_loader import (
    get_swagger_version,
    load_swagger,
    reload_swagger,
    validate_swagger,
)
from ozon_agent.skills.ozon_api.swagger_models import SwaggerLoaderError, SwaggerValidationError


def test_load_swagger(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    document = load_swagger(swagger_path)
    assert document.version == "3.0.0"
    assert document.title == "Test API"
    assert document.endpoints


def test_reload_swagger(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    first = load_swagger(swagger_path)
    payload = json.loads(swagger_path.read_text(encoding="utf-8"))
    payload["info"]["title"] = "Updated API"
    swagger_path.write_text(json.dumps(payload), encoding="utf-8")
    second = reload_swagger(swagger_path)
    assert first.title != second.title
    assert second.title == "Updated API"


def test_validate_swagger_errors_on_missing_paths() -> None:
    try:
        validate_swagger({"openapi": "3.0.0", "info": {"title": "X"}})
    except SwaggerValidationError as exc:
        assert "paths" in str(exc)
    else:
        raise AssertionError("Expected SwaggerValidationError")


def test_get_swagger_version(tmp_path: Path) -> None:
    swagger_path = _write_swagger(tmp_path)
    assert get_swagger_version(swagger_path) == "3.0.0"


def test_load_swagger_invalid_json(tmp_path: Path) -> None:
    swagger_path = tmp_path / "swagger.json"
    swagger_path.write_text("{broken", encoding="utf-8")
    try:
        reload_swagger(swagger_path)
    except SwaggerLoaderError as exc:
        assert "parse" in str(exc).lower()
    else:
        raise AssertionError("Expected SwaggerLoaderError")


def test_load_real_swagger_from_skill() -> None:
    document = reload_swagger()
    assert document.version == "3.0.0"
    assert document.title
    assert len(document.endpoints) > 100
    endpoint_names = {endpoint.name for endpoint in document.endpoints}
    assert "product-info-stocks" in endpoint_names


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "description": "test"},
        "paths": {
            "/v1/product/info/stocks": {
                "post": {
                    "operationId": "ProductInfoStocks",
                    "summary": "Stocks info",
                    "description": "Get stock info",
                    "tags": ["ProductAPI", "Prices&StocksAPI"],
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
            }
        },
    }
    swagger_path = tmp_path / "swagger.json"
    swagger_path.write_text(json.dumps(payload), encoding="utf-8")
    return swagger_path
