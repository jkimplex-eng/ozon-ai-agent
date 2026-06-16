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


def build_category_map() -> dict[str, list[str]]:
    category_map: dict[str, list[str]] = {}
    for endpoint in list_endpoints():
        category_name = endpoint.category.value.lower()
        category_map.setdefault(category_name, []).append(endpoint.name)
    for endpoint_names in category_map.values():
        endpoint_names.sort()
    return dict(sorted(category_map.items()))
