from __future__ import annotations

from ozon_agent.mcp.registry import get_tool, list_tools, register_tool, unregister_tool
from ozon_agent.mcp.schemas import MCPToolDescriptor


def test_register_list_get_and_unregister_tool() -> None:
    tool = MCPToolDescriptor(
        name="products.product_info",
        description="Product info",
        category="Products",
        request_schema={},
        response_schema={},
        endpoint_metadata={"path": "/v2/product/info", "method": "POST"},
    )
    unregister_tool(tool.name)
    register_tool(tool)
    assert get_tool(tool.name) == tool
    assert tool in list_tools()
    unregister_tool(tool.name)
    try:
        get_tool(tool.name)
    except KeyError as exc:
        assert tool.name in str(exc)
    else:
        raise AssertionError("Expected KeyError")
