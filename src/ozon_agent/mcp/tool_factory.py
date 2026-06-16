from __future__ import annotations

from ozon_agent.integrations.ozon_api.client_registry import get_client, list_clients
from ozon_agent.integrations.ozon_api.models import OzonMethodDescriptor
from ozon_agent.mcp.schemas import MCPToolDescriptor


def discover_tools() -> list[MCPToolDescriptor]:
    tools: list[MCPToolDescriptor] = []
    for client_name in list_clients():
        client = get_client(client_name)
        for method_name in client.list_methods():
            tools.append(_build_tool_descriptor(client_name, client.get_method(method_name)))
    return sorted(tools, key=lambda item: item.name)


def _build_tool_descriptor(
    client_name: str,
    descriptor: OzonMethodDescriptor,
) -> MCPToolDescriptor:
    metadata = descriptor.metadata
    description = metadata.summary or metadata.description or metadata.name
    return MCPToolDescriptor(
        name=f"{client_name}.{metadata.method_name}",
        description=description,
        category=metadata.category,
        request_schema=metadata.request_schema,
        response_schema=metadata.response_schema,
        endpoint_metadata=descriptor.describe(),
    )
