from __future__ import annotations

from typing import Any

from ozon_agent.skills.ozon_api.swagger_registry import list_endpoints


def build_endpoint_map() -> dict[str, dict[str, Any]]:
    endpoint_map: dict[str, dict[str, Any]] = {}
    for endpoint in list_endpoints():
        endpoint_map[endpoint.name] = {
            "path": endpoint.path,
            "method": endpoint.method,
            "category": endpoint.category.value,
            "tags": list(endpoint.tags),
        }
    return endpoint_map
