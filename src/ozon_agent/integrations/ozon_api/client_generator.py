from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ozon_agent.skills.ozon_api.swagger_loader import load_swagger
from ozon_agent.skills.ozon_api.swagger_models import OzonApiEndpoint
from ozon_agent.skills.ozon_api.swagger_registry import count_endpoints_by_category, list_endpoints


@dataclass(frozen=True)
class ClientMethodBlueprint:
    name: str
    method: str
    path: str
    summary: str
    category: str
    request_schema_keys: list[str]
    response_schema_keys: list[str]


@dataclass(frozen=True)
class ClientModuleBlueprint:
    name: str
    endpoint_count: int
    methods: list[ClientMethodBlueprint]


@dataclass(frozen=True)
class ClientBlueprint:
    client_name: str
    source: str
    swagger_title: str
    swagger_version: str
    request_execution: str
    endpoint_count: int
    module_count: int
    modules: list[ClientModuleBlueprint]
    category_counts: dict[str, int]


def generate_client_blueprint() -> dict[str, Any]:
    document = load_swagger()
    endpoints = list_endpoints()
    modules_by_category: dict[str, list[ClientMethodBlueprint]] = {}
    for endpoint in endpoints:
        module_name = endpoint.category.value.lower()
        modules_by_category.setdefault(module_name, []).append(_build_method_blueprint(endpoint))

    modules = [
        ClientModuleBlueprint(
            name=module_name,
            endpoint_count=len(methods),
            methods=sorted(methods, key=lambda item: (item.name, item.method)),
        )
        for module_name, methods in sorted(modules_by_category.items())
    ]
    category_counts = {
        category.value.lower(): count
        for category, count in count_endpoints_by_category().items()
        if count > 0
    }
    blueprint = ClientBlueprint(
        client_name="ozon_api_client",
        source="skills/ozon_api/swagger.json",
        swagger_title=document.title,
        swagger_version=document.version,
        request_execution="disabled",
        endpoint_count=len(endpoints),
        module_count=len(modules),
        modules=modules,
        category_counts=category_counts,
    )
    return asdict(blueprint)


def _build_method_blueprint(endpoint: OzonApiEndpoint) -> ClientMethodBlueprint:
    return ClientMethodBlueprint(
        name=endpoint.name,
        method=endpoint.method,
        path=endpoint.path,
        summary=endpoint.summary,
        category=endpoint.category.value,
        request_schema_keys=sorted(endpoint.request_schema.keys()),
        response_schema_keys=sorted(endpoint.response_schema.keys()),
    )
