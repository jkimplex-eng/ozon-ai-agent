from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from ozon_agent.cli import main
from ozon_agent.mcp.schemas import MCPExecutionDisabledError
from ozon_agent.mcp.server import MCPServer
from ozon_agent.skills.ozon_api.swagger_loader import reload_swagger


def test_mcp_server_list_describe_and_stats(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    server = MCPServer()
    tools = server.list_tools()
    assert tools
    description = server.describe_tool("products.product_info")
    assert description["category"] == "Products"
    assert description["name"] == "products.product_info"
    stats = server.stats()
    assert stats["tools"] == 2
    assert stats["categories"] == {"Products": 1, "Stocks": 1}


def test_mcp_server_execution_disabled(tmp_path: Path) -> None:
    reload_swagger(_write_swagger(tmp_path))
    server = MCPServer()
    try:
        server.execute_tool("products.product_info", {})
    except MCPExecutionDisabledError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("Expected MCPExecutionDisabledError")


def test_mcp_cli_commands() -> None:
    runner = CliRunner()
    tools_result = runner.invoke(main, ["mcp", "tools"])
    assert tools_result.exit_code == 0
    assert "products." in tools_result.output
    show_result = runner.invoke(main, ["mcp", "show", "products.product_info"])
    assert show_result.exit_code == 0
    assert "Ozon MCP Tool" in show_result.output
    stats_result = runner.invoke(main, ["mcp", "stats"])
    assert stats_result.exit_code == 0
    assert "Tools" in stats_result.output


def _write_swagger(tmp_path: Path) -> Path:
    payload = {
        "openapi": "3.0.0",
        "info": {"title": "MCP Server Test API", "description": "test"},
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
