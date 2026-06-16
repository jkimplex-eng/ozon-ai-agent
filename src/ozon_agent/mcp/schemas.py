from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MCPExecutionDisabledError(RuntimeError):
    pass


@dataclass(frozen=True)
class MCPToolDescriptor:
    name: str
    description: str
    category: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]
    endpoint_metadata: dict[str, Any]

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
            "endpoint_metadata": self.endpoint_metadata,
        }

    def execute(self, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        raise MCPExecutionDisabledError(
            f"MCP execution is disabled for tool '{self.name}'. "
            "This foundation layer only supports discovery and description."
        )
