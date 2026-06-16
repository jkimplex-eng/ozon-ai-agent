from __future__ import annotations

from collections import Counter

from ozon_agent.mcp.registry import get_tool, list_tools, register_tool
from ozon_agent.mcp.schemas import MCPExecutionDisabledError, MCPToolDescriptor
from ozon_agent.mcp.tool_factory import discover_tools


class MCPServer:
    def __init__(self, auto_discover: bool = True) -> None:
        if auto_discover:
            self.reload_tools()

    def reload_tools(self) -> list[MCPToolDescriptor]:
        tools = discover_tools()
        for tool in tools:
            register_tool(tool)
        return tools

    def list_tools(self) -> list[MCPToolDescriptor]:
        return list_tools()

    def describe_tool(self, name: str) -> dict[str, object]:
        return get_tool(name).describe()

    def stats(self) -> dict[str, object]:
        tools = self.list_tools()
        category_counts = Counter(tool.category for tool in tools)
        return {
            "tools": len(tools),
            "categories": dict(sorted(category_counts.items())),
        }

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, object] | None = None,
    ) -> dict[str, object]:
        raise MCPExecutionDisabledError(
            f"MCP execution is disabled for tool '{name}'. Discovery only."
        )
