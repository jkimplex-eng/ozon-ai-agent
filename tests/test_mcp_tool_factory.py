from __future__ import annotations

import json
from pathlib import Path

from ozon_agent.mcp.schemas import MCPExecutionDisabledError
from ozon_agent.mcp.tool_factory import discover_tools
from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger


def test_discover_tools_from_typed_clients(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    tools = discover_tools()
    tool_names = {tool.name for tool in tools}
    assert "products.product_info" in tool_names
    assert "stocks.product_info_stocks" in tool_names
    product_tool = next(tool for tool in tools if tool.name == "products.product_info")
    assert product_tool.category == "Products"
    assert product_tool.endpoint_metadata["path"] == "/v2/product/info"


def test_tool_execution_is_disabled(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    tool = discover_tools()[0]
    try:
        tool.execute({})
    except MCPExecutionDisabledError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("Expected MCPExecutionDisabledError")


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "MCP Test API", "description": "test"},
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
