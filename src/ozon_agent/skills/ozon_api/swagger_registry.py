from __future__ import annotations

from ozon_agent.skills.ozon_api.swagger_loader import load_swagger
from ozon_agent.skills.ozon_api.swagger_models import (
    EndpointCategory,
    EndpointNotFoundError,
    OzonApiEndpoint,
)


def list_endpoints() -> list[OzonApiEndpoint]:
    return list(load_swagger().endpoints)


def get_endpoint(name: str) -> OzonApiEndpoint:
    normalized_query = _normalize_query(name)
    endpoints = list_endpoints()
    for endpoint in endpoints:
        if _normalize_query(endpoint.name) == normalized_query:
            return endpoint
    partial_matches = [
        endpoint for endpoint in endpoints if normalized_query in _search_blob(endpoint)
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    raise EndpointNotFoundError(name)


def search_endpoints(query: str) -> list[OzonApiEndpoint]:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return []
    matches = [
        endpoint
        for endpoint in list_endpoints()
        if normalized_query in _search_blob(endpoint)
    ]
    return sorted(matches, key=lambda item: (item.category.value, item.name, item.method))


def count_endpoints() -> int:
    return len(list_endpoints())


def count_endpoints_by_category() -> dict[EndpointCategory, int]:
    counts = {category: 0 for category in EndpointCategory}
    for endpoint in list_endpoints():
        counts[endpoint.category] = counts.get(endpoint.category, 0) + 1
    return counts


def _search_blob(endpoint: OzonApiEndpoint) -> str:
    parts = [
        endpoint.name,
        endpoint.path,
        endpoint.method,
        endpoint.summary,
        endpoint.description,
        " ".join(endpoint.tags),
        endpoint.category.value,
    ]
    return _normalize_query(" ".join(parts))


def _normalize_query(value: str) -> str:
    return value.strip().lower().replace("_", "-")
