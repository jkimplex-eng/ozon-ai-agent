from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OzonEndpointMetadata:
    name: str
    method_name: str
    path: str
    http_method: str
    summary: str
    description: str
    tags: list[str]
    category: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class OzonMethodDescriptor:
    metadata: OzonEndpointMetadata

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.metadata.name,
            "method_name": self.metadata.method_name,
            "path": self.metadata.path,
            "method": self.metadata.http_method,
            "summary": self.metadata.summary,
            "description": self.metadata.description,
            "tags": list(self.metadata.tags),
            "category": self.metadata.category,
            "request_schema": self.metadata.request_schema,
            "response_schema": self.metadata.response_schema,
        }


def endpoint_name_to_method_name(endpoint_name: str) -> str:
    return endpoint_name.strip().lower().replace("-", "_")
