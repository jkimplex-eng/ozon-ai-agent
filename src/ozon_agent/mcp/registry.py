from __future__ import annotations

from ozon_agent.mcp.schemas import MCPToolDescriptor

_TOOLS: dict[str, MCPToolDescriptor] = {}


def register_tool(tool: MCPToolDescriptor) -> MCPToolDescriptor:
    _TOOLS[tool.name] = tool
    return tool


def unregister_tool(name: str) -> None:
    _TOOLS.pop(name, None)


def list_tools() -> list[MCPToolDescriptor]:
    return [tool for _, tool in sorted(_TOOLS.items())]


def get_tool(name: str) -> MCPToolDescriptor:
    exact_match = _TOOLS.get(name)
    if exact_match is not None:
        return exact_match
    prefix_matches = [
        (tool_name, tool)
        for tool_name, tool in _TOOLS.items()
        if tool_name.startswith(f"{name}_")
    ]
    if prefix_matches:
        return sorted(prefix_matches, key=lambda item: (len(item[0]), item[0]))[0][1]
    raise KeyError(f"MCP tool {name} not found")
